# from datetime import datetime

# from flask import url_for
# import pytz
# from app import db
# import hashlib
# from urllib.parse import urlparse, urlunparse

# from app.models.user import User

# # association table for many-to-many
# bookmark_tags = db.Table(
#     'bookmark_tags',
#     db.Column('bookmark_id', db.Integer, db.ForeignKey('bookmark.id'), primary_key=True),
#     db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
# )

# def normalize_url(url: str) -> str:
#     """Normalize URL for hashing and deduplication."""
#     parsed = urlparse(url)
#     normalized = urlunparse((
#         parsed.scheme.lower(),
#         parsed.netloc.lower(),
#         parsed.path,
#         parsed.params,
#         parsed.query,
#         ''  # no fragment
#     ))
#     return normalized

# def generate_url_hash(url: str) -> str:
#     norm_url = normalize_url(url)
#     return hashlib.sha256(norm_url.encode('utf-8')).hexdigest()

# class Bookmark(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     url = db.Column(db.String(500), nullable=False)
#     short_url = db.Column(db.String(20), unique=True)
#     hash_url = db.Column(db.String(64), unique=True, nullable=False)
#     title = db.Column(db.String(200))
#     notes = db.Column(db.Text)
#     archived = db.Column(db.Boolean, default=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#      # relationships
#     tags = db.relationship('Tag', secondary=bookmark_tags, back_populates='bookmarks')

#     def set_hash(self):
#         self.hash_url = generate_url_hash(self.url)

#     def generate_short_code(self):
#         """Generate 6-char short code from hash."""
#         import base64
#         short = base64.urlsafe_b64encode(bytes.fromhex(self.hash_url[:12])).decode('utf-8').rstrip('=')
#         return short[:6]

#     def set_short_url(self):
#         self.short_url = self.generate_short_code()

#     def __repr__(self):
#         return f'<Bookmark {self.short_url or self.url}>'
    
#     # def to_dict(self):
#     #     ist = pytz.timezone('Asia/Kolkata')
#     #     created_ist = self.created_at.replace(tzinfo=pytz.UTC).astimezone(ist)
        
#     #     # Get owner via backref
#     #     owner = None
#     #     if self.saved_by_users:
#     #         owner = self.saved_by_users[0].username  # or loop if multiple

#     #     return {
#     #         'id': self.id,
#     #         'url': self.url,
#     #         'short_url': self.short_url,
#     #         'full_short_url': url_for('short.redirect_short', short_code=self.short_url, _external=True),
#     #         'title': self.title,
#     #         'notes': self.notes,
#     #         'archived': self.archived,
#     #         'created_at': created_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
#     #         'tags': [t.name for t in self.tags],
#     #         'owner': owner
#     #     }

#     def to_dict(self, user_id=None):
#         ist = pytz.timezone('Asia/Kolkata')
#         created_ist = self.created_at.replace(tzinfo=pytz.UTC).astimezone(ist)
#         user_data = None
#         if user_id:
#             from app.models.user_bookmark import user_bookmarks
#             stmt = user_bookmarks.select().where(
#                 user_bookmarks.c.user_id == user_id,
#                 user_bookmarks.c.bookmark_id == self.id
#             )
#             result = db.session.execute(stmt).first()
#             if result:
#                 user_data = {
#                     'notes': result.notes,
#                     'archived': result.archived
#                 }

#         return {
#             'id': self.id,
#             'url': self.url,
#             'short_url': self.short_url,
#             'full_short_url': url_for('short.redirect_short', short_code=self.short_url, _external=True),
#             'title': self.title,
#             'notes': user_data['notes'] if user_data else self.notes,
#             'archived': user_data['archived'] if user_data else self.archived,
#             'created_at': created_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
#             'tags': [t.name for t in self.tags],
#         }

# app/models/bookmark.py
from app import db
from .user_bookmark import UserBookmark
import secrets
import string
from urllib.parse import urlparse
from flask import url_for

def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')

def generate_url_hash(url: str) -> str:
    import hashlib
    return hashlib.sha256(url.encode()).hexdigest()[:16]

class Bookmark(db.Model):
    __tablename__ = 'bookmark'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(2048), nullable=False, unique=True)
    hash_url = db.Column(db.String(32), nullable=False, unique=True)
    short_url = db.Column(db.String(20), nullable=False, unique=True)

    # relationships
    user_bookmarks = db.relationship(
        'UserBookmark',
        back_populates='bookmark',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    tags = db.relationship(
        'Tag',
        secondary='tag_user_bookmark',
        back_populates='bookmarks',
        lazy='dynamic'
    )

    def set_hash(self):
        self.hash_url = generate_url_hash(self.url)

    def set_short_url(self):
        self.short_url = generate_short_code()

    def to_dict(self, user_id=None):
        data = {
            'id': self.id,
            'url': self.url,
            'hash_url': self.hash_url,
            'short_url': self.short_url,
            'full_short_url': url_for('short.redirect_short', short_code=self.short_url, _external=True),
            'tags': [t.name for t in self.tags]
        }
        if user_id:
            ub = self.user_bookmarks.filter_by(user_id=user_id).first()
            if ub:
                data.update({
                    'title': ub.title,
                    'notes': ub.notes,
                    'archived': ub.archived,
                    'created_at': ub.created_at.isoformat() + 'Z',
                    'updated_at': ub.updated_at.isoformat() + 'Z' if ub.updated_at else None
                })
        return data