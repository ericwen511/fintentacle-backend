from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import hashlib
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fintentacle-secret-key-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///fintentacle.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app, origins="*")

# 數據模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.relationship('Note', backref='author', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'notes_count': len(self.notes)
        }

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    stock_symbol = db.Column(db.String(10), nullable=True)
    tags = db.Column(db.String(500), nullable=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'stock_symbol': self.stock_symbol,
            'tags': self.tags.split(',') if self.tags else [],
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'author': {
                'id': self.author.id,
                'username': self.author.username
            } if self.author else None
        }

class NewsCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(1000), nullable=False)
    source = db.Column(db.String(100), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'source': self.source,
            'published_at': self.published_at.isoformat() if self.published_at else None
        }

# API路由
@app.route('/')
def index():
    return jsonify({
        'message': '金融八爪魚 FinTentacle API',
        'version': '2.0.0',
        'status': 'running',
        'endpoints': {
            'users': '/api/users',
            'notes': '/api/notes',
            'news': '/api/news',
            'stocks': '/api/stocks',
            'stats': '/api/stats'
        }
    })

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# 用戶API
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        users = User.query.all()
        return jsonify({
            'users': [user.to_dict() for user in users],
            'total': len(users)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        if not data or not data.get('username'):
            return jsonify({'error': '用戶名為必填項'}), 400
        
        user = User(
            username=data['username'],
            email=data.get('email', ''),
            password_hash=hashlib.sha256(data.get('password', 'default123').encode()).hexdigest(),
            is_admin=data.get('is_admin', False)
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': '用戶創建成功',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': '用戶名和密碼為必填項'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        if not user or user.password_hash != password_hash:
            return jsonify({'error': '用戶名或密碼錯誤'}), 401
        
        token = f"{user.id}-{secrets.token_hex(16)}"
        
        return jsonify({
            'message': '登錄成功',
            'token': token,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 筆記API
@app.route('/api/notes', methods=['GET'])
def get_notes():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        user_id = request.args.get('user_id', type=int)
        
        query = Note.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        else:
            query = query.filter_by(is_public=True)
        
        query = query.order_by(Note.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        notes = pagination.items
        
        return jsonify({
            'notes': [note.to_dict() for note in notes],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notes', methods=['POST'])
def create_note():
    try:
        data = request.get_json()
        if not data or not data.get('title') or not data.get('content'):
            return jsonify({'error': '標題和內容為必填項'}), 400
        
        user_id = data.get('user_id', 1)
        user = User.query.get(user_id)
        if not user:
            user = User(username='default_user', email='default@example.com')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        
        note = Note(
            title=data['title'],
            content=data['content'],
            stock_symbol=data.get('stock_symbol'),
            tags=','.join(data.get('tags', [])) if data.get('tags') else None,
            is_public=data.get('is_public', True),
            user_id=user_id
        )
        
        db.session.add(note)
        db.session.commit()
        
        return jsonify({
            'message': '筆記創建成功',
            'note': note.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    try:
        note = Note.query.get_or_404(note_id)
        data = request.get_json()
        
        if 'title' in data:
            note.title = data['title']
        if 'content' in data:
            note.content = data['content']
        if 'stock_symbol' in data:
            note.stock_symbol = data['stock_symbol']
        if 'tags' in data:
            note.tags = ','.join(data['tags']) if data['tags'] else None
        
        note.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '筆記更新成功',
            'note': note.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return jsonify({'message': '筆記刪除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 新聞API
@app.route('/api/news', methods=['GET'])
def get_news():
    try:
        # 檢查緩存
        cache_expiry = datetime.utcnow() - timedelta(hours=1)
        fresh_news = NewsCache.query.filter(NewsCache.cached_at > cache_expiry).order_by(NewsCache.published_at.desc()).all()
        
        if not fresh_news:
            # 創建示例新聞
            sample_news = [
                {
                    'title': 'NVIDIA股價創新高，AI晶片需求持續強勁',
                    'description': 'NVIDIA公司股價在最新財報發布後創下歷史新高，受益於人工智能和數據中心業務的強勁增長。',
                    'url': 'https://example.com/nvidia-stock-high',
                    'source': 'Financial Times',
                    'published_at': datetime.utcnow() - timedelta(hours=2)
                },
                {
                    'title': '台積電宣布擴大美國投資，新建3奈米廠',
                    'description': '台積電宣布將在美國亞利桑那州新建3奈米製程工廠，投資額預計達到400億美元。',
                    'url': 'https://example.com/tsmc-investment',
                    'source': 'Reuters',
                    'published_at': datetime.utcnow() - timedelta(hours=4)
                },
                {
                    'title': '聯準會暗示可能暫停升息，市場反應積極',
                    'description': '聯邦準備理事會官員在最新講話中暗示可能暫停升息步伐，股市應聲上漲。',
                    'url': 'https://example.com/fed-rates',
                    'source': 'Bloomberg',
                    'published_at': datetime.utcnow() - timedelta(hours=6)
                }
            ]
            
            # 清除舊緩存
            NewsCache.query.delete()
            
            # 添加新緩存
            fresh_news = []
            for news_data in sample_news:
                news = NewsCache(**news_data)
                db.session.add(news)
                fresh_news.append(news)
            
            db.session.commit()
        
        return jsonify({
            'news': [news.to_dict() for news in fresh_news[:10]],
            'total': len(fresh_news)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 股票API
@app.route('/api/stocks/search', methods=['GET'])
def search_stocks():
    try:
        query = request.args.get('q', '').upper()
        if not query:
            return jsonify({'error': '請提供搜索關鍵字'}), 400
        
        # 模擬股票數據
        sample_stocks = {
            'NVDA': {
                'symbol': 'NVDA',
                'name': 'NVIDIA Corporation',
                'price': 456.78,
                'change': 12.34,
                'change_percent': 2.78
            },
            'TSLA': {
                'symbol': 'TSLA',
                'name': 'Tesla, Inc.',
                'price': 234.56,
                'change': -5.67,
                'change_percent': -2.36
            },
            'AAPL': {
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'price': 178.90,
                'change': 3.45,
                'change_percent': 1.97
            },
            'TSM': {
                'symbol': 'TSM',
                'name': 'Taiwan Semiconductor Manufacturing Company Limited',
                'price': 89.12,
                'change': 1.23,
                'change_percent': 1.40
            }
        }
        
        stock_data = sample_stocks.get(query)
        if stock_data:
            return jsonify({'stock': stock_data})
        else:
            return jsonify({'error': '找不到該股票'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 統計API
@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_users = User.query.count()
        total_notes = Note.query.count()
        public_notes = Note.query.filter_by(is_public=True).count()
        total_news = NewsCache.query.count()
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_notes = Note.query.filter(Note.created_at > week_ago).count()
        
        return jsonify({
            'total_users': total_users,
            'total_notes': total_notes,
            'public_notes': public_notes,
            'total_news': total_news,
            'recent_notes': recent_notes,
            'updated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 初始化數據庫
def init_db():
    with app.app_context():
        db.create_all()
        
        if not User.query.first():
            # 創建管理員用戶
            admin = User(
                username='admin',
                email='admin@fintentacle.com',
                password_hash=hashlib.sha256('admin123'.encode()).hexdigest(),
                is_admin=True
            )
            db.session.add(admin)
            
            # 創建示例用戶
            demo_user = User(
                username='demo_user',
                email='demo@fintentacle.com',
                password_hash=hashlib.sha256('demo123'.encode()).hexdigest(),
                is_admin=False
            )
            db.session.add(demo_user)
            
            db.session.commit()
            
            # 創建示例筆記
            sample_notes = [
                {
                    'title': 'NVIDIA投資分析',
                    'content': 'NVIDIA作為AI晶片領導者，在人工智能浪潮中具有強大的競爭優勢。公司的GPU產品在機器學習和數據中心領域需求旺盛，預期未來幾年將持續受益於AI技術的普及。建議長期持有。',
                    'stock_symbol': 'NVDA',
                    'tags': 'AI,晶片,長期投資',
                    'user_id': admin.id
                },
                {
                    'title': '台積電技術護城河分析',
                    'content': '台積電在先進製程技術方面領先全球，3奈米和5奈米製程技術為公司建立了強大的護城河。隨著AI和高性能運算需求增長，台積電的技術優勢將轉化為持續的營收增長。',
                    'stock_symbol': 'TSM',
                    'tags': '半導體,技術,護城河',
                    'user_id': admin.id
                },
                {
                    'title': '特斯拉電動車市場前景',
                    'content': '特斯拉在電動車市場的領先地位正面臨傳統車廠的挑戰，但其在自動駕駛技術、充電網絡和電池技術方面仍有優勢。需要密切關注其市場份額變化和新產品推出情況。',
                    'stock_symbol': 'TSLA',
                    'tags': '電動車,自動駕駛,新能源',
                    'user_id': demo_user.id
                }
            ]
            
            for note_data in sample_notes:
                note = Note(**note_data, is_public=True)
                db.session.add(note)
            
            db.session.commit()
            
            print("數據庫初始化完成！")
            print("管理員帳號: admin / admin123")
            print("示例用戶: demo_user / demo123")

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

