from flask import Blueprint, jsonify, request
from src.models.user import db
from src.models.note import Note, Tag
from src.models.watchlist import SystemStats
from src.routes.auth import login_required

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/', methods=['GET'])
@login_required
def get_notes():
    """獲取用戶筆記列表"""
    try:
        from flask import session
        user_id = session['user_id']
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        tag_id = request.args.get('tag_id', type=int)
        stock_symbol = request.args.get('stock_symbol', '').strip()
        
        query = Note.query.filter_by(user_id=user_id)
        
        # 按標籤過濾
        if tag_id:
            query = query.filter(Note.tags.any(Tag.id == tag_id))
        
        # 按股票代碼過濾
        if stock_symbol:
            query = query.filter(Note.stock_symbol.contains(stock_symbol))
        
        # 按創建時間倒序排列
        query = query.order_by(Note.created_at.desc())
        
        notes = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'notes': [note.to_dict() for note in notes.items],
            'total': notes.total,
            'pages': notes.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/', methods=['POST'])
@login_required
def create_note():
    """創建新筆記"""
    try:
        from flask import session
        user_id = session['user_id']
        
        data = request.json
        
        if not data.get('title') or not data.get('content'):
            return jsonify({'error': '標題和內容為必填項'}), 400
        
        note = Note(
            user_id=user_id,
            title=data['title'],
            content=data['content'],
            stock_symbol=data.get('stock_symbol', '').strip() or None,
            stock_name=data.get('stock_name', '').strip() or None
        )
        
        # 處理標籤
        tag_ids = data.get('tag_ids', [])
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            note.tags = tags
        
        db.session.add(note)
        db.session.commit()
        
        # 更新筆記統計
        SystemStats.increment_stat('total_notes')
        
        return jsonify({
            'message': '筆記創建成功',
            'note': note.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/<int:note_id>', methods=['GET'])
@login_required
def get_note(note_id):
    """獲取單個筆記"""
    try:
        from flask import session
        user_id = session['user_id']
        
        note = Note.query.filter_by(id=note_id, user_id=user_id).first()
        if not note:
            return jsonify({'error': '筆記不存在'}), 404
        
        return jsonify(note.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/<int:note_id>', methods=['PUT'])
@login_required
def update_note(note_id):
    """更新筆記"""
    try:
        from flask import session
        user_id = session['user_id']
        
        note = Note.query.filter_by(id=note_id, user_id=user_id).first()
        if not note:
            return jsonify({'error': '筆記不存在'}), 404
        
        data = request.json
        
        # 更新基本資訊
        if 'title' in data:
            note.title = data['title']
        if 'content' in data:
            note.content = data['content']
        if 'stock_symbol' in data:
            note.stock_symbol = data['stock_symbol'].strip() or None
        if 'stock_name' in data:
            note.stock_name = data['stock_name'].strip() or None
        
        # 更新標籤
        if 'tag_ids' in data:
            tag_ids = data['tag_ids']
            if tag_ids:
                tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
                note.tags = tags
            else:
                note.tags = []
        
        db.session.commit()
        
        return jsonify({
            'message': '筆記更新成功',
            'note': note.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    """刪除筆記"""
    try:
        from flask import session
        user_id = session['user_id']
        
        note = Note.query.filter_by(id=note_id, user_id=user_id).first()
        if not note:
            return jsonify({'error': '筆記不存在'}), 404
        
        db.session.delete(note)
        db.session.commit()
        
        # 更新筆記統計
        SystemStats.increment_stat('total_notes', -1)
        
        return jsonify({'message': '筆記已刪除'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/search', methods=['GET'])
@login_required
def search_notes():
    """搜索筆記"""
    try:
        from flask import session
        user_id = session['user_id']
        
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not query:
            return jsonify({'error': '搜索關鍵字不能為空'}), 400
        
        notes = Note.query.filter(
            Note.user_id == user_id,
            (Note.title.contains(query)) | 
            (Note.content.contains(query)) |
            (Note.stock_symbol.contains(query)) |
            (Note.stock_name.contains(query))
        ).order_by(Note.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'notes': [note.to_dict() for note in notes.items],
            'total': notes.total,
            'pages': notes.pages,
            'current_page': page,
            'per_page': per_page,
            'query': query
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/recent', methods=['GET'])
@login_required
def get_recent_notes():
    """獲取最近的筆記"""
    try:
        from flask import session
        user_id = session['user_id']
        
        limit = request.args.get('limit', 5, type=int)
        
        notes = Note.query.filter_by(user_id=user_id)\
                         .order_by(Note.created_at.desc())\
                         .limit(limit).all()
        
        return jsonify([note.to_dict() for note in notes]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 標籤相關API
@notes_bp.route('/tags', methods=['GET'])
@login_required
def get_tags():
    """獲取所有標籤"""
    try:
        tags = Tag.query.all()
        return jsonify([tag.to_dict() for tag in tags]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/tags', methods=['POST'])
@login_required
def create_tag():
    """創建新標籤"""
    try:
        data = request.json
        
        if not data.get('name'):
            return jsonify({'error': '標籤名稱為必填項'}), 400
        
        # 檢查標籤是否已存在
        if Tag.query.filter_by(name=data['name']).first():
            return jsonify({'error': '標籤已存在'}), 400
        
        tag = Tag(
            name=data['name'],
            color=data.get('color', '#007bff')
        )
        
        db.session.add(tag)
        db.session.commit()
        
        return jsonify({
            'message': '標籤創建成功',
            'tag': tag.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

