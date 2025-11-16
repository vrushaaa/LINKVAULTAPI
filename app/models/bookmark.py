from datetime import datetime

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
    url = db.Column(db.String(500), nullable=False)
    short_url = db.Column(db.String(20), unique=True)  #e.g. x7k9p
    hash_url = db.Column(db.String(64), unique=True, nullable=False)  #SHA-256
    title = db.Column(db.String(200))
    notes = db.Column(db.Text)
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    tags = db.relationship('Tag', secondary=bookmark_tags, back_populates='bookmarks')

    def set_hash(self):
        self.hash_url = generate_url_hash(self.url)

    def set_short_url(self):
        self.short_url = self.generate_short_code()

    def __repr__(self):
        return f'<Bookmark {self.short_url or self.url}>'
    
    def to_dict(self):
        ist = pytz.timezone('Asia/Kolkata')
        created_ist = self.created_at.replace(tzinfo=pytz.UTC).astimezone(ist)
        return {
            'id': self.id,
            'url': self.url,
            'hash_url': self.hash_url,
            'short_url': self.short_url,
            'full_short_url': url_for('short.redirect_short', short_code=self.short_url, _external=True),
            'tags': [t.name for t in self.tags]
        }
    
    # add user 