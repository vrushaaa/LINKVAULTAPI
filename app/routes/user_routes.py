from flask import Blueprint, request, jsonify
from app.models.user import User
from app.models.bookmark import Bookmark
from app.models.tag import Tag
from app import db
from sqlalchemy.exc import IntegrityError
import re

bp = Blueprint('user', __name__, url_prefix='/api/users')

#util for validating email
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# creat user
@bp.route('', methods=['POST'])
def create_user():
    data = request.get_json(silent=True)

    # 1. Missing JSON
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    # 2. Missing fields
    username = data.get('username')
    email = data.get('email')

    if not username or not email:
        return jsonify({'error': 'Missing username or email'}), 400

    # 3. Username validation
    if len(username.strip()) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if not username.replace('_', '').replace('-', '').isalnum():
        return jsonify({'error': 'Username can only contain letters, numbers, _ and -'}), 400

    # 4. Email validation
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # 5. Check duplicates
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    try:
        user = User(username=username.strip(), email=email.strip())
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Database error: could not create user'}), 500

#get user bookmarkss
@bp.route('/<int:user_id>/bookmarks', methods=['GET'])
def get_user_bookmarks(user_id):
    # 1. User not found
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    query = Bookmark.query.filter_by(user_id=user.id)

    # 2. Filter by tag
    tag = request.args.get('tag')
    if tag:
        tag = tag.strip().lower()
        if not tag:
            return jsonify({'error': 'Tag cannot be empty'}), 400
        query = query.join(Bookmark.tags).filter(Tag.name == tag)

    # 3. Filter by archived
    archived = request.args.get('archived')
    if archived is not None:
        if archived.lower() not in ['true', 'false']:
            return jsonify({'error': 'archived must be true or false'}), 400
        archived_bool = archived.lower() == 'true'
        query = query.filter(Bookmark.archived == archived_bool)

    try:
        bookmarks = query.order_by(Bookmark.created_at.desc()).all()
        return jsonify([b.to_dict() for b in bookmarks]), 200
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve bookmarks', 'details': str(e)}), 500

@bp.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad Request', 'message': str(e.description) if hasattr(e, 'description') else 'Invalid input'}), 400

@bp.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not Found', 'message': 'Resource not found'}), 404

@bp.errorhandler(409)
def conflict(e):
    return jsonify({'error': 'Conflict', 'message': str(e.description) if hasattr(e, 'description') else 'Resource already exists'}), 409

@bp.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal Server Error', 'message': 'Something went wrong'}), 500