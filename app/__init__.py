from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config
import os

# === DECLARE db & migrate FIRST ===
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

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
    def update_tag_counts(session, flush_context):
        """Update Tag.bookmark_count without triggering lazy loads during flush.

        Accessing relationship attributes (like `obj.tags`) can force a
        flush while a flush is already in progress. Instead, query the
        association table `tag_user_bookmarks` directly to collect affected
        tag ids, then update counts using SQL expressions.
        """
        tag_ids_to_update = set()

        # Collect bookmark IDs from session changes
        bookmark_ids = set()
        for obj in session.new | session.dirty | session.deleted:
            if isinstance(obj, Bookmark):
                if obj.id is not None:
                    bookmark_ids.add(obj.id)

        if not bookmark_ids:
            return

        # Find tag ids related to these bookmarks from the association table
        rows = session.execute(
            db.select(tag_user_bookmarks.c.tag_id)
            .where(tag_user_bookmarks.c.bookmark_id.in_(bookmark_ids))
        ).scalars().all()

        tag_ids_to_update.update(rows)

        # Update counts for each affected tag
        for tag_id in tag_ids_to_update:
            count = session.scalar(
                db.select(db.func.count())
                .select_from(tag_user_bookmarks)
                .where(tag_user_bookmarks.c.tag_id == tag_id)
            )
            session.execute(
                db.update(Tag)
                .where(Tag.id == tag_id)
                .values(bookmark_count=count)
            )
 # ✅ Added below lines for authentication support
    from app.auth.auth import auth  # added auth blueprint import
    app.register_blueprint(auth, url_prefix='/auth')  # registered auth blueprint
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")  # added secret key for sessions

    def http_url(url):
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return 'https://' + url
    app.jinja_env.globals.update(http_url=http_url)

    

    return app