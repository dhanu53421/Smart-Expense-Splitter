from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

# Create db instance that will be initialized in the main app
db = SQLAlchemy()

# Association table for many-to-many relationship between Product and Member
class ProductMember(db.Model):
    __tablename__ = 'product_members'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    
    # Define unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('product_id', 'member_id'),)
    
    # Relationships
    product = db.relationship('Product', back_populates='members_involved')
    member = db.relationship('Member', back_populates='products_involved')

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    groups = db.relationship('Group', back_populates='user', cascade='all, delete-orphan')
    bill_templates = db.relationship('BillTemplate', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def get_total_expenses(self):
        """Get total expenses across all groups"""
        total = 0
        for group in self.groups:
            total += group.get_total_expenses()
        return total
    
    def get_expenses_by_category(self):
        """Get expenses grouped by category across all groups"""
        category_totals = {}
        for group in self.groups:
            group_categories = group.get_expenses_by_category()
            for category, amount in group_categories.items():
                category_totals[category] = category_totals.get(category, 0) + amount
        return category_totals
    
    def get_monthly_expenses(self, year=None, month=None):
        """Get monthly expenses for a specific month or all months"""
        if year is None:
            year = datetime.now().year
        
        monthly_totals = {}
        for group in self.groups:
            group_monthly = group.get_monthly_expenses(year)
            for month_key, amount in group_monthly.items():
                monthly_totals[month_key] = monthly_totals.get(month_key, 0) + amount
        
        if month is not None:
            month_key = f"{year}-{month:02d}"
            return monthly_totals.get(month_key, 0)
        
        return monthly_totals
    
    def get_default_currency(self):
        """Get the user's default currency"""
        default = UserCurrency.query.filter_by(user_id=self.id, is_default=True, is_active=True).first()
        if default:
            return default.currency
        return None
    
    def get_active_currencies(self):
        """Get all active currencies for the user"""
        return [uc.currency for uc in UserCurrency.query.filter_by(user_id=self.id, is_active=True).all()]
    
    def add_currency(self, currency_id, is_default=False):
        """Add a currency to user's active currencies"""
        currency = Currency.query.get(currency_id)
        if not currency or not currency.is_active:
            return False
        
        # Check if currency already exists for user
        existing = UserCurrency.query.filter_by(user_id=self.id, currency_id=currency_id).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.is_default = is_default
                db.session.commit()
            return True
        
        # If this is the first currency or is_default is True, make it default
        if is_default or not self.get_active_currencies():
            # Remove existing default
            UserCurrency.query.filter_by(user_id=self.id, is_default=True).update({'is_default': False})
        
        user_currency = UserCurrency(
            user_id=self.id,
            currency_id=currency_id,
            is_default=is_default or not self.get_active_currencies()
        )
        db.session.add(user_currency)
        db.session.commit()
        return True
    
    def remove_currency(self, currency_id):
        """Remove a currency from user's active currencies"""
        user_currency = UserCurrency.query.filter_by(user_id=self.id, currency_id=currency_id, is_active=True).first()
        if not user_currency:
            return False
        
        # Check if this is the last currency
        active_currencies = UserCurrency.query.filter_by(user_id=self.id, is_active=True).count()
        if active_currencies <= 1:
            return False  # Cannot remove the last currency
        
        # If this was the default, set another currency as default
        if user_currency.is_default:
            user_currency.is_active = False
            user_currency.is_default = False
            
            # Find another active currency to make default
            other_currency = UserCurrency.query.filter_by(user_id=self.id, is_active=True).first()
            if other_currency:
                other_currency.is_default = True
        else:
            user_currency.is_active = False
        
        db.session.commit()
        return True
    
    def set_default_currency(self, currency_id):
        """Set a currency as default for the user"""
        user_currency = UserCurrency.query.filter_by(user_id=self.id, currency_id=currency_id, is_active=True).first()
        if not user_currency:
            return False
        
        # Remove existing default
        UserCurrency.query.filter_by(user_id=self.id, is_default=True).update({'is_default': False})
        
        # Set new default
        user_currency.is_default = True
        db.session.commit()
        return True

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='groups')
    members = db.relationship('Member', back_populates='group', cascade='all, delete-orphan')
    bills = db.relationship('Bill', back_populates='group', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Group {self.name}>'
    
    def get_total_expenses(self):
        """Get total expenses for this group"""
        total = 0
        for bill in self.bills:
            total += bill.get_total_amount()
        return total
    
    def get_expenses_by_category(self):
        """Get expenses grouped by category for this group"""
        category_totals = {}
        for bill in self.bills:
            category = bill.category
            amount = bill.get_total_amount()
            category_totals[category] = category_totals.get(category, 0) + amount
        return category_totals
    
    def get_monthly_expenses(self, year=None):
        """Get monthly expenses for this group"""
        if year is None:
            year = datetime.now().year
        
        monthly_totals = {}
        for bill in self.bills:
            if bill.date.year == year:
                month_key = f"{bill.date.year}-{bill.date.month:02d}"
                monthly_totals[month_key] = monthly_totals.get(month_key, 0) + bill.get_total_amount()
        
        return monthly_totals
    
    def get_member_expenses(self, member_id):
        """Get expenses for a specific member in this group"""
        member_total = 0
        for bill in self.bills:
            member_summary = bill.get_member_summary()
            if member_id in member_summary:
                member_total += member_summary[member_id]['owes']
        return member_total
    
    def get_top_categories(self, limit=5):
        """Get top expense categories"""
        categories = self.get_expenses_by_category()
        return sorted(categories.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_average_bill_amount(self):
        """Get average bill amount for this group"""
        if not self.bills:
            return 0
        total = self.get_total_expenses()
        return total / len(self.bills)

class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    mobile_number = db.Column(db.String(20), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('Group', back_populates='members')
    paid_products = db.relationship('Product', back_populates='payer')
    products_involved = db.relationship('ProductMember', back_populates='member', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Member {self.name} in Group {self.group_id}>'

class Bill(db.Model):
    __tablename__ = 'bills'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    date = db.Column(db.Date, default=datetime.utcnow().date)
    category = db.Column(db.String(50), default='Other')
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('Group', back_populates='bills')
    products = db.relationship('Product', back_populates='bill', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<BillTemplate {self.name}>'
    
    def get_total_amount(self):
        return sum(product.price for product in self.products)
    
    def get_member_summary(self):
        """Calculate what each member owes or is owed with detailed breakdown"""
        summary = {}
        
        # Initialize summary for each member in the group
        for member in self.group.members:
            summary[member.id] = {
                'member': member,
                'paid': 0,  # Total amount paid by this member
                'owes': 0,  # Total amount this member owes
                'products': [],  # Products this member is involved in
                'net': 0,  # Net amount (positive means others owe this member)
                'paid_products': [],  # Products paid by this member
                'shared_products': []  # Products shared by this member
            }
        
        # Calculate amounts for each product
        for product in self.products:
            # Add to payer's paid amount
            payer_id = product.payer_id
            summary[payer_id]['paid'] += product.price
            summary[payer_id]['paid_products'].append(product)
            
            # Calculate each member's share for this product
            involved_members = [pm.member_id for pm in product.members_involved]
            if involved_members:
                share_per_member = round(product.price / len(involved_members), 2)
                
                # Add share to each involved member's owed amount
                for member_id in involved_members:
                    summary[member_id]['owes'] += share_per_member
                    summary[member_id]['shared_products'].append(product)
                    
                    # Add product details to member's products list
                    other_members = [m for m in involved_members if m != member_id]
                    summary[member_id]['products'].append({
                        'product': product,
                        'share': share_per_member,
                        'shared_with': other_members,
                        'payer': product.payer,
                        'is_payer': member_id == payer_id
                    })
        
        # Calculate net amount for each member
        for member_id, data in summary.items():
            data['net'] = round(data['paid'] - data['owes'], 2)
            data['paid'] = round(data['paid'], 2)
            data['owes'] = round(data['owes'], 2)
        
        return summary
    
    def get_settlement_summary(self):
        """Generate a list of transactions to settle all debts with detailed information"""
        member_summary = self.get_member_summary()
        
        # Extract members with positive and negative balances
        creditors = []
        debtors = []
        
        for member_id, data in member_summary.items():
            if data['net'] > 0:
                creditors.append((member_id, data['net']))
            elif data['net'] < 0:
                debtors.append((member_id, abs(data['net'])))
        
        # Sort by amount (descending)
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)
        
        # Generate settlement transactions
        transactions = []
        
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor_id, debt = debtors[i]
            creditor_id, credit = creditors[j]
            
            # Calculate transaction amount
            amount = min(debt, credit)
            
            # Get the members involved
            debtor = member_summary[debtor_id]['member']
            creditor = member_summary[creditor_id]['member']
            
            # Find shared products between these members
            shared_products = []
            for product in self.products:
                debtor_involved = any(pm.member_id == debtor_id for pm in product.members_involved)
                creditor_involved = any(pm.member_id == creditor_id for pm in product.members_involved)
                creditor_paid = product.payer_id == creditor_id
                
                if debtor_involved and creditor_paid:
                    shared_products.append(product)
            
            # Create transaction with detailed information
            transactions.append({
                'from_member': debtor,
                'to_member': creditor,
                'amount': round(amount, 2),
                'shared_products': shared_products,
                'debtor_total_owed': member_summary[debtor_id]['owes'],
                'creditor_total_paid': member_summary[creditor_id]['paid'],
                'transaction_id': f"T-{debtor_id}-{creditor_id}"
            })
            
            # Update remaining amounts
            debtors[i] = (debtor_id, debt - amount)
            creditors[j] = (creditor_id, credit - amount)
            
            # Move to next member if their balance is settled
            if debtors[i][1] < 0.01:  # Using small threshold to handle floating point errors
                i += 1
            if creditors[j][1] < 0.01:
                j += 1
        
        return transactions

class BillTemplate(db.Model):
    __tablename__ = 'bill_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    category = db.Column(db.String(50), default='Other')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='bill_templates')
    template_products = db.relationship('TemplateProduct', back_populates='bill_template', cascade='all, delete-orphan')

class TemplateProduct(db.Model):
    __tablename__ = 'template_products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    bill_template_id = db.Column(db.Integer, db.ForeignKey('bill_templates.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bill_template = db.relationship('BillTemplate', back_populates='template_products')
    
    def __repr__(self):
        return f'<Bill {self.title} for Group {self.group_id}>'
    
    def get_total_amount(self):
        return sum(product.price for product in self.products)
    
    def get_member_summary(self):
        """Calculate what each member owes or is owed with detailed breakdown"""
        summary = {}
        
        # Initialize summary for each member in the group
        for member in self.group.members:
            summary[member.id] = {
                'member': member,
                'paid': 0,  # Total amount paid by this member
                'owes': 0,  # Total amount this member owes
                'products': [],  # Products this member is involved in
                'net': 0,  # Net amount (positive means others owe this member)
                'paid_products': [],  # Products paid by this member
                'shared_products': []  # Products shared by this member
            }
        
        # Calculate amounts for each product
        for product in self.products:
            # Add to payer's paid amount
            payer_id = product.payer_id
            summary[payer_id]['paid'] += product.price
            summary[payer_id]['paid_products'].append(product)
            
            # Calculate each member's share for this product
            involved_members = [pm.member_id for pm in product.members_involved]
            if involved_members:
                share_per_member = round(product.price / len(involved_members), 2)
                
                # Add share to each involved member's owed amount
                for member_id in involved_members:
                    summary[member_id]['owes'] += share_per_member
                    summary[member_id]['shared_products'].append(product)
                    
                    # Add product details to member's products list
                    other_members = [m for m in involved_members if m != member_id]
                    summary[member_id]['products'].append({
                        'product': product,
                        'share': share_per_member,
                        'shared_with': other_members,
                        'payer': product.payer,
                        'is_payer': member_id == payer_id
                    })
        
        # Calculate net amount for each member
        for member_id, data in summary.items():
            data['net'] = round(data['paid'] - data['owes'], 2)
            data['paid'] = round(data['paid'], 2)
            data['owes'] = round(data['owes'], 2)
        
        return summary
    
    def get_settlement_summary(self):
        """Generate a list of transactions to settle all debts with detailed information"""
        member_summary = self.get_member_summary()
        
        # Extract members with positive and negative balances
        creditors = []
        debtors = []
        
        for member_id, data in member_summary.items():
            if data['net'] > 0:
                creditors.append((member_id, data['net']))
            elif data['net'] < 0:
                debtors.append((member_id, abs(data['net'])))
        
        # Sort by amount (descending)
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)
        
        # Generate settlement transactions
        transactions = []
        
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor_id, debt = debtors[i]
            creditor_id, credit = creditors[j]
            
            # Calculate transaction amount
            amount = min(debt, credit)
            
            # Get the members involved
            debtor = member_summary[debtor_id]['member']
            creditor = member_summary[creditor_id]['member']
            
            # Find shared products between these members
            shared_products = []
            for product in self.products:
                debtor_involved = any(pm.member_id == debtor_id for pm in product.members_involved)
                creditor_involved = any(pm.member_id == creditor_id for pm in product.members_involved)
                creditor_paid = product.payer_id == creditor_id
                
                if debtor_involved and creditor_paid:
                    shared_products.append(product)
            
            # Create transaction with detailed information
            transactions.append({
                'from_member': debtor,
                'to_member': creditor,
                'amount': round(amount, 2),
                'shared_products': shared_products,
                'debtor_total_owed': member_summary[debtor_id]['owes'],
                'creditor_total_paid': member_summary[creditor_id]['paid'],
                'transaction_id': f"T-{debtor_id}-{creditor_id}"
            })
            
            # Update remaining amounts
            debtors[i] = (debtor_id, debt - amount)
            creditors[j] = (creditor_id, credit - amount)
            
            # Move to next member if their balance is settled
            if debtors[i][1] < 0.01:  # Using small threshold to handle floating point errors
                i += 1
            if creditors[j][1] < 0.01:
                j += 1
        
        return transactions

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bill = db.relationship('Bill', back_populates='products')
    payer = db.relationship('Member', back_populates='paid_products')
    members_involved = db.relationship('ProductMember', back_populates='product', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Product {self.name} in Bill {self.id}>'
    
    @property
    def members_count(self):
        """Get the number of members involved in this product"""
        return len(self.members_involved)
    
    @property
    def payer_name(self):
        """Get the name of the member who paid for this product"""
        return self.payer.name if self.payer else 'Unknown'

class Currency(db.Model):
    __tablename__ = 'currencies'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)  # ISO 4217 code (USD, EUR, etc.)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    decimal_places = db.Column(db.Integer, default=2)
    exchange_rate = db.Column(db.Float, default=1.0)  # Rate relative to base currency
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def format_amount(self, amount):
        """Format amount according to currency rules"""
        if not amount:
            amount = 0
        
        # Handle different currency formatting
        if self.code == 'USD':
            return f"${amount:,.2f}"
        elif self.code == 'EUR':
            # European format: €1.234,56
            return f"€{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        elif self.code == 'GBP':
            return f"£{amount:,.2f}"
        elif self.code == 'JPY':
            return f"¥{int(amount):,}"
        elif self.code == 'INR':
            return f"₹{amount:,.2f}"
        elif self.code == 'CNY':
            return f"¥{amount:,.2f}"
        else:
            # Default format
            return f"{self.symbol}{amount:,.2f}"

    def format_amount_simple(self, amount):
        """Simple format without currency symbol"""
        if not amount:
            amount = 0
        return f"{amount:,.2f}"

    def __repr__(self):
        return f'<Currency {self.code} - {self.name}>'
    
    def format_amount(self, amount):
        """Format amount according to currency settings"""
        formatted = f"{self.symbol}{amount:,.{self.decimal_places}f}"
        return formatted
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'symbol': self.symbol,
            'decimal_places': self.decimal_places,
            'exchange_rate': self.exchange_rate,
            'is_active': self.is_active
        }

class UserCurrency(db.Model):
    __tablename__ = 'user_currencies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='user_currencies')
    currency = db.relationship('Currency', backref='user_currencies')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'currency_id'),)
    
    def __repr__(self):
        return f'<UserCurrency User:{self.user_id} Currency:{self.currency_id} Default:{self.is_default}>'

