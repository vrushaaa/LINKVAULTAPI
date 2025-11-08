import os
from flask import Flask, jsonify,request, current_app
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

    #global error handling for undefined routes
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested endpoint does not exist',
            'available_endpoints': [
                'POST /api/bookmarks',
                'GET /api/bookmarks/',
                'GET /api/bookmarks/<id>',
                'PUT /api/bookmarks/<id>',
                'DELETE /api/bookmarks/<id>',
                'GET /api/export',
                'GET /<short_code>'
            ]
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'Method Not Allowed',
            'message': f'Method {request.method} not allowed for {request.path}',
            'allowed_methods': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        }), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        current_app.logger.error(f'Unhandled Exception: {error}', exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Something went wrong. Please try again later.'
        }), 500

    app.register_blueprint(bookmarks_bp, url_prefix='/api')
    app.register_blueprint(short_bp)  # Root level

    return app