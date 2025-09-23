from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, DateField, SelectField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, Regexp
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class GroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Create Group')

class MemberForm(FlaskForm):
    name = StringField('Member Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email()])
    mobile_number = StringField('Mobile Number', validators=[DataRequired(), Length(max=20), 
                                Regexp(r'^\+?[0-9\s\(\)\-\.]{10,20}$', message='Please enter a valid phone number format')])
    submit = SubmitField('Add Member')

class BillForm(FlaskForm):
    title = StringField('Bill Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('Food & Dining', 'Food & Dining'),
        ('Transportation', 'Transportation'),
        ('Entertainment', 'Entertainment'),
        ('Shopping', 'Shopping'),
        ('Travel', 'Travel'),
        ('Utilities', 'Utilities'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Business', 'Business'),
        ('Other', 'Other')
    ], validators=[DataRequired()], default='Other')
    submit = SubmitField('Create Bill')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    price = FloatField('Price', validators=[DataRequired()])
    payer = SelectField('Paid By', coerce=int, validators=[DataRequired()])
    members_involved = SelectMultipleField('Members Involved', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Product')

class BillTemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired(), Length(max=100)])
    title = StringField('Bill Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    category = SelectField('Category', choices=[
        ('Food & Dining', 'Food & Dining'),
        ('Transportation', 'Transportation'),
        ('Entertainment', 'Entertainment'),
        ('Shopping', 'Shopping'),
        ('Travel', 'Travel'),
        ('Utilities', 'Utilities'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Business', 'Business'),
        ('Other', 'Other')
    ], validators=[DataRequired()], default='Other')
    submit = SubmitField('Save Template')

class TemplateProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    price = FloatField('Price', validators=[DataRequired()])
    submit = SubmitField('Add Product')

class CurrencySettingsForm(FlaskForm):
    default_currency = SelectField('Default Currency', coerce=int, validators=[DataRequired()])
    currencies = SelectMultipleField('Active Currencies', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Currency Settings')
    
    def __init__(self, user_id=None, *args, **kwargs):
        super(CurrencySettingsForm, self).__init__(*args, **kwargs)
        from models import Currency, UserCurrency
        # Get all active currencies
        active_currencies = Currency.query.filter_by(is_active=True).all()
        self.default_currency.choices = [(c.id, f"{c.code} - {c.name}") for c in active_currencies]
        self.currencies.choices = [(c.id, f"{c.code} - {c.name}") for c in active_currencies]

class AddCurrencyForm(FlaskForm):
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    make_default = BooleanField('Make this my default currency')
    submit = SubmitField('Add Currency')
    
    def __init__(self, user_id=None, *args, **kwargs):
        super(AddCurrencyForm, self).__init__(*args, **kwargs)
        from models import Currency, UserCurrency
        # Get currencies not already added by user
        if user_id:
            user_currency_ids = [uc.currency_id for uc in UserCurrency.query.filter_by(user_id=user_id, is_active=True).all()]
            available_currencies = Currency.query.filter(
                Currency.is_active == True,
                ~Currency.id.in_(user_currency_ids)
            ).all()
        else:
            available_currencies = Currency.query.filter_by(is_active=True).all()
        
        self.currency_id.choices = [(c.id, f"{c.code} - {c.name}") for c in available_currencies]