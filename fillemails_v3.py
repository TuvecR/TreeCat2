import os
from time import sleep
import pandas as pd
from twocaptcha import TwoCaptcha
from playwright.sync_api import sync_playwright
import re

# Setează calea către fișierele de autentificare relativ la script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_auth_state_paths():
    return [
        os.path.join(SCRIPT_DIR, "auth-state.json"),
        os.path.join(SCRIPT_DIR, "auth-state2.json"),
        os.path.join(SCRIPT_DIR, "auth-state3.json"),
        os.path.join(SCRIPT_DIR, "auth-state4.json"),
        os.path.join(SCRIPT_DIR, "auth-state5.json")
    ]

def get_available_auth_states():
    """Returns only the auth state files that actually exist"""
    auth_states = get_auth_state_paths()
    available_states = []
    for auth_state in auth_states:
        if os.path.exists(auth_state):
            available_states.append(auth_state)
    return available_states

def extract_email_from_page(page):
    """Extract email address from the page using multiple methods"""
    try:
        print("⏳ Waiting for email to appear after captcha resolution...")
        sleep(10)  # Wait longer for email to appear
        
        # Method 1: Check for mailto links
        try:
            mailto_links = page.query_selector_all("a[href^='mailto:']")
            for link in mailto_links:
                href = link.get_attribute("href")
                if href:
                    email = href.replace("mailto:", "").strip()
                    if "@" in email and "." in email and len(email) > 5:
                        print(f"✅ Email found in mailto: {email}")
                        return email
        except Exception as e:
            print(f"Error checking mailto links: {e}")
        
        # Method 2: Extract from page text with enhanced filtering
        try:
            page_text = page.evaluate("() => document.body.innerText")
            email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            matches = re.findall(email_pattern, page_text, re.IGNORECASE)
            
            for match in matches:
                if (not match.startswith('@') and 
                    'youtube' not in match.lower() and 
                    'google' not in match.lower() and
                    'gmail' not in match.lower() and
                    'noreply' not in match.lower() and
                    'support' not in match.lower() and
                    'no-reply' not in match.lower() and
                    'example' not in match.lower() and
                    len(match) > 5):
                    print(f"✅ Email found in text: {match}")
                    return match
                    
        except Exception as e:
            print(f"Error extracting from text: {e}")
        
        # Method 3: Check HTML content
        try:
            html_content = page.content()
            email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            matches = re.findall(email_pattern, html_content, re.IGNORECASE)
            
            for match in matches:
                if (not match.startswith('@') and 
                    'youtube' not in match.lower() and 
                    'google' not in match.lower() and
                    'gmail' not in match.lower() and
                    len(match) > 5):
                    print(f"✅ Email found in HTML: {match}")
                    return match
                    
        except Exception as e:
            print(f"Error extracting from HTML: {e}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error extracting email: {e}")
        return None

def save_email_to_excel(url, email, excel_file_path):
    """Save extracted email to Excel file"""
    try:
        df = pd.read_excel(excel_file_path)
        
        if 'Email' not in df.columns:
            df['Email'] = ''
        
        url_base = url.replace('/about', '').rstrip('/')
        
        for index, row in df.iterrows():
            if pd.notna(row['URL']) and row['URL'].rstrip('/') == url_base:
                current_email = row.get('Email', '')
                if pd.isna(current_email) or current_email == '' or str(current_email).strip() == '':
                    df.at[index, 'Email'] = email
                    print(f"✅ Email saved to Excel for {url_base}: {email}")
                break
        
        df.to_excel(excel_file_path, index=False)
        
    except Exception as e:
        print(f"❌ Error saving email to Excel: {e}")

def should_process_url(url, excel_file_path):
    """Check if URL needs processing"""
    try:
        df = pd.read_excel(excel_file_path)
        
        if 'Email' not in df.columns:
            return True
        
        url_base = url.replace('/about', '').rstrip('/')
        
        for index, row in df.iterrows():
            if pd.notna(row['URL']) and row['URL'].rstrip('/') == url_base:
                current_email = row.get('Email', '')
                if pd.isna(current_email) or current_email == '' or str(current_email).strip() == '':
                    return True
                else:
                    print(f"⚠️ Email already exists for {url_base}: {current_email} - skipping URL")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking URL in Excel: {e}")
        return True

context_index = 0
contexts = []

def wait_for_captcha(page):
    retries = 5
    while retries > 0:
        recaptcha_div = page.query_selector('div[class*="g-recaptcha"]')
        if recaptcha_div:
            print("✅ Recaptcha element found")
            return recaptcha_div
        else:
            print("🔍 Recaptcha element not found. Retrying...")
            sleep(.5)
        retries -= 1
    return None

def get_email_button(page):
    email_button_selectors = [
        "button:has-text('View email address')",
        "button:has-text('view email address')",
        "button:has-text('Afișează adresa de e-mail')",
        "button:has-text('afișează adresa de e-mail')",
        "button:has-text('Email')",
        "button:has-text('e-mail')",
        "[aria-label*='email' i]"
    ]

    for selector in email_button_selectors:
        email_button = page.query_selector(selector)
        if email_button and email_button.is_visible():
            print(f"✅ Found email button with selector: {selector}")
            return email_button
    print("❌ Email button not found")
    return None

def inject_captcha_token_youtube(page, captcha_solution):
    """
    YouTube-specific token injection based on research.
    YouTube uses a different approach for validating reCAPTCHA tokens.
    """
    print("💉 Injecting captcha token using YouTube-specific method...")
    
    result = page.evaluate(f"""
        (token) => {{
            console.log('Starting YouTube-specific token injection...');
            
            // Method 1: Find or create the standard g-recaptcha-response textarea
            let textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
            if (!textarea) {{
                textarea = document.createElement('textarea');
                textarea.name = 'g-recaptcha-response';
                textarea.id = 'g-recaptcha-response';
                textarea.style.display = 'none';
                document.body.appendChild(textarea);
                console.log('Created new g-recaptcha-response textarea');
            }}
            
            textarea.value = token;
            console.log('Token set in textarea:', token.substring(0, 50) + '...');
            
            // Method 2: Use grecaptcha.getResponse() method to set the response
            if (typeof grecaptcha !== 'undefined') {{
                try {{
                    // Try to get widget ID and set response directly
                    const widgets = Object.keys(window.___grecaptcha_cfg.clients || {{}});
                    widgets.forEach(widgetId => {{
                        try {{
                            // Set the response for each widget
                            if (window.___grecaptcha_cfg.clients[widgetId]) {{
                                window.___grecaptcha_cfg.clients[widgetId].callback = function() {{
                                    console.log('reCAPTCHA callback triggered with token');
                                }};
                            }}
                        }} catch (e) {{
                            console.log('Error setting widget callback:', e);
                        }}
                    }});
                    
                    console.log('Processed grecaptcha widgets:', widgets.length);
                }} catch (e) {{
                    console.log('Error processing grecaptcha:', e);
                }}
            }}
            
            // Method 3: Try to trigger YouTube's specific callback
            // YouTube often has a specific callback for business email captcha
            if (typeof onBusinessEmailCaptchaSubmit !== 'undefined') {{
                try {{
                    onBusinessEmailCaptchaSubmit(token);
                    console.log('Called YouTube onBusinessEmailCaptchaSubmit callback');
                }} catch (e) {{
                    console.log('Error calling onBusinessEmailCaptchaSubmit:', e);
                }}
            }}
            
            // Method 4: Look for YouTube's specific form and inject token there
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {{
                // Look for hidden inputs that might need the token
                let hiddenInput = form.querySelector('input[name="g-recaptcha-response"]');
                if (!hiddenInput) {{
                    hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'g-recaptcha-response';
                    form.appendChild(hiddenInput);
                }}
                hiddenInput.value = token;
                console.log('Token injected into form hidden input');
                
                // Also try common YouTube form field names
                const ytTokenInput = form.querySelector('input[name="recaptcha_token"]') || 
                                   form.querySelector('input[name="captcha_response"]') ||
                                   form.querySelector('input[name="token"]');
                if (ytTokenInput) {{
                    ytTokenInput.value = token;
                    console.log('Token injected into YouTube-specific input field');
                }}
            }});
            
            // Method 5: Fire events that YouTube might be listening for
            ['recaptcha-ready', 'recaptcha-success', 'captcha-solved'].forEach(eventName => {{
                try {{
                    const event = new CustomEvent(eventName, {{ 
                        detail: {{ token: token }},
                        bubbles: true 
                    }});
                    document.dispatchEvent(event);
                    console.log('Fired event:', eventName);
                }} catch (e) {{
                    console.log('Error firing event:', eventName, e);
                }}
            }});
            
            return {{
                success: true,
                textareaExists: !!textarea,
                textareaValue: textarea.value.length,
                grecaptchaExists: typeof grecaptcha !== 'undefined',
                formsProcessed: forms.length
            }};
        }}
    """, captcha_solution)
    
    print(f"💉 YouTube token injection result: {result}")
    sleep(5)  # Wait for YouTube to process the token

def solve_captcha_youtube(page, url, excel_file_path):
    """Enhanced captcha solving specifically for YouTube"""
    recaptcha_div = wait_for_captcha(page)
    if recaptcha_div:
        data_site_key = recaptcha_div.get_attribute('data-sitekey')
        print("✅ Recaptcha data-sitekey:", data_site_key)
    else:
        print("❌ No recaptcha element found")
        return None

    solver = TwoCaptcha("e33f4e34710f054a35a17795f2c7414c")
    if not data_site_key:
        print("❌ No data-sitekey found")
        return False

    try:
        print("🔧 Solving captcha with 2Captcha...")
        result = solver.recaptcha(sitekey=data_site_key, url=page.url)
        captcha_solution = result['code']
        print(f"✅ Captcha solved! Token: {captcha_solution[:50]}...")
    except Exception as e:
        print(f"❌ Error solving captcha: {e}")
        return None

    # YouTube-specific token injection
    inject_captcha_token_youtube(page, captcha_solution)
    
    # Try multiple approaches to submit the form
    print("🚀 Attempting to submit using multiple methods...")
    
    # Method 1: Look for and click the standard submit button
    submit_selectors = [
        "button:has-text('Submit')",
        "button:has-text('Trimite')",
        "button:has-text('Verify')",
        "button:has-text('Verifică')",
        "button:has-text('Continue')",
        "input[type='submit']",
        "button[type='submit']"
    ]
    
    submit_clicked = False
    for selector in submit_selectors:
        try:
            buttons = page.query_selector_all(selector)
            for button in buttons:
                if button.is_visible():
                    print(f"✅ Found submit button: {selector}")
                    try:
                        button.evaluate("element => element.click()")
                        print("✅ Submit clicked with JavaScript")
                        submit_clicked = True
                        break
                    except:
                        try:
                            button.click(force=True)
                            print("✅ Submit clicked with force")
                            submit_clicked = True
                            break
                        except Exception as e:
                            print(f"❌ Click failed: {e}")
            if submit_clicked:
                break
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
    
    # Method 2: If no submit button found, try to submit forms directly
    if not submit_clicked:
        print("🔄 No submit button found, trying to submit forms directly...")
        try:
            forms_submitted = page.evaluate("""
                () => {
                    const forms = document.querySelectorAll('form');
                    let submitted = 0;
                    forms.forEach(form => {
                        try {
                            form.submit();
                            submitted++;
                        } catch (e) {
                            console.log('Error submitting form:', e);
                        }
                    });
                    return submitted;
                }
            """)
            if forms_submitted > 0:
                print(f"✅ Submitted {forms_submitted} forms directly")
                submit_clicked = True
        except Exception as e:
            print(f"❌ Error submitting forms directly: {e}")
    
    # Method 3: Try to trigger YouTube's specific submission logic
    if not submit_clicked:
        print("🎯 Attempting YouTube-specific submission...")
        try:
            page.evaluate(f"""
                () => {{
                    // Try to trigger YouTube's business email reveal
                    if (typeof window.ytInitialData !== 'undefined') {{
                        console.log('Found YouTube data, attempting to trigger email reveal...');
                    }}
                    
                    // Fire a submit event on the document
                    const submitEvent = new Event('submit', {{ bubbles: true }});
                    document.dispatchEvent(submitEvent);
                    
                    // Try to find and trigger any click handlers
                    const clickableElements = document.querySelectorAll('[onclick], [data-command], button');
                    clickableElements.forEach(el => {{
                        if (el.textContent.toLowerCase().includes('submit') || 
                            el.textContent.toLowerCase().includes('trimite') ||
                            el.textContent.toLowerCase().includes('verify')) {{
                            try {{
                                el.click();
                                console.log('Clicked element:', el.textContent.trim());
                            }} catch (e) {{
                                console.log('Error clicking element:', e);
                            }}
                        }}
                    }});
                    
                    return true;
                }}
            """)
            print("✅ Triggered YouTube-specific submission logic")
            submit_clicked = True
        except Exception as e:
            print(f"❌ Error with YouTube-specific submission: {e}")
    
    if not submit_clicked:
        print("❌ Could not submit the captcha in any way")
        return None
    
    # Wait longer for YouTube to process the request
    print("⏳ Waiting for YouTube to process the captcha...")
    sleep(15)  # Increased wait time for YouTube processing
    
    # Check for limit messages with enhanced detection
    limit_detected = page.evaluate("""
        () => {
            const limitMessages = [
                "reached today's access limit",
                "daily limit reached", 
                "access limit reached",
                "you've reached today's access limit",
                "email address hidden",
                "limita de accesări",
                "adresa de e-mail este ascunsă",
                "ai atins limita",
                "limita zilnică"
            ];
            
            const pageText = document.body.innerText.toLowerCase();
            for (const msg of limitMessages) {
                if (pageText.includes(msg.toLowerCase())) {
                    return msg;
                }
            }
            return false;
        }
    """)
    
    if limit_detected:
        print(f"⚠️ Daily limit detected: {limit_detected}")
        return False
    
    # Try to extract email
    extracted_email = extract_email_from_page(page)
    if extracted_email:
        print(f"✅ Email successfully extracted: {extracted_email}")
        save_email_to_excel(url, extracted_email, excel_file_path)
        return True
    
    print("❌ Failed to extract email after captcha resolution.")
    return None

def run_youtube_optimized(contexts, url, excel_file_path):
    global context_index
    if context_index >= len(contexts):
        print("❌ All available contexts have been used.")
        return "STOP"
    
    if not should_process_url(url, excel_file_path):
        return "CONTINUE"
    
    print(f"🔄 Using context {context_index+1}/{len(contexts)} for URL: {url}")
    
    page = contexts[context_index].new_page()
    
    try:
        page.goto(url, timeout=30000)
        sleep(5)
        
        btn = get_email_button(page)
        if btn:
            print("👆 Clicking email button...")
            btn.click()
            sleep(5)
            
            result = solve_captcha_youtube(page, url, excel_file_path)
            if result is True:
                print(f"✅ Successfully processed {url}")
                page.close()
                return "CONTINUE"
            elif result is False:
                print("⚠️ LIMIT reached for this context!")
                context_index += 1
                page.close()
                return run_youtube_optimized(contexts, url, excel_file_path)
            else:
                print(f"❌ Failed to process {url}")
                page.close()
                return "CONTINUE"
        else:
            print(f"❌ No email button found on {url}")
            page.close()
            return "CONTINUE"
    except Exception as e:
        print(f"❌ Error processing {url}: {e}")
        page.close()
        return "CONTINUE"

def execute_youtube_flow():
    available_auth_states = get_available_auth_states()
    
    if not available_auth_states:
        print(f"❌ No auth state files found!")
        return
    
    print(f"✅ Found {len(available_auth_states)} auth state files")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-dev-shm-usage",
                "--no-sandbox"
            ]
        )
        
        # Create contexts
        for auth_state in available_auth_states:
            try:
                context = browser.new_context(
                    storage_state=auth_state,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                contexts.append(context)
                print(f"✅ Created context for {os.path.basename(auth_state)}")
            except Exception as e:
                print(f"❌ Failed to create context for {auth_state}: {e}")
        
        if not contexts:
            print("❌ No contexts could be created.")
            return
        
        excel_file = os.path.join(SCRIPT_DIR, "2_Doc_Completed.xlsx")
        
        if not os.path.exists(excel_file):
            print(f"❌ Excel file not found at {excel_file}")
            return
        
        try:
            df = pd.read_excel(excel_file)
            print(f"📊 Loaded {len(df)} rows from Excel")
            
            if 'URL' not in df.columns:
                print("❌ Error: 'URL' column not found in the Excel file.")
                return
            
            # Count existing emails
            if 'Email' in df.columns:
                emails_exist = df['Email'].notna() & (df['Email'] != '')
                existing_count = emails_exist.sum()
                remaining_count = len(df) - existing_count
                print(f"📧 {existing_count} emails already exist, {remaining_count} remaining to process")
            
            processed_count = 0
            success_count = 0
            
            global context_index
            for index, row in df.iterrows():
                url = row['URL']
                if pd.notna(url) and url:
                    url = url.rstrip('/')
                    modified_url = f"{url}/about"
                    print(f"\n[{index+1}/{len(df)}] 🎯 Processing: {url}")
                    
                    status = run_youtube_optimized(contexts, modified_url, excel_file)
                    processed_count += 1
                    
                    if status == "STOP":
                        print("🛑 All contexts exhausted for this URL. Moving to next URL.")
                        continue
                    elif status == "CONTINUE":
                        # Check if email was actually added
                        try:
                            df_check = pd.read_excel(excel_file)
                            matching_rows = df_check.loc[df_check['URL'].str.rstrip('/') == url]
                            if len(matching_rows) > 0:
                                current_email = matching_rows['Email'].iloc[0] if 'Email' in df_check.columns else ''
                                if pd.notna(current_email) and current_email != '':
                                    success_count += 1
                        except:
                            pass
                else:
                    print(f"⚠️ Skipping row {index} because URL is empty")
                    
            print(f"\n🎉 Processing complete!")
            print(f"📊 Final stats: {success_count} emails extracted from {processed_count} processed channels")
            
        except Exception as e:
            print(f"❌ Error: An error occurred while processing the Excel file: {str(e)}")
        
        browser.close()

if __name__ == "__main__":
    execute_youtube_flow()