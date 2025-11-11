from app import db
from app.models.user_bookmark import user_bookmarks

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    saved_bookmarks = db.relationship(
        'Bookmark',
        secondary=user_bookmarks,
        backref=db.backref('saved_by_users', lazy='dynamic'),
        lazy='dynamic'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }