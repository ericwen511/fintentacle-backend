import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.note import Note, Tag
from src.models.news import NewsBookmark
from src.models.watchlist import Watchlist, SystemStats
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.admin import admin_bp
from src.routes.notes import notes_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# 啟用CORS支援
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(notes_bp, url_prefix='/api/notes')

# 數據庫配置
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def init_database():
    """初始化數據庫和預設數據"""
    with app.app_context():
        db.create_all()
        
        # 初始化系統統計
        if SystemStats.query.count() == 0:
            stats = [
                SystemStats(stat_name='total_companies', stat_value=0),
                SystemStats(stat_name='total_news', stat_value=0),
                SystemStats(stat_name='total_notes', stat_value=0),
                SystemStats(stat_name='total_users', stat_value=0)
            ]
            for stat in stats:
                db.session.add(stat)
        
        # 初始化預設標籤
        if Tag.query.count() == 0:
            default_tags = [
                Tag(name='買入', color='#28a745'),
                Tag(name='賣出', color='#dc3545'),
                Tag(name='觀察', color='#ffc107'),
                Tag(name='財報', color='#17a2b8'),
                Tag(name='技術分析', color='#6f42c1'),
                Tag(name='基本面', color='#fd7e14'),
                Tag(name='風險', color='#e83e8c'),
                Tag(name='機會', color='#20c997')
            ]
            for tag in default_tags:
                db.session.add(tag)
        
        db.session.commit()
        print("數據庫初始化完成")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5001, debug=True)
