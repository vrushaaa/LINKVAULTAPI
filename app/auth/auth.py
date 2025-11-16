# app/routes/auth.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import google
from flask_dance.contrib.github import github
from app import db, bcrypt
from app.models.user import User

auth = Blueprint('auth', __name__)

# REGISTER 
@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('bookmarks_api.dashboard'))

    # === WEB FORM SUBMISSION ===
    if request.method == 'POST' and request.form:
        name = request.form.get('name')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate all fields
        if not all([name, email, username, password]):
            flash('Please fill all fields', 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.signup'))

        # Create user
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            username=username.strip().lower()
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registered successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))

    # === API JSON SUBMISSION ===
    elif request.is_json:
        data = request.get_json()
        name = data.get('name')  # changed from full_name
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not all([name, email, username, password]):
            return jsonify({
                'error': 'All fields are required: name, email, username, password'
            }), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            username=username.strip().lower()
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return jsonify({
            'message': 'Registered successfully!',
            'user': {
                'id': user.id,
                'name': user.name,          # changed
                'email': user.email,
                'username': user.username
            }
        }), 201

    # === GET → SHOW REGISTER PAGE ===
    return render_template('signup.html')


# LOGIN 
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('bookmarks_api.dashboard'))

    # === WEB FORM LOGIN ===
    if request.method == 'POST' and request.form:
        identifier = request.form.get('username')  # can be username OR email
        password = request.form.get('password')

        if not identifier or not password:
            flash('Please fill all fields', 'error')
            return redirect(url_for('auth.login'))

        # Try login by username first, then email
        user = (
            User.query.filter_by(username=identifier.lower()).first() or
            User.query.filter_by(email=identifier.lower()).first()
        )

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('bookmarks_api.dashboard'))

        flash('Invalid username/email or password', 'error')
        return redirect(url_for('auth.login'))

    # === API JSON LOGIN ===
    elif request.is_json:
        data = request.get_json()
        identifier = data.get('username')
        password = data.get('password')

        if not identifier or not password:
            return jsonify({'error': 'username/email and password required'}), 400

        # Login via username or email
        user = (
            User.query.filter_by(username=identifier.lower()).first() or
            User.query.filter_by(email=identifier.lower()).first()
        )

        if user and user.check_password(password):
            login_user(user)
            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }), 200

        return jsonify({'error': 'Invalid credentials'}), 401

    # === GET → show login page ===
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


# app/routes/auth.py

@auth.route('/login/google')
def login_google():
    if not google.authorized:
        return redirect(url_for("google.login"))
    return redirect(url_for('auth.oauth_callback', provider='google'))

@auth.route('/login/github')
def login_github():
    if not github.authorized:
        return redirect(url_for("github.login"))
    return redirect(url_for('auth.oauth_callback', provider='github'))

# @auth.route('/auth/<provider>/callback')
# def oauth_callback(provider):
#     if provider not in ['google', 'github']:
#         flash('Invalid provider', 'error')
#         return redirect(url_for('auth.login'))

#     oauth = google if provider == 'google' else github

#     if not oauth.authorized:
#         flash(f'{provider.title()} login failed', 'error')
#         return redirect(url_for('auth.login'))

#     # === GET USER INFO ===
#     if provider == 'google':
#         resp = oauth.get("/oauth2/v1/userinfo")
#         if not resp.ok:
#             flash('Failed to fetch user info', 'error')
#             return redirect(url_for('auth.login'))
#         data = resp.json()
#         email = data['email']
#         full_name = data.get('name', '')
#         username = data['email'].split('@')[0]

#     else:  # GitHub
#         resp = oauth.get("/user")
#         if not resp.ok:
#             flash('Failed to fetch GitHub user', 'error')
#             return redirect(url_for('auth.login'))
#         user_data = resp.json()
#         email_resp = oauth.get("/user/emails")
#         email = None
#         if email_resp.ok:
#             emails = email_resp.json()
#             primary = next((e for e in emails if e['primary']), emails[0])
#             email = primary['email']
#         full_name = user_data.get('name', user_data['login'])
#         username = user_data['login']

#     if not email:
#         flash('Could not retrieve email', 'error')
#         return redirect(url_for('auth.login'))

#     # === FIND OR CREATE USER ===
#     user = User.query.filter_by(email=email).first()
#     if not user:
#         user = User(
#             full_name=full_name or username,
#             email=email,
#             username=username
#         )
#         user.set_password('oauth-' + str(user.id))  # Dummy password
#         db.session.add(user)
#         db.session.commit()
#         flash('Account created via ' + provider.title() + '!', 'success')
#     else:
#         flash('Logged in via ' + provider.title() + '!', 'success')

#     login_user(user)
#     return redirect(url_for('bookmarks_api.dashboard'))









# # auth.py
# from flask import Blueprint, render_template, request, flash, redirect, url_for
# from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, SubmitField
# from wtforms.validators import DataRequired, Email

# bp = Blueprint('auth', __name__, template_folder='templates')

# class LoginForm(FlaskForm):
#     email    = StringField('Email', validators=[DataRequired(), Email()])
#     password = PasswordField('Password', validators=[DataRequired()])
#     submit   = SubmitField('Login')

# @bp.route('/login', methods=['GET', 'POST'])
# def login():
#     form = LoginForm()
#     if form.validate_on_submit():
#         # TODO: verify credentials
#         flash('Logged in successfully!', 'success')
#         return redirect(url_for('dashboard.index'))
#     return render_template('login.html', form=form)



# # ✅ Added below lines for integration with create_app and logout functionality
# auth_bp = bp  # alias for blueprint to match create_app import  # added line

# from flask import session  # added for session handling

# @auth_bp.route('/logout')  # new logout route
# def logout():
#     session.clear()  # clear session data
#     flash('You have been logged out.', 'info')  # flash message
#     return redirect(url_for('auth.login'))  # redirect to login

# @bp.route('/signup', methods=['GET', 'POST'])
# def signup():
#     # You can later add real registration logic here
#     return render_template('signup.html')  # create this template next



@auth.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad Request', 'message': str(e.description) if hasattr(e, 'description') else 'Invalid input'}), 400

@auth.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not Found', 'message': 'Resource not found'}), 404

@auth.errorhandler(409)
def conflict(e):
    return jsonify({'error': 'Conflict', 'message': str(e.description) if hasattr(e, 'description') else 'Resource already exists'}), 409

@auth.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal Server Error', 'message': 'Something went wrong'}), 500