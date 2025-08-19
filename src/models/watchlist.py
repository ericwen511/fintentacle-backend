from datetime import datetime
from src.models.user import db

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(20), nullable=False)
    stock_name = db.Column(db.String(100), nullable=False)
    market = db.Column(db.String(10), nullable=False)  # 'TWSE', 'NASDAQ', 'NYSE', etc.
    stock_type = db.Column(db.String(20), default='listed')  # 'listed', 'unlisted', 'ipo', 'unicorn'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 複合唯一約束：同一用戶不能重複關注同一市場的同一股票
    __table_args__ = (db.UniqueConstraint('user_id', 'stock_symbol', 'market'),)

    def __repr__(self):
        return f'<Watchlist {self.stock_symbol}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stock_symbol': self.stock_symbol,
            'stock_name': self.stock_name,
            'market': self.market,
            'stock_type': self.stock_type,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SystemStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stat_name = db.Column(db.String(50), unique=True, nullable=False)
    stat_value = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemStats {self.stat_name}: {self.stat_value}>'

    def to_dict(self):
        return {
            'id': self.id,
            'stat_name': self.stat_name,
            'stat_value': self.stat_value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_stat(stat_name):
        """獲取統計數據"""
        stat = SystemStats.query.filter_by(stat_name=stat_name).first()
        return stat.stat_value if stat else 0
    
    @staticmethod
    def update_stat(stat_name, value):
        """更新統計數據"""
        stat = SystemStats.query.filter_by(stat_name=stat_name).first()
        if stat:
            stat.stat_value = value
            stat.updated_at = datetime.utcnow()
        else:
            stat = SystemStats(stat_name=stat_name, stat_value=value)
            db.session.add(stat)
        db.session.commit()
    
    @staticmethod
    def increment_stat(stat_name, increment=1):
        """增加統計數據"""
        current_value = SystemStats.get_stat(stat_name)
        SystemStats.update_stat(stat_name, current_value + increment)

