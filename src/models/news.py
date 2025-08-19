from datetime import datetime
from src.models.user import db

class NewsBookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100))
    stock_symbol = db.Column(db.String(20))
    stock_name = db.Column(db.String(100))
    summary = db.Column(db.Text)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<NewsBookmark {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'stock_symbol': self.stock_symbol,
            'stock_name': self.stock_name,
            'summary': self.summary,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

