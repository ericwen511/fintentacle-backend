from flask import Blueprint, jsonify, request, session
from src.models.user import User, db
from src.models.watchlist import SystemStats
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """登入驗證裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '需要登入'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理員權限驗證裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '需要登入'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理員權限'}), 403
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
def register():
    """用戶註冊"""
    try:
        data = request.json
        
        # 驗證必要欄位
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': '用戶名、郵箱和密碼為必填項'}), 400
        
        # 檢查用戶名是否已存在
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': '用戶名已存在'}), 400
        
        # 檢查郵箱是否已存在
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': '郵箱已存在'}), 400
        
        # 創建新用戶
        user = User(
            username=data['username'],
            email=data['email']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # 更新用戶統計
        SystemStats.increment_stat('total_users')
        
        return jsonify({
            'message': '註冊成功',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用戶登入"""
    try:
        data = request.json
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': '用戶名和密碼為必填項'}), 400
        
        # 查找用戶
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': '用戶名或密碼錯誤'}), 401
        
        if not user.is_active:
            return jsonify({'error': '帳號已被停用'}), 401
        
        # 設置會話
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        # 更新最後登入時間
        user.update_last_login()
        
        return jsonify({
            'message': '登入成功',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用戶登出"""
    session.clear()
    return jsonify({'message': '登出成功'}), 200

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """獲取當前用戶資料"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': '用戶不存在'}), 404
    
    return jsonify(user.to_dict()), 200

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用戶資料"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': '用戶不存在'}), 404
        
        data = request.json
        
        # 更新用戶名（如果提供且不重複）
        if 'username' in data and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': '用戶名已存在'}), 400
            user.username = data['username']
            session['username'] = data['username']
        
        # 更新郵箱（如果提供且不重複）
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': '郵箱已存在'}), 400
            user.email = data['email']
        
        # 更新密碼（如果提供）
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'message': '資料更新成功',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """檢查登入狀態"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.is_active:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict()
            }), 200
    
    return jsonify({'authenticated': False}), 200