# Add currency relationship to User model
User.currencies = db.relationship('UserCurrency', back_populates='user', cascade='all, delete-orphan')

def populate_initial_currencies():
    """Populate the database with common currencies"""
    currencies = [
        {'code': 'USD', 'name': 'US Dollar', 'symbol': '$', 'decimal_places': 2},
        {'code': 'EUR', 'name': 'Euro', 'symbol': '€', 'decimal_places': 2},
        {'code': 'GBP', 'name': 'British Pound', 'symbol': '£', 'decimal_places': 2},
        {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥', 'decimal_places': 0},
        {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'C$', 'decimal_places': 2},
        {'code': 'AUD', 'name': 'Australian Dollar', 'symbol': 'A$', 'decimal_places': 2},
        {'code': 'CHF', 'name': 'Swiss Franc', 'symbol': 'CHF', 'decimal_places': 2},
        {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': '¥', 'decimal_places': 2},
        {'code': 'INR', 'name': 'Indian Rupee', 'symbol': '₹', 'decimal_places': 2},
        {'code': 'KRW', 'name': 'South Korean Won', 'symbol': '₩', 'decimal_places': 0},
        {'code': 'BRL', 'name': 'Brazilian Real', 'symbol': 'R$', 'decimal_places': 2},
        {'code': 'MXN', 'name': 'Mexican Peso', 'symbol': '$', 'decimal_places': 2},
        {'code': 'SGD', 'name': 'Singapore Dollar', 'symbol': 'S$', 'decimal_places': 2},
        {'code': 'HKD', 'name': 'Hong Kong Dollar', 'symbol': 'HK$', 'decimal_places': 2},
        {'code': 'SEK', 'name': 'Swedish Krona', 'symbol': 'kr', 'decimal_places': 2},
        {'code': 'NOK', 'name': 'Norwegian Krone', 'symbol': 'kr', 'decimal_places': 2},
        {'code': 'NZD', 'name': 'New Zealand Dollar', 'symbol': 'NZ$', 'decimal_places': 2},
        {'code': 'PLN', 'name': 'Polish Zloty', 'symbol': 'zł', 'decimal_places': 2},
        {'code': 'DKK', 'name': 'Danish Krone', 'symbol': 'kr', 'decimal_places': 2},
        {'code': 'CZK', 'name': 'Czech Koruna', 'symbol': 'Kč', 'decimal_places': 2}
    ]
    
    for currency_data in currencies:
        existing = Currency.query.filter_by(code=currency_data['code']).first()
        if not existing:
            currency = Currency(**currency_data)
            db.session.add(currency)
    
    db.session.commit()