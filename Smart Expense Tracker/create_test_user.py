import requests
import re

def create_test_user():
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Step 1: Get the registration page to obtain CSRF token
    register_page = session.get('http://127.0.0.1:5000/register')
    print(f"Register page status: {register_page.status_code}")
    
    # Extract CSRF token
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', register_page.text)
    if not csrf_match:
        print("Could not find CSRF token")
        # Let's save the page to debug
        with open('debug_register.html', 'w', encoding='utf-8') as f:
            f.write(register_page.text)
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"Found CSRF token: {csrf_token}")
    
    # Step 2: Register a new user
    register_data = {
        'csrf_token': csrf_token,
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'test123',
        'password2': 'test123',
        'submit': 'Register'
    }
    
    register_response = session.post('http://127.0.0.1:5000/register', data=register_data)
    print(f"Register response status: {register_response.status_code}")
    print(f"Register response URL: {register_response.url}")
    
    # Check if registration was successful (should redirect to login or dashboard)
    if 'register' in register_response.url.lower() and register_response.status_code == 200:
        print("Registration failed")
        # Let's try to extract the error message
        error_match = re.search(r'class="[^"]*alert[^"]*"[^>]*>([^<]+)', register_response.text)
        if error_match:
            print(f"Error: {error_match.group(1).strip()}")
        return False
    
    print("Registration appears successful!")
    
    # Step 3: Login with the new user
    login_page = session.get('http://127.0.0.1:5000/login')
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', login_page.text)
    csrf_token = csrf_match.group(1)
    
    login_data = {
        'csrf_token': csrf_token,
        'username': 'testuser',
        'password': 'test123',
        'submit': 'Login'
    }
    
    login_response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print(f"Login response status: {login_response.status_code}")
    print(f"Login response URL: {login_response.url}")
    
    if 'login' in login_response.url.lower() and login_response.status_code == 200:
        print("Login failed")
        return False
    
    print("Login successful!")
    
    # Step 4: Access currency settings page
    currency_page = session.get('http://127.0.0.1:5000/settings/currency')
    print(f"Currency page status: {currency_page.status_code}")
    print(f"Currency page URL: {currency_page.url}")
    
    if 'login' in currency_page.url.lower():
        print("Still being redirected to login - authentication failed")
        return False
    
    print("Successfully accessed currency settings!")
    
    # Step 5: Analyze the page content
    print("\nAnalyzing page content...")
    
    # Look for select elements
    select_matches = re.findall(r'<select[^>]*>(.*?)</select>', currency_page.text, re.DOTALL)
    print(f"Found {len(select_matches)} select elements")
    
    # Look for option elements
    option_matches = re.findall(r'<option[^>]*>([^<]+)</option>', currency_page.text)
    print(f"Found {len(option_matches)} option elements")
    
    # Look for USD specifically
    usd_matches = re.findall(r'USD', currency_page.text)
    print(f"Found {len(usd_matches)} USD references")
    
    # Check for empty dropdowns
    empty_selects = 0
    for i, select_content in enumerate(select_matches):
        options_in_select = re.findall(r'<option[^>]*>([^<]+)</option>', select_content)
        print(f"Select {i+1} has {len(options_in_select)} options")
        if len(options_in_select) <= 1:  # Only "Choose..." or similar
            empty_selects += 1
            print(f"  WARNING: Select {i+1} appears to be mostly empty")
        else:
            print(f"  Options: {[opt.strip() for opt in options_in_select]}")
    
    # Save the full content for inspection
    with open('currency_authenticated.html', 'w', encoding='utf-8') as f:
        f.write(currency_page.text)
        print("Saved full currency page to currency_authenticated.html")
    
    return empty_selects == 0  # Return True if no empty dropdowns found

if __name__ == "__main__":
    success = create_test_user()
    if success:
        print("\n✅ Currency dropdowns appear to be working correctly!")
    else:
        print("\n❌ Found issues with currency dropdowns")