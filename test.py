from playwright.sync_api import sync_playwright
import os
import time

def use_saved_auth_for_youtube():
    """Use saved authentication state to access YouTube"""
    
    # Check if auth state file exists
    if not os.path.exists("auth-state.json"):
        print("Error: auth-state.json not found!")
        print("Please run the save_google_profile.py script first to save your authentication.")
        return
    
    print("Loading saved authentication state...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-dev-shm-usage"
            ]
        )
        
        # Load the saved authentication state
        context = browser.new_context(
            storage_state="auth-state.json",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        # Navigate to YouTube
        print("Navigating to YouTube...")
        page.goto("https://www.youtube.com")
        
        # Wait a moment for the page to load
        time.sleep(3)
        
        # Check if logged in by looking for the avatar button
        try:
            page.wait_for_selector("#avatar-btn", timeout=10000)
            print("✅ Successfully logged into YouTube!")
            
            # Get user info if available
            try:
                # Try to get the user's name or email
                avatar_btn = page.locator("#avatar-btn")
                avatar_btn.click()
                time.sleep(1)
                
                # Look for account info
                account_name = page.locator("yt-formatted-string#account-name")
                if account_name.count() > 0:
                    name = account_name.inner_text()
                    print(f"Logged in as: {name}")
                
                # Close the menu by clicking elsewhere
                page.click("body")
                
            except Exception as e:
                print("Could not retrieve account info, but login appears successful")
                
        except Exception as e:
            print("❌ Login verification failed. You might not be logged in.")
            print("The authentication state might be expired or invalid.")
        
        print("\nYouTube is now open with your saved authentication.")
        print("You can now add your automation code here.")
        print("Press Enter to close the browser...")
        input()
        
        browser.close()

def demo_youtube_automation():
    """Example of what you can do with authenticated YouTube access"""
    
    if not os.path.exists("auth-state.json"):
        print("Error: auth-state.json not found!")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-first-run"]
        )
        
        context = browser.new_context(storage_state="auth-state.json")
        page = context.new_page()
        page.goto("https://www.youtube.com")
        
        try:
            # Wait for login
            page.wait_for_selector("#avatar-btn", timeout=10000)
            print("✅ Logged into YouTube successfully!")
            
            # Example automation: Search for a video
            search_box = page.locator("input[name='search_query']")
            search_box.fill("Python tutorial")
            search_box.press("Enter")
            
            # Wait for search results
            page.wait_for_selector("ytd-video-renderer", timeout=10000)
            print("✅ Search completed!")
            
            # Example: Click on first video
            first_video = page.locator("ytd-video-renderer").first
            video_title = first_video.locator("#video-title").inner_text()
            print(f"First video: {video_title}")
            
            # Uncomment to actually click the video
            # first_video.click()
            
            print("Demo completed. Press Enter to close...")
            input()
            
        except Exception as e:
            print(f"Error during automation: {e}")
        
        browser.close()

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Just open YouTube with saved authentication")
    print("2. Demo YouTube automation (search and show results)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        demo_youtube_automation()
    else:
        use_saved_auth_for_youtube()