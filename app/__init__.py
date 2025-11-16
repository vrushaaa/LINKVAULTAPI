from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import os
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.models.user import User
    from app.models.bookmark import Bookmark
    from app.models.tag import Tag
    from app.models.user_bookmark import UserBookmark
    from app.models.tag_user_bookmark import tag_user_bookmarks

    # Blueprints
    from app.routes.bookmark_routes import bp as bookmark_bp, short_bp
    from app.routes.user_routes import user_bp

    app.register_blueprint(bookmark_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(short_bp)

    # @app.route('/')
    # def welcome():
    #     from flask import render_template
    #     return render_template('landing.html'), 200

    # auto update tag_user_bookmark.bookmark_count
    from sqlalchemy import event

    @event.listens_for(db.session, "after_flush")
    def update_tag_user_counts(session, flush_context):
        # collect all (user_id, tag_id) pairs that changed
        affected = set()

        for obj in session.new | session.dirty | session.deleted:
            if isinstance(obj, UserBookmark):
                user_id = obj.user_id
                bookmark_id = obj.bookmark_id

                # get all tags for this bookmark
                tags = db.session.execute(
                    db.select(tag_user_bookmarks.c.tag_id)
                    .where(tag_user_bookmarks.c.bookmark_id == bookmark_id)
                ).scalars().all()

                for tag_id in tags:
                    affected.add((user_id, tag_id))

        # update counts
        for user_id, tag_id in affected:
            count = db.session.scalar(
                db.select(db.func.count())
                .select_from(tag_user_bookmarks)
                .where(
                    tag_user_bookmarks.c.user_id == user_id,
                    tag_user_bookmarks.c.tag_id == tag_id
                )
            )
            db.session.execute(
                db.update(tag_user_bookmarks)
                .where(
                    tag_user_bookmarks.c.user_id == user_id,
                    tag_user_bookmarks.c.tag_id == tag_id
                )
                .values(bookmark_count=count)
            )
 # ✅ Added below lines for authentication support
    from app.auth.auth import auth_bp  # added auth blueprint import
    app.register_blueprint(auth_bp, url_prefix='/auth')  # registered auth blueprint
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")  # added secret key for sessions
    

    return app