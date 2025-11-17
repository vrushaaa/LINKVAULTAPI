from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from flask import current_app



class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)          # ← NEW
    email = db.Column(db.String(120), unique=True, nullable=False)  # ← NEW
    password_hash = db.Column(db.String(255), nullable=False)

    saved_bookmarks = db.relationship(
        'UserBookmark',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'email': self.email
        }

    def __repr__(self):
        return f'<User {self.username}>'
    
    # def generate_reset_token(self):
    #     """Generate password reset token"""
    #     serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    #     return serializer.dumps(self.email, salt='password-reset-salt')

    # @staticmethod
    # def verify_reset_token(token, expiration=3600):
    #     """Verify password reset token"""
    #     serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    #     try:
    #         email = serializer.loads(
    #             token,
    #             salt='password-reset-salt',
    #             max_age=expiration
    #         )
    #         return User.query.filter_by(email=email).first()
    #     except:
    #         return None