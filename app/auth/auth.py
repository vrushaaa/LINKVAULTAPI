# app/routes/auth.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import google
from flask_dance.contrib.github import github
from itsdangerous import URLSafeTimedSerializer
from app import db, bcrypt
from app.models.user import User
from flask_mail import Message
from app import mail

auth = Blueprint('auth', __name__)

def generate_reset_token(user):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({"user_id": user.id})

def verify_reset_token(token, expiration=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token, max_age=expiration)
        return User.query.get(data["user_id"])
    except Exception:
        return None

def send_reset_email(user):
    token = generate_reset_token(user)
    reset_url = url_for("auth.reset_password", token=token, _external=True)

    msg = Message(
        subject="Reset Your Password - LinkVault",
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[user.email]
    )

    msg.body = f"""
Hi {user.username},

Click the link below to reset your password:

{reset_url}

If you did not request this, simply ignore this message.

LinkVault Security Team
"""

    mail.send(msg)

@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        if not email:
            flash("Email is required.", "error")
            return redirect(url_for("auth.forgot_password"))

        user = User.query.filter_by(email=email.lower().strip()).first()

        if user:
            send_reset_email(user)
            flash("A password reset link has been sent to your email.", "success")
            return redirect(url_for("auth.login"))

        flash("No account found with that email.", "error")
        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = verify_reset_token(token)

    if user is None:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("password")

        if not new_password:
            flash("Password cannot be empty.", "error")
            return redirect(url_for("auth.reset_password", token=token))

        user.set_password(new_password)
        db.session.commit()

        flash("Your password has been reset successfully!", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)








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





















# @auth.route("/forgot-password", methods=["GET", "POST"])
# def forgot_password():
#     if current_user.is_authenticated:
#         return redirect(url_for('bookmarks_api.dashboard'))
    
#     if request.method == "POST":
#         email = request.form.get("email")
        
#         if not email:
#             flash("Email is required", "error")
#             return render_template("forgot_password.html")
        
#         user = User.query.filter_by(email=email.lower()).first()
        
#         if user:
#             # Generate reset token
#             token = user.generate_reset_token()
            
#             # Create reset URL
#             reset_url = url_for('auth.reset_password', token=token, _external=True)
            
#             # Send email
#             try:
#                 msg = Message(
#                     'Password Reset Request - LinkVault',
#                     recipients=[user.email]
#                 )
#                 msg.body = f'''Hello {user.name},

# You requested a password reset for your LinkVault account.

# Click the link below to reset your password:
# {reset_url}

# This link will expire in 1 hour.

# If you didn't request this, please ignore this email.

# Best regards,
# LinkVault Team
# '''
#                 msg.html = f'''
#                 <h2>Password Reset Request</h2>
#                 <p>Hello {user.name},</p>
#                 <p>You requested a password reset for your LinkVault account.</p>
#                 <p><a href="{reset_url}" style="background: #c1e328; color: black; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a></p>
#                 <p>Or copy this link: <br><code>{reset_url}</code></p>
#                 <p>This link will expire in 1 hour.</p>
#                 <p>If you didn't request this, please ignore this email.</p>
#                 <hr>
#                 <p>Best regards,<br>LinkVault Team</p>
#                 '''
                
#                 mail.send(msg)
#                 flash("Password reset link sent to your email", "success")
#             except Exception as e:
#                 flash("Error sending email. Please try again.", "error")
#                 print(f"Email error: {e}")
#         else:
#             # Don't reveal if email exists (security)
#             flash("If this email exists, a reset link has been sent.", "info")
        
#         return redirect(url_for("auth.login"))
    
#     return render_template("forgot_password.html")


# @auth.route("/reset-password/<token>", methods=["GET", "POST"])
# def reset_password(token):
#     if current_user.is_authenticated:
#         return redirect(url_for('bookmarks_api.dashboard'))
    
#     user = User.verify_reset_token(token)
    
#     if not user:
#         flash("Invalid or expired reset link", "error")
#         return redirect(url_for('auth.forgot_password'))
    
#     if request.method == "POST":
#         password = request.form.get("password")
#         confirm_password = request.form.get("confirm_password")
        
#         if not password or not confirm_password:
#             flash("All fields are required", "error")
#             return render_template("reset_password.html", token=token)
        
#         if password != confirm_password:
#             flash("Passwords do not match", "error")
#             return render_template("reset_password.html", token=token)
        
#         if len(password) < 6:
#             flash("Password must be at least 6 characters", "error")
#             return render_template("reset_password.html", token=token)
        
#         # Update password
#         user.set_password(password)
#         db.session.commit()
        
#         flash("Password reset successful! Please login.", "success")
#         return redirect(url_for('auth.login'))
    
#     return render_template("reset_password.html", token=token)
