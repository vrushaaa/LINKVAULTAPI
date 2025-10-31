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

    return app