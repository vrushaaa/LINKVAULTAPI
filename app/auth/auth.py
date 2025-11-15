# auth.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email

bp = Blueprint('auth', __name__, template_folder='templates')

class LoginForm(FlaskForm):
    email    = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Login')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # TODO: verify credentials
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('login.html', form=form)



# ✅ Added below lines for integration with create_app and logout functionality
auth_bp = bp  # alias for blueprint to match create_app import  # added line

from flask import session  # added for session handling

@auth_bp.route('/logout')  # new logout route
def logout():
    session.clear()  # clear session data
    flash('You have been logged out.', 'info')  # flash message
    return redirect(url_for('auth.login'))  # redirect to login

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    # You can later add real registration logic here
    return render_template('signup.html')  # create this template next

# --- Social login placeholders (so url_for works) ---
@bp.route('/google-login')
def google_login():
    # TODO: Implement Google OAuth later
    return "Google login not yet implemented", 501  # 501 = Not Implemented


@bp.route('/github-login')
def github_login():
    # TODO: Implement GitHub OAuth later
    return "GitHub login not yet implemented", 501

