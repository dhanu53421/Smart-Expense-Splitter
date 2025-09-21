# Smart Expense Splitter

A web application for managing group expenses, bills, and splitting costs among members.

## Features

- User authentication (register, login, logout)
- Create and manage expense groups
- Add members to groups with contact information
- Create bills within groups
- Add products to bills with price and sharing details
- Automatic expense calculation and settlement suggestions
- Export bill data to CSV and Excel formats

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation Steps

1. Clone the repository or download the source code

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python smart_expense_splitter.py
   ```

5. Access the application in your web browser at:
   ```
   http://127.0.0.1:5000
   ```

## Database

The application uses SQLite as the database, which is stored in the file `expense_splitter.db`. The database schema is automatically created when you run the application for the first time.

## Usage Guide

### 1. Registration and Login

- Register a new account with a username, email, and password
- Login with your credentials

### 2. Creating Groups

- From the dashboard, click "Create Group"
- Enter a group name and optional description
- Click "Create Group"

### 3. Adding Members

- Navigate to a group's detail page
- Click "Add Member"
- Enter the member's name, email, and mobile number
- Click "Add Member"

### 4. Creating Bills

- From a group's detail page, click "Add Bill"
- Enter the bill title, description, and date
- Click "Create Bill"

### 5. Adding Products

- From a bill's detail page, click "Add Product"
- Enter the product name and price
- Select who paid for the product
- Select which members shared the expense
- Click "Add Product"

### 6. Viewing Settlements

- The bill detail page shows a summary of expenses and suggested settlements
- Each member's balance is calculated automatically

### 7. Exporting Data

- From a bill's detail page, use the dropdown menu to export to CSV or Excel

## Troubleshooting

### Database Reset

If you need to reset the database:

1. Stop the application
2. Delete the `expense_splitter.db` file
3. Restart the application (a new database will be created)

### Common Issues

- **Login Issues**: Ensure you're using the correct username and password
- **Product Not Appearing**: Make sure you've selected at least one member to share the expense
- **Calculation Errors**: Verify that all products have a valid price and at least one member selected

## License

This project is licensed under the MIT License - see the LICENSE file for details.