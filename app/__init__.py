import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # loading config
    from config import Config
    app.config.from_object(Config)

    #initializing
    db.init_app(app)
    migrate.init_app(app, db)


    # importing models to register with SQLAlchemy
    from app.models.bookmark import Bookmark  
    from app.models.tag import Tag      

    from app.routes.bookmark_routes import bp as bookmarks_bp
    from app.routes.bookmark_routes import short_bp

    app.register_blueprint(bookmarks_bp, url_prefix='/api')
    app.register_blueprint(short_bp)  # Root level

 # ✅ Added below lines for authentication support
    from app.auth.auth import auth_bp  # added auth blueprint import
    app.register_blueprint(auth_bp, url_prefix='/auth')  # registered auth blueprint
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")  # added secret key for sessions
    

    return app