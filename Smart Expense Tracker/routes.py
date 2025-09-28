from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from smart_expense_splitter import app, db
from models import User, Group, Member, Bill, Product, ProductMember, BillTemplate, TemplateProduct
from forms import LoginForm, RegistrationForm, GroupForm, MemberForm, BillForm, ProductForm, BillTemplateForm, TemplateProductForm
from datetime import datetime
# import pandas as pd
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

# Settings route
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', title='Settings')

@app.route('/settings/currency', methods=['GET', 'POST'])
@login_required
def currency_settings():
    from models import Currency, UserCurrency, populate_initial_currencies
    from forms import CurrencySettingsForm, AddCurrencyForm
    
    # Ensure currencies are populated
    populate_initial_currencies()
    
    # Get user's current currencies
    user_currencies = current_user.get_active_currencies()
    default_currency = current_user.get_default_currency()
    
    # If user has no currencies, automatically add USD as default
    if not user_currencies:
        usd_currency = Currency.query.filter_by(code='USD').first()
        if usd_currency:
            current_user.add_currency(usd_currency.id, is_default=True)
            user_currencies = current_user.get_active_currencies()
            default_currency = usd_currency
            flash('Welcome! USD has been set as your default currency. You can change this below.', 'info')
    
    # Currency settings form
    form = CurrencySettingsForm(user_id=current_user.id)
    add_form = AddCurrencyForm(user_id=current_user.id)
    
    if form.submit.data and form.validate_on_submit():
        # Update default currency
        if form.default_currency.data:
            current_user.set_default_currency(form.default_currency.data)
            flash('Default currency updated successfully!', 'success')
        return redirect(url_for('currency_settings'))
    
    if add_form.submit.data and add_form.validate_on_submit():
        # Add new currency
        if current_user.add_currency(add_form.currency_id.data, add_form.make_default.data):
            flash('Currency added successfully!', 'success')
            if add_form.make_default.data:
                flash('Default currency updated!', 'success')
        else:
            flash('Failed to add currency. Please try again.', 'danger')
        return redirect(url_for('currency_settings'))
    
    # Set form defaults
    if default_currency:
        form.default_currency.data = default_currency.id
    
    # Get all available currencies for the dropdown
    available_currencies = Currency.query.filter_by(is_active=True).all()
    
    return render_template('currency_settings.html', 
                           title='Currency Settings',
                           form=form,
                           add_form=add_form,
                           user_currencies=user_currencies,
                           default_currency=default_currency,
                           available_currencies=available_currencies)

@app.route('/settings/currency/remove/<int:currency_id>', methods=['POST'])
@login_required
def remove_currency(currency_id):
    if current_user.remove_currency(currency_id):
        flash('Currency removed successfully!', 'success')
    else:
        flash('Cannot remove currency. You must have at least one active currency.', 'danger')
    return redirect(url_for('currency_settings'))

@app.route('/settings/currency/set-default/<int:currency_id>', methods=['POST'])
@login_required
def set_default_currency_route(currency_id):
    if current_user.set_default_currency(currency_id):
        flash('Default currency updated successfully!', 'success')
    else:
        flash('Failed to update default currency.', 'danger')
    return redirect(url_for('currency_settings'))

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
            category=form.category.data,
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
                'price': p.price,
                'members_count': len(p.members_involved),
                'payer_name': p.payer.name if p.payer else 'Unknown'
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
        bill.category = form.category.data
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

# Export routes - simple CSV export without pandas
@app.route('/bill/<int:bill_id>/export/csv')
@login_required
def export_bill_csv(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.group.user_id != current_user.id:
        flash('You do not have permission to export this bill.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get bill summary and settlement data
    member_summary = bill.get_member_summary()
    settlement = bill.get_settlement_summary()
    
    # Create CSV content manually
    csv_content = []
    
    # Add bill information
    csv_content.append(f"Bill: {bill.title}")
    csv_content.append(f"Date: {bill.date}")
    csv_content.append(f"Group: {bill.group.name}")
    csv_content.append("")
    
    # Add member summary
    csv_content.append("Member Summary:")
    csv_content.append("Member,Products,Total Paid,Total Owed,Net Balance")
    
    for member_id, data in member_summary.items():
        member = data['member']
        products_info = []
        for product_data in data['products']:
            product = product_data['product']
            shared_with = [Member.query.get(m_id).name for m_id in product_data['shared_with']]
            shared_info = f"shared with {', '.join(shared_with)}" if shared_with else "independent"
            products_info.append(f"{product.name} ({shared_info}): ${product_data['share']:.2f}")
        
        products_str = '; '.join(products_info)
        csv_content.append(f'"{member.name}","{products_str}","${data["paid"]:.2f}","${data["owes"]:.2f}","${data["net"]:.2f}"')
    
    csv_content.append("")
    
    # Add settlement summary
    csv_content.append("Settlement Summary:")
    csv_content.append("From,To,Amount")
    
    for transaction in settlement:
        csv_content.append(f'"{transaction["from_member"].name}","{transaction["to_member"].name}","${transaction["amount"]:.2f}"')
    
    # Join all lines with newlines
    csv_string = '\n'.join(csv_content)
    
    # Create a response with the CSV file
    return send_file(
        io.BytesIO(csv_string.encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"{bill.title.replace(' ', '_')}_summary.csv"
    )

# @app.route('/bill/<int:bill_id>/export/excel')
# @login_required
# def export_bill_excel(bill_id):
#     bill = Bill.query.get_or_404(bill_id)
#     if bill.group.user_id != current_user.id:
#         flash('You do not have permission to export this bill.', 'danger')
#         return redirect(url_for('dashboard'))
#     
#     # Create a DataFrame for the bill summary
#     member_summary = bill.get_member_summary()
#     settlement = bill.get_settlement_summary()
#     
#     # Create member summary DataFrame
#     summary_data = []
#     for member_id, data in member_summary.items():
#         member = data['member']
#         products_info = []
#         for product_data in data['products']:
#             product = product_data['product']
#             shared_with = [Member.query.get(m_id).name for m_id in product_data['shared_with']]
#             shared_info = f"shared with {', '.join(shared_with)}" if shared_with else "independent"
#             products_info.append(f"{product.name} ({shared_info}): ${product_data['share']:.2f}")
#         
#         summary_data.append({
#             'Member': member.name,
#             'Products': '\n'.join(products_info),
#             'Total Paid': data['paid'],
#             'Total Owed': data['owes'],
#             'Net Balance': data['net']
#         })
#     
#     summary_df = pd.DataFrame(summary_data)
#     
#     # Create settlement DataFrame
#     settlement_data = []
#     for transaction in settlement:
#         settlement_data.append({
#             'From': transaction['from_member'].name,
#             'To': transaction['to_member'].name,
#             'Amount': transaction['amount']
#         })
#     
#     settlement_df = pd.DataFrame(settlement_data)
#     
#     # Create a buffer to store the Excel file
#     buffer = io.BytesIO()
#     
#     # Create an Excel writer
#     with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
#         # Write the bill information to a sheet
#         bill_info = pd.DataFrame([
#             {'Info': 'Bill', 'Value': bill.title},
#             {'Info': 'Date', 'Value': bill.date},
#             {'Info': 'Group', 'Value': bill.group.name},
#             {'Info': 'Total Amount', 'Value': bill.get_total_amount()}
#         ])
#         bill_info.to_excel(writer, sheet_name='Bill Info', index=False)
#         
#         # Write the member summary to a sheet
#         summary_df.to_excel(writer, sheet_name='Member Summary', index=False)
#         
#         # Write the settlement summary to a sheet
#         settlement_df.to_excel(writer, sheet_name='Settlement', index=False)
#         
#         # Write the products to a sheet
#         products_data = []
#         for product in bill.products:
#             members_involved = [pm.member.name for pm in product.members_involved]
#             products_data.append({
#                 'Product': product.name,
#                 'Price': product.price,
#                 'Paid By': product.payer.name,
#                 'Members Involved': ', '.join(members_involved)
#             })
#         
#         products_df = pd.DataFrame(products_data)
#         products_df.to_excel(writer, sheet_name='Products', index=False)
#     
#     # Set the buffer position to the beginning
#     buffer.seek(0)
#     
#     # Create a response with the Excel file)
#     return send_file(
#         buffer,
#         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#         as_attachment=True,
#         download_name=f"{bill.title.replace(' ', '_')}_summary.xlsx"
#     )

# Static pages
@app.route('/about')
def about():
    return render_template('about.html', title='About Us')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', title='Privacy Policy')

@app.route('/terms')
def terms():
    return render_template('terms.html', title='Terms of Service')

@app.route('/contact')
def contact():
    return render_template('contact.html', title='Contact Us')

# Bill Template routes
@app.route('/templates')
@login_required
def bill_templates():
    templates = BillTemplate.query.filter_by(user_id=current_user.id).order_by(BillTemplate.created_at.desc()).all()
    return render_template('bill_templates.html', title='Bill Templates', templates=templates)

@app.route('/template/new', methods=['GET', 'POST'])
@login_required
def new_bill_template():
    form = BillTemplateForm()
    if form.validate_on_submit():
        template = BillTemplate(
            name=form.name.data,
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            user_id=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        flash(f'Template "{form.name.data}" created successfully!', 'success')
        return redirect(url_for('bill_template_detail', template_id=template.id))
    return render_template('create_bill_template.html', title='New Bill Template', form=form)

@app.route('/template/<int:template_id>')
@login_required
def bill_template_detail(template_id):
    template = BillTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('You do not have permission to view this template.', 'danger')
        return redirect(url_for('bill_templates'))
    return render_template('bill_template_detail.html', title=template.name, template=template)

@app.route('/template/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bill_template(template_id):
    template = BillTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('You do not have permission to edit this template.', 'danger')
        return redirect(url_for('bill_templates'))
    form = BillTemplateForm(obj=template)
    if form.validate_on_submit():
        template.name = form.name.data
        template.title = form.title.data
        template.description = form.description.data
        template.category = form.category.data
        db.session.commit()
        flash(f'Template "{form.name.data}" updated successfully!', 'success')
        return redirect(url_for('bill_template_detail', template_id=template.id))
    return render_template('edit_bill_template.html', title='Edit Template', form=form, template=template)

@app.route('/template/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_bill_template(template_id):
    template = BillTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('You do not have permission to delete this template.', 'danger')
        return redirect(url_for('bill_templates'))
    db.session.delete(template)
    db.session.commit()
    flash(f'Template "{template.name}" deleted successfully!', 'success')
    return redirect(url_for('bill_templates'))

@app.route('/template/<int:template_id>/product/new', methods=['GET', 'POST'])
@login_required
def new_template_product(template_id):
    template = BillTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('You do not have permission to add products to this template.', 'danger')
        return redirect(url_for('bill_templates'))
    form = TemplateProductForm()
    if form.validate_on_submit():
        template_product = TemplateProduct(
            name=form.name.data,
            price=form.price.data,
            bill_template_id=template.id
        )
        db.session.add(template_product)
        db.session.commit()
        flash(f'Product "{form.name.data}" added to template!', 'success')
        return redirect(url_for('bill_template_detail', template_id=template.id))
    return render_template('create_template_product.html', title='Add Template Product', form=form, template=template)

@app.route('/template/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_template_product(product_id):
    template_product = TemplateProduct.query.get_or_404(product_id)
    template = template_product.bill_template
    if template.user_id != current_user.id:
        flash('You do not have permission to delete this template product.', 'danger')
        return redirect(url_for('bill_templates'))
    db.session.delete(template_product)
    db.session.commit()
    flash(f'Product "{template_product.name}" removed from template!', 'success')
    return redirect(url_for('bill_template_detail', template_id=template.id))

@app.route('/template/<int:template_id>/use/<int:group_id>')
@login_required
def use_bill_template(template_id, group_id):
    template = BillTemplate.query.get_or_404(template_id)
    group = Group.query.get_or_404(group_id)
    
    if template.user_id != current_user.id:
        flash('You do not have permission to use this template.', 'danger')
        return redirect(url_for('bill_templates'))
    
    if group.user_id != current_user.id:
        flash('You do not have permission to add bills to this group.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Create a new bill from template
    bill = Bill(
        title=template.title,
        description=template.description,
        category=template.category,
        group_id=group.id
    )
    db.session.add(bill)
    db.session.commit()
    
    # Add template products to the new bill
    for template_product in template.template_products:
        # Create a placeholder product (user will need to assign payer and members)
        product = Product(
            name=template_product.name,
            price=template_product.price,
            bill_id=bill.id,
            payer_id=group.members[0].id if group.members else None
        )
        db.session.add(product)
        db.session.commit()
    
    flash(f'Bill created from template "{template.name}"!', 'success')
    return redirect(url_for('edit_bill', bill_id=bill.id))

# Bill Search and Filter routes
@app.route('/bills')
@login_required
def bills():
    # Get filter parameters
    search_query = request.args.get('search', '', type=str)
    category_filter = request.args.get('category', '', type=str)
    date_from = request.args.get('date_from', '', type=str)
    date_to = request.args.get('date_to', '', type=str)
    group_filter = request.args.get('group', '', type=str)
    sort_by = request.args.get('sort', 'date_desc', type=str)
    
    # Base query - get all bills for user's groups
    query = Bill.query.join(Group).filter(Group.user_id == current_user.id)
    
    # Apply search filter
    if search_query:
        query = query.filter(
            db.or_(
                Bill.title.ilike(f'%{search_query}%'),
                Bill.description.ilike(f'%{search_query}%')
            )
        )
    
    # Apply category filter
    if category_filter:
        query = query.filter(Bill.category == category_filter)
    
    # Apply date filters
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Bill.date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Bill.date <= to_date)
        except ValueError:
            pass
    
    # Apply group filter
    if group_filter:
        query = query.filter(Bill.group_id == int(group_filter))
    
    # Apply sorting
    if sort_by == 'date_desc':
        query = query.order_by(Bill.date.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Bill.date.asc())
    elif sort_by == 'title_asc':
        query = query.order_by(Bill.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Bill.title.desc())
    elif sort_by == 'amount_desc':
        query = query.outerjoin(Product).group_by(Bill.id).order_by(db.func.sum(Product.price).desc().nullslast())
    elif sort_by == 'amount_asc':
        query = query.outerjoin(Product).group_by(Bill.id).order_by(db.func.sum(Product.price).asc().nullslast())
    
    # Execute query with pagination
    page = request.args.get('page', 1, type=int)
    bills = query.paginate(page=page, per_page=10, error_out=False)
    
    # Get user's groups for filter dropdown
    user_groups = Group.query.filter_by(user_id=current_user.id).all()
    
    # Get available categories
    categories = ['Food & Dining', 'Transportation', 'Shopping', 'Entertainment', 'Bills & Utilities', 'Healthcare', 'Travel', 'Education', 'Other']
    
    return render_template('bills.html', 
                         title='Bills',
                         bills=bills,
                         user_groups=user_groups,
                         categories=categories,
                         search_query=search_query,
                         category_filter=category_filter,
                         date_from=date_from,
                         date_to=date_to,
                         group_filter=group_filter,
                         sort_by=sort_by)

# Analytics routes
@app.route('/analytics')
@login_required
def analytics():
    """Main analytics dashboard"""
    # Get user's groups
    groups = Group.query.filter_by(user_id=current_user.id).all()
    
    # Overall statistics
    total_expenses = current_user.get_total_expenses()
    total_groups = len(groups)
    total_bills = sum(len(group.bills) for group in groups)
    average_bill_amount = total_expenses / total_bills if total_bills > 0 else 0
    
    # Category breakdown
    category_totals = current_user.get_expenses_by_category()
    
    # Monthly expenses for current year
    current_year = datetime.now().year
    monthly_expenses = current_user.get_monthly_expenses(current_year)
    
    # Top categories
    all_categories = []
    for group in groups:
        all_categories.extend(group.get_top_categories())
    
    # Combine and sort categories
    category_summary = {}
    for category, amount in all_categories:
        category_summary[category] = category_summary.get(category, 0) + amount
    
    top_categories = sorted(category_summary.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Format top categories for template
    formatted_top_categories = []
    for category, total in top_categories:
        count = sum(1 for group in groups for cat, amt in group.get_top_categories() if cat == category)
        formatted_top_categories.append({
            'category': category,
            'total': total,
            'count': count
        })
    
    # Recent activity (last 5 bills)
    recent_bills = Bill.query.join(Group).filter(Group.user_id == current_user.id).order_by(Bill.created_at.desc()).limit(5).all()
    
    # Format monthly data for charts
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_data = {
        'labels': months,
        'data': [monthly_expenses.get(f"{current_year}-{month:02d}", 0) for month in range(1, 13)]
    }
    
    # Format category data for charts
    category_data = {
        'labels': list(category_totals.keys()),
        'data': list(category_totals.values())
    }
    
    # Create group analytics list
    group_analytics_list = []
    for group in groups:
        group_total = group.get_total_expenses()
        group_bills = len(group.bills)
        group_avg = group.get_average_bill_amount()
        group_top_categories = group.get_top_categories()
        
        group_analytics_list.append({
            'group': group,
            'total_expenses': group_total,
            'total_bills': group_bills,
            'average_bill_amount': group_avg,
            'top_categories': group_top_categories
        })
    
    return render_template('analytics.html',
                           title='Analytics',
                           total_expenses=total_expenses,
                           total_groups=total_groups,
                           total_bills=total_bills,
                           average_bill_amount=average_bill_amount,
                           category_totals=category_totals,
                           monthly_expenses=monthly_expenses,
                           top_categories=formatted_top_categories,
                           recent_bills=recent_bills,
                           current_year=current_year,
                           groups=groups,
                           monthly_data=monthly_data,
                           category_data=category_data,
                           group_analytics_list=group_analytics_list)

@app.route('/analytics/group/<int:group_id>')
@login_required
def group_analytics(group_id):
    """Group-specific analytics"""
    group = Group.query.get_or_404(group_id)
    if group.user_id != current_user.id:
        flash('You do not have permission to view analytics for this group.', 'danger')
        return redirect(url_for('analytics'))
    
    # Group statistics
    total_expenses = group.get_total_expenses()
    total_bills = len(group.bills)
    average_bill = group.get_average_bill_amount()
    
    # Category breakdown for group
    category_totals = group.get_expenses_by_category()
    
    # Monthly expenses for current year
    current_year = datetime.now().year
    monthly_expenses = group.get_monthly_expenses(current_year)
    
    # Top categories for group
    top_categories = group.get_top_categories()
    
    # Member expenses
    member_expenses = []
    for member in group.members:
        member_total = group.get_member_expenses(member.id)
        member_expenses.append({
            'member': member,
            'total_expense': member_total
        })
    
    # Sort by expense amount
    member_expenses.sort(key=lambda x: x['total_expense'], reverse=True)
    
    # Recent bills for this group
    recent_bills = Bill.query.filter_by(group_id=group.id).order_by(Bill.created_at.desc()).limit(5).all()
    
    return render_template('group_analytics.html',
                           title=f'Analytics - {group.name}',
                           group=group,
                           total_expenses=total_expenses,
                           total_bills=total_bills,
                           average_bill=average_bill,
                           category_totals=category_totals,
                           monthly_expenses=monthly_expenses,
                           top_categories=top_categories,
                           member_expenses=member_expenses,
                           recent_bills=recent_bills,
                           current_year=current_year)

@app.route('/analytics/export/csv')
@login_required
def export_analytics_csv():
    """Export analytics data as CSV"""
    import csv
    
    # Get user's groups
    groups = Group.query.filter_by(user_id=current_user.id).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Group Name', 'Bill Title', 'Category', 'Date', 'Total Amount', 'Description'])
    
    # Write data
    for group in groups:
        for bill in group.bills:
            writer.writerow([
                group.name,
                bill.title,
                bill.category,
                bill.date.strftime('%Y-%m-%d'),
                f"{bill.get_total_amount():.2f}",
                bill.description or ''
            ])
    
    # Prepare response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'expense_analytics_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/api/analytics/monthly-data/<int:year>')
@login_required
def api_monthly_data(year):
    """API endpoint for monthly expense data"""
    monthly_data = current_user.get_monthly_expenses(year)
    
    # Format data for charts
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    data = []
    
    for month in range(1, 13):
        month_key = f"{year}-{month:02d}"
        amount = monthly_data.get(month_key, 0)
        data.append({
            'month': months[month-1],
            'amount': amount
        })
    
    return jsonify({
        'year': year,
        'data': data
    })

@app.route('/api/analytics/category-data')
@login_required
def api_category_data():
    """API endpoint for category expense data"""
    category_data = current_user.get_expenses_by_category()
    
    # Format data for charts
    data = []
    for category, amount in category_data.items():
        data.append({
            'category': category,
            'amount': amount
        })
    
    return jsonify({
        'data': data
    })