from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

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
    
    def __repr__(self):
        return f'<User {self.username}>'

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
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('Group', back_populates='bills')
    products = db.relationship('Product', back_populates='bill', cascade='all, delete-orphan')
    
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
        return f'<Product {self.name} in Bill {self.bill_id}>'
    
    @property
    def members_count(self):
        """Get the number of members involved in this product"""
        return len(self.members_involved)
    
    @property
    def payer_name(self):
        """Get the name of the member who paid for this product"""
        return self.payer.name if self.payer else 'Unknown'