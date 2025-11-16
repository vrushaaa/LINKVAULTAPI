# app/routes/auth.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models.user import User

auth = Blueprint('auth', __name__)

# REGISTER 
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('bookmark_routes.dashboard'))

    # Web form submit 
    if request.method == 'POST' and request.form:
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please fill all fields', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registered successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))

    # API JSON submit
    elif request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return jsonify({'message': 'Registered successfully!'}), 201

    # GET → show page
    return render_template('register.html')


# LOGIN 
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('bookmark_routes.dashboard'))

    # Web form
    if request.method == 'POST' and request.form:
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('bookmarks_api.dashboard'))

        flash('Invalid credentials', 'error')
        return redirect(url_for('auth.login'))

    # API JSON
    elif request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return jsonify({
                'message': 'Login successful',
                'user': {'id': user.id, 'username': user.username}
            }), 200

        return jsonify({'error': 'Invalid credentials'}), 401

    # GET → show login page
    return render_template('login.html')


# LOGOUT 
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    
    # If request was JSON → return JSON
    if request.is_json:
        return jsonify({'message': 'Logged out'}), 200
    
    # Otherwise → web redirect
    return redirect(url_for('auth.login'))