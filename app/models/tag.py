from app import db

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    bookmarks = db.relationship('Bookmark', secondary='bookmark_tags', back_populates='tags')

    def __repr__(self):
        return f'<Tag {self.name}>'