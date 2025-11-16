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
    from app.models.bookmark import Bookmark, bookmark_tags
    from app.models.tag import Tag

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
        tag_ids_to_update = set()

        for obj in session.new | session.dirty | session.deleted:
            if isinstance(obj, Bookmark):
                # Current tags
                for tag in obj.tags:
                    tag_ids_to_update.add(tag.id)

                # If deleted, get old tags from DB
                if obj in session.deleted:
                    old_tags = db.session.execute(
                        db.select(bookmark_tags.c.tag_id)
                        .where(bookmark_tags.c.bookmark_id == obj.id)
                    ).scalars().all()
                    tag_ids_to_update.update(old_tags)

        # Update counts
        for tag_id in tag_ids_to_update:
            count = db.session.scalar(
                db.select(db.func.count())
                .select_from(bookmark_tags)
                .where(bookmark_tags.c.tag_id == tag_id)
            )
            db.session.execute(
                db.update(Tag)
                .where(Tag.id == tag_id)
                .values(bookmark_count=count)
            )

    return app