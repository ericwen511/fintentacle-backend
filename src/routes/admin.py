from flask import Blueprint, jsonify, request
from src.models.user import User, db
from src.models.watchlist import SystemStats
from src.models.note import Note
from src.models.news import NewsBookmark
from src.routes.auth import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """獲取所有用戶列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        users = User.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user_admin(user_id):
    """管理員更新用戶資料"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        # 更新用戶名（如果提供且不重複）
        if 'username' in data and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': '用戶名已存在'}), 400
            user.username = data['username']
        
        # 更新郵箱（如果提供且不重複）
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': '郵箱已存在'}), 400
            user.email = data['email']
        
        # 更新管理員權限
        if 'is_admin' in data:
            user.is_admin = bool(data['is_admin'])
        
        # 更新帳號狀態
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        
        # 重置密碼（如果提供）
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'message': '用戶資料更新成功',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user_admin(user_id):
    """管理員刪除用戶"""
    try:
        user = User.query.get_or_404(user_id)
        
        # 防止刪除自己
        from flask import session
        if user.id == session.get('user_id'):
            return jsonify({'error': '不能刪除自己的帳號'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        # 更新用戶統計
        SystemStats.increment_stat('total_users', -1)
        
        return jsonify({'message': '用戶已刪除'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_system_stats():
    """獲取系統統計數據"""
    try:
        # 實時計算統計數據
        total_users = User.query.count()
        total_notes = Note.query.count()
        total_news = NewsBookmark.query.count()
        
        # 更新統計數據
        SystemStats.update_stat('total_users', total_users)
        SystemStats.update_stat('total_notes', total_notes)
        SystemStats.update_stat('total_news', total_news)
        
        # 獲取所有統計數據
        stats = SystemStats.query.all()
        stats_dict = {stat.stat_name: stat.stat_value for stat in stats}
        
        # 添加額外統計
        active_users = User.query.filter_by(is_active=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        
        stats_dict.update({
            'active_users': active_users,
            'admin_users': admin_users
        })
        
        return jsonify(stats_dict), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/search', methods=['GET'])
@admin_required
def search_users():
    """搜索用戶"""
    try:
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not query:
            return jsonify({'error': '搜索關鍵字不能為空'}), 400
        
        users = User.query.filter(
            (User.username.contains(query)) | 
            (User.email.contains(query))
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page,
            'per_page': per_page,
            'query': query
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/bulk-action', methods=['POST'])
@admin_required
def bulk_user_action():
    """批量用戶操作"""
    try:
        data = request.json
        user_ids = data.get('user_ids', [])
        action = data.get('action')
        
        if not user_ids or not action:
            return jsonify({'error': '用戶ID列表和操作類型為必填項'}), 400
        
        users = User.query.filter(User.id.in_(user_ids)).all()
        
        if action == 'activate':
            for user in users:
                user.is_active = True
        elif action == 'deactivate':
            for user in users:
                user.is_active = False
        elif action == 'make_admin':
            for user in users:
                user.is_admin = True
        elif action == 'remove_admin':
            for user in users:
                user.is_admin = False
        elif action == 'delete':
            # 防止刪除當前管理員
            from flask import session
            current_user_id = session.get('user_id')
            users = [user for user in users if user.id != current_user_id]
            for user in users:
                db.session.delete(user)
        else:
            return jsonify({'error': '無效的操作類型'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': f'批量操作完成，影響 {len(users)} 個用戶',
            'action': action,
            'affected_count': len(users)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

