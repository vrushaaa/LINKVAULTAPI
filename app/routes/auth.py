# from flask import Blueprint, request, jsonify, url_for
# from flask_login import login_user, logout_user, login_required, current_user
# from app import db, bcrypt
# from app.models.user import User

# auth = Blueprint('auth', __name__)

# @auth.route('/register', methods=['POST'])
# def register_user():
#     data = request.get_json()
#     username = data.get('username')
#     password = data.get('password')

#     if User.query.filter_by(username=username).first():
#         return jsonify({'error': 'User exists'}), 400

#     user = User(username=username)
#     user.set_password(password)
#     db.session.add(user)
#     db.session.commit()

#     return jsonify({'message': 'Registered! Now login.'}), 201

# @auth.route('/login', methods=['POST'])
# def login_user():
#     data = request.get_json()
#     user = User.query.filter_by(username=data.get('username')).first()

#     if user and user.check_password(data.get('password')):
#         login_user(user)
#         return jsonify({
#             'message': 'Logged in',
#             'user': {'id': user.id, 'username': user.username}
#         })

#     return jsonify({'error': 'Invalid credentials'}), 401

# @auth.route('/logout')
# @login_required
# def logout_user():
#     logout_user()
#     return jsonify({'message': 'Logged out'})