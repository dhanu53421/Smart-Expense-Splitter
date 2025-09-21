from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from smart_expense_splitter import app, db
from models import User, Group, Member, Bill, Product, ProductMember
from forms import LoginForm, RegistrationForm, GroupForm, MemberForm, BillForm, ProductForm
from datetime import datetime
import pandas as pd
import io

# Index route
@app.route('/')
def index():
    return render_template('index.html')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not check_password_hash(user.password_hash, form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.password_hash = generate_password_hash(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    groups = Group.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', title='Dashboard', groups=groups)

# Group routes
@app.route('/group/new', methods=['GET', 'POST'])
@login_required
def new_group():
    form = GroupForm()
    if form.validate_on_submit():
        group = Group(
            name=form.name.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(group)
        db.session.commit()
        flash(f'Group "{form.name.data}" created successfully!', 'success')
        return redirect(url_for('group_detail', group_id=group.id))
    return render_template('create_group.html', title='New Group', form=form, group=None)

@app.route('/group/<int:group_id>')
@login_required
def group_detail(group_id):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        flash('You do not have permission to view this group.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('group_detail.html', title=group.name, group=group)

@app.route('/group/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        flash('You do not have permission to edit this group.', 'danger')
        return redirect(url_for('dashboard'))
    form = GroupForm(obj=group)
    if form.validate_on_submit():
        group.name = form.name.data
        group.description = form.description.data
        db.session.commit()
        flash(f'Group "{form.name.data}" updated successfully!', 'success')
        return redirect(url_for('group_detail', group_id=group.id))
    return render_template('edit_group.html', title='Edit Group', form=form, group=group)

@app.route('/group/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        flash('You do not have permission to delete this group.', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(group)
    db.session.commit()
    flash(f'Group "{group.name}" deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

# Member routes
@app.route('/group/<int:group_id>/member/new', methods=['GET', 'POST'])
@login_required
def new_member(group_id):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        flash('You do not have permission to add members to this group.', 'danger')
        return redirect(url_for('dashboard'))
    form = MemberForm()
    if form.validate_on_submit():
        member = Member(
            name=form.name.data,
            email=form.email.data,
            mobile_number=form.mobile_number.data,
            group_id=group.id
        )
        db.session.add(member)
        db.session.commit()
        flash(f'Member "{form.name.data}" added successfully!', 'success')
        return redirect(url_for('group_detail', group_id=group.id))
    return render_template('create_member.html', title='New Member', form=form, group=group)

@app.route('/member/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    if member.group.user_id != current_user.id:
        flash('You do not have permission to edit this member.', 'danger')
        return redirect(url_for('dashboard'))
    form = MemberForm(obj=member)
    if form.validate_on_submit():
        member.name = form.name.data
        member.email = form.email.data
        member.mobile_number = form.mobile_number.data
        db.session.commit()
        flash(f'Member "{form.name.data}" updated successfully!', 'success')
        return redirect(url_for('group_detail', group_id=member.group_id))
    return render_template('edit_member.html', title='Edit Member', form=form, member=member)

@app.route('/member/<int:member_id>/delete', methods=['POST'])
@login_required
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    if member.group.user_id != current_user.id:
        flash('You do not have permission to delete this member.', 'danger')
        return redirect(url_for('dashboard'))
    group_id = member.group_id
    db.session.delete(member)
    db.session.commit()
    flash(f'Member "{member.name}" deleted successfully!', 'success')
    return redirect(url_for('group_detail', group_id=group_id))

# Bill routes
@app.route('/group/<int:group_id>/bill/new', methods=['GET', 'POST'])
@login_required
def new_bill(group_id):
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        flash('You do not have permission to add bills to this group.', 'danger')
        return redirect(url_for('dashboard'))
    form = BillForm()
    if form.validate_on_submit():
        bill = Bill(
            title=form.title.data,
            description=form.description.data,
            date=form.date.data,
            group_id=group.id
        )
        db.session.add(bill)
        db.session.commit()
        flash(f'Bill "{form.title.data}" created successfully!', 'success')
        return redirect(url_for('bill_detail', bill_id=bill.id))
    return render_template('create_bill.html', title='New Bill', form=form, group=group)

@app.route('/bill/<int:bill_id>')
@login_required
def bill_detail(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.group.user_id != current_user.id:
        flash('You do not have permission to view this bill.', 'danger')
        return redirect(url_for('dashboard'))
    member_summary = bill.get_member_summary()
    settlement = bill.get_settlement_summary()
    
    # Create a JSON-serializable version of member_summary for JavaScript
    js_member_summary = {}
    for member_id, data in member_summary.items():
        js_member_summary[member_id] = {
            'member': {
                'id': data['member'].id,
                'name': data['member'].name,
                'email': data['member'].email,
                'mobile_number': data['member'].mobile_number
            },
            'paid': data['paid'],
            'owes': data['owes'],
            'net': data['net'],
            'paid_products': [{
                'id': p.id,
                'name': p.name,
                'price': p.price,
                'members_count': len(p.members_involved)
            } for p in data['paid_products']],
            'shared_products': [{
                'id': p.id,
                'name': p.name,
                'price': p.price
            } for p in data['shared_products']]
        }
    
    return render_template('bill_detail.html', title=bill.title, bill=bill, 
                           member_summary=member_summary, settlement=settlement, 
                           js_member_summary=js_member_summary, abs=abs)

@app.route('/bill/<int:bill_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.group.user_id != current_user.id:
        flash('You do not have permission to edit this bill.', 'danger')
        return redirect(url_for('dashboard'))
    form = BillForm(obj=bill)
    if form.validate_on_submit():
        bill.title = form.title.data
        bill.description = form.description.data
        bill.date = form.date.data
        db.session.commit()
        flash(f'Bill "{form.title.data}" updated successfully!', 'success')
        return redirect(url_for('bill_detail', bill_id=bill.id))
    return render_template('edit_bill.html', title='Edit Bill', form=form, bill=bill)

@app.route('/bill/<int:bill_id>/delete', methods=['POST'])
@login_required
def delete_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.group.user_id != current_user.id:
        flash('You do not have permission to delete this bill.', 'danger')
        return redirect(url_for('dashboard'))
    group_id = bill.group_id
    db.session.delete(bill)
    db.session.commit()
    flash(f'Bill "{bill.title}" deleted successfully!', 'success')
    return redirect(url_for('group_detail', group_id=group_id))

# Product routes
@app.route('/bill/<int:bill_id>/product/new', methods=['GET', 'POST'])
@login_required
def new_product(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.group.user_id != current_user.id:
        flash('You do not have permission to add products to this bill.', 'danger')
        return redirect(url_for('dashboard'))
    form = ProductForm()
    # Populate the payer and members_involved select fields
    form.payer.choices = [(m.id, m.name) for m in bill.group.members]
    form.members_involved.choices = [(m.id, m.name) for m in bill.group.members]
    
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            price=form.price.data,
            bill_id=bill.id,
            payer_id=form.payer.data
        )
        db.session.add(product)
        db.session.flush()  # Flush to get the product ID
        
        # Add members involved
        for member_id in form.members_involved.data:
            product_member = ProductMember(
                product_id=product.id,
                member_id=member_id
            )
            db.session.add(product_member)
        
        db.session.commit()
        flash(f'Product "{form.name.data}" added successfully!', 'success')
        return redirect(url_for('bill_detail', bill_id=bill.id))
    return render_template('create_product.html', title='New Product', form=form, bill=bill)

@app.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.bill.group.user_id != current_user.id:
        flash('You do not have permission to edit this product.', 'danger')
        return redirect(url_for('dashboard'))
    form = ProductForm(obj=product)
    # Populate the payer and members_involved select fields
    form.payer.choices = [(m.id, m.name) for m in product.bill.group.members]
    form.members_involved.choices = [(m.id, m.name) for m in product.bill.group.members]
    # Set the default values for members_involved
    form.members_involved.default = [pm.member_id for pm in product.members_involved]
    
    if request.method == 'GET':
        form.payer.data = product.payer_id
        form.members_involved.data = [pm.member_id for pm in product.members_involved]
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.price = form.price.data
        product.payer_id = form.payer.data
        
        # Remove existing product_member associations
        ProductMember.query.filter_by(product_id=product.id).delete()
        
        # Add new members involved
        for member_id in form.members_involved.data:
            product_member = ProductMember(
                product_id=product.id,
                member_id=member_id
            )
            db.session.add(product_member)
        
        db.session.commit()
        flash(f'Product "{form.name.data}" updated successfully!', 'success')
        return redirect(url_for('bill_detail', bill_id=product.bill_id))
    return render_template('edit_product.html', title='Edit Product', form=form, product=product)

@app.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.bill.group.user_id != current_user.id:
        flash('You do not have permission to delete this product.', 'danger')
        return redirect(url_for('dashboard'))
    bill_id = product.bill_id
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product.name}" deleted successfully!', 'success')
    return redirect(url_for('bill_detail', bill_id=bill_id))

# Export routes
@app.route('/bill/<int:bill_id>/export/csv')
@login_required
def export_bill_csv(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.group.user_id != current_user.id:
        flash('You do not have permission to export this bill.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Create a DataFrame for the bill summary
    member_summary = bill.get_member_summary()
    settlement = bill.get_settlement_summary()
    
    # Create member summary DataFrame
    summary_data = []
    for member_id, data in member_summary.items():
        member = data['member']
        products_info = []
        for product_data in data['products']:
            product = product_data['product']
            shared_with = [Member.query.get(m_id).name for m_id in product_data['shared_with']]
            shared_info = f"shared with {', '.join(shared_with)}" if shared_with else "independent"
            products_info.append(f"{product.name} ({shared_info}): ${product_data['share']:.2f}")
        
        summary_data.append({
            'Member': member.name,
            'Products': '\n'.join(products_info),
            'Total Paid': f"${data['paid']:.2f}",
            'Total Owed': f"${data['owes']:.2f}",
            'Net Balance': f"${data['net']:.2f}"
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Create settlement DataFrame
    settlement_data = []
    for transaction in settlement:
        settlement_data.append({
            'From': transaction['from_member'].name,
            'To': transaction['to_member'].name,
            'Amount': f"${transaction['amount']:.2f}"
        })
    
    settlement_df = pd.DataFrame(settlement_data)
    
    # Create a buffer to store the CSV
    buffer = io.StringIO()
    
    # Write the bill information
    buffer.write(f"Bill: {bill.title}\n")
    buffer.write(f"Date: {bill.date}\n")
    buffer.write(f"Group: {bill.group.name}\n\n")
    
    # Write the member summary
    buffer.write("Member Summary:\n")
    summary_df.to_csv(buffer, index=False)
    buffer.write("\n\n")
    
    # Write the settlement summary
    buffer.write("Settlement Summary:\n")
    settlement_df.to_csv(buffer, index=False)
    
    # Set the buffer position to the beginning
    buffer.seek(0)
    
    # Create a response with the CSV file
    return send_file(
        io.BytesIO(buffer.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"{bill.title.replace(' ', '_')}_summary.csv"
    )

@app.route('/bill/<int:bill_id>/export/excel')
@login_required
def export_bill_excel(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.group.user_id != current_user.id:
        flash('You do not have permission to export this bill.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Create a DataFrame for the bill summary
    member_summary = bill.get_member_summary()
    settlement = bill.get_settlement_summary()
    
    # Create member summary DataFrame
    summary_data = []
    for member_id, data in member_summary.items():
        member = data['member']
        products_info = []
        for product_data in data['products']:
            product = product_data['product']
            shared_with = [Member.query.get(m_id).name for m_id in product_data['shared_with']]
            shared_info = f"shared with {', '.join(shared_with)}" if shared_with else "independent"
            products_info.append(f"{product.name} ({shared_info}): ${product_data['share']:.2f}")
        
        summary_data.append({
            'Member': member.name,
            'Products': '\n'.join(products_info),
            'Total Paid': data['paid'],
            'Total Owed': data['owes'],
            'Net Balance': data['net']
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Create settlement DataFrame
    settlement_data = []
    for transaction in settlement:
        settlement_data.append({
            'From': transaction['from_member'].name,
            'To': transaction['to_member'].name,
            'Amount': transaction['amount']
        })
    
    settlement_df = pd.DataFrame(settlement_data)
    
    # Create a buffer to store the Excel file
    buffer = io.BytesIO()
    
    # Create an Excel writer
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Write the bill information to a sheet
        bill_info = pd.DataFrame([
            {'Info': 'Bill', 'Value': bill.title},
            {'Info': 'Date', 'Value': bill.date},
            {'Info': 'Group', 'Value': bill.group.name},
            {'Info': 'Total Amount', 'Value': bill.get_total_amount()}
        ])
        bill_info.to_excel(writer, sheet_name='Bill Info', index=False)
        
        # Write the member summary to a sheet
        summary_df.to_excel(writer, sheet_name='Member Summary', index=False)
        
        # Write the settlement summary to a sheet
        settlement_df.to_excel(writer, sheet_name='Settlement', index=False)
        
        # Write the products to a sheet
        products_data = []
        for product in bill.products:
            members_involved = [pm.member.name for pm in product.members_involved]
            products_data.append({
                'Product': product.name,
                'Price': product.price,
                'Paid By': product.payer.name,
                'Members Involved': ', '.join(members_involved)
            })
        
        products_df = pd.DataFrame(products_data)
        products_df.to_excel(writer, sheet_name='Products', index=False)
    
    # Set the buffer position to the beginning
    buffer.seek(0)
    
    # Create a response with the Excel file
    return send_file(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"{bill.title.replace(' ', '_')}_summary.xlsx"
    )