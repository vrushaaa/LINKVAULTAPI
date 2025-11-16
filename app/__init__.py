# app/__init__.py
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# === DECLARE db & migrate FIRST ===
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # === INIT EXTENSIONS ===
    db.init_app(app)
    migrate.init_app(app, db)

    # === NOW IMPORT MODELS (after db is ready) ===
    from app.models.bookmark import Bookmark
    from app.models.tag import Tag
    from app.models.tag_user_bookmark import tag_user_bookmarks

    # === REGISTER BLUEPRINTS ===
    from app.routes.bookmark_routes import bp
    from app.routes.bookmark_routes import short_bp
    app.register_blueprint(bp, url_prefix='/api')
    app.register_blueprint(short_bp)

    # === WELCOME ROUTE ===
    @app.route('/')
    def welcome():
        return render_template('welcome.html'), 200

    # === AUTO UPDATE Tag.bookmark_count ===
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

    return app