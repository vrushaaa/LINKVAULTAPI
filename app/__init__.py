import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt



login_manager = LoginManager()
bcrypt = Bcrypt()

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return User.query.get(int(user_id))

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access your bookmarks.'
login_manager.login_message_category = 'info'


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
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # importing models to register with SQLAlchemy
    from app.models.bookmark import Bookmark  
    from app.models.tag import Tag      

    from app.routes.bookmark_routes import bp as bookmarks_bp
    from app.routes.bookmark_routes import short_bp
    from app.auth import auth as auth_bp
    # from app.routes.auth import auth as auth_bp


    app.register_blueprint(bookmarks_bp, url_prefix='/api')
    app.register_blueprint(short_bp)  # Root level
    app.register_blueprint(auth_bp, url_prefix='/api')
    

    return app