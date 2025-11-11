from app import db
from datetime import datetime

user_bookmarks = db.Table('user_bookmarks',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('bookmark_id', db.Integer, db.ForeignKey('bookmark.id'), primary_key=True),
    db.Column('saved_at', db.DateTime, default=datetime.utcnow),
    db.Column('notes', db.Text, nullable=True),
    db.Column('archived', db.Boolean, default=False)
)