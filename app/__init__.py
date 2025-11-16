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

    app.register_blueprint(bookmarks_bp, url_prefix='/api')
    app.register_blueprint(short_bp)  # Root level

    

    return app