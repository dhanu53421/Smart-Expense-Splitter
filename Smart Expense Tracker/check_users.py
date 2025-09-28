from smart_expense_splitter import app, db
from models import User

with app.app_context():
    users = User.query.all()
    print(f'Found {len(users)} users')
    for user in users:
        print(f'Username: {user.username}, Email: {user.email}')