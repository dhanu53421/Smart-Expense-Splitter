import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# import pandas as pd
import io
import json

# Install email_validator package if not already installed
try:
    import email_validator
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "email_validator"])

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense_splitter.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit for CSRF tokens

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Import models and initialize database
from models import db
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import forms after initializing db to avoid circular imports
from forms import LoginForm, RegistrationForm, GroupForm, BillForm, ProductForm

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Import routes
from routes import *

# Currency formatting utility functions
@app.template_filter('currency_format')
def currency_format_filter(amount, currency=None):
    """Template filter to format currency amounts"""
    if currency is None and current_user.is_authenticated:
        currency = current_user.get_default_currency()
    
    if currency:
        return currency.format_amount(amount)
    else:
        # Default fallback formatting
        return f"${amount:,.2f}"

@app.template_filter('currency_format_simple')
def currency_format_simple_filter(amount, currency=None):
    """Template filter to format currency amounts without symbol"""
    if currency is None and current_user.is_authenticated:
        currency = current_user.get_default_currency()
    
    if currency:
        return currency.format_amount_simple(amount)
    else:
        # Default fallback formatting
        return f"{amount:,.2f}"

def format_amount_for_user(amount, user=None):
    """Helper function to format amount for a specific user"""
    if user is None:
        user = current_user
    
    if user and user.is_authenticated:
        currency = user.get_default_currency()
        if currency:
            return currency.format_amount(amount)
    
    # Default fallback
    return f"${amount:,.2f}"

# Run the application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)