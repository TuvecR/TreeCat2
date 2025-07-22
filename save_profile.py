from playwright.sync_api import sync_playwright
import json
import time

def save_auth_state(account_number):
    """Save authentication state for one account - exact copy of your working code"""
    # Generate filename
    if account_number == 1:
        filename = "auth-state.json"
    else:
        filename = f"auth-state{account_number}.json"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",  # Use real Chrome instead of Chromium
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--no-first-run",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        page.goto("https://accounts.google.com")
        
        # Wait for manual login
        print(f"Please log in manually for account {account_number}, then press Enter")
        input()
        
        # Save authentication state
        context.storage_state(path=filename)
        print(f"Authentication state saved to '{filename}'")
        browser.close()
    
    return filename

def save_multiple_auth_states():
    """Save multiple authentication states - replicate your logic for up to 10 accounts"""
    
    saved_states = []
    
    # Ask how many accounts they want to create
    print("How many accounts do you want to create? (1-10)")
    try:
        max_accounts = int(input().strip())
        if max_accounts < 1 or max_accounts > 10:
            print("Please enter a number between 1 and 10")
            return
    except ValueError:
        print("Please enter a valid number")
        return
    
    # Loop for the specified number of accounts
    for i in range(1, max_accounts + 1):
        print(f"\n=== Setting up Account {i} out of {max_accounts} ===")
        
        # Use your exact save_auth_state logic
        filename = save_auth_state(i)
        saved_states.append(filename)
        
        # If not the last account, wait 5 seconds before next browser
        if i < max_accounts:
            print(f"\nAccount {i} completed! Starting next browser in 5 seconds...")
            time.sleep(5)
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"Total auth states created: {len(saved_states)}")
    for state in saved_states:
        print(f"✓ {state}")

if __name__ == "__main__":
    save_multiple_auth_states()