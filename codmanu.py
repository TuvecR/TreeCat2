import os
from time import sleep
import pandas as pd
from twocaptcha import TwoCaptcha
from playwright.sync_api import sync_playwright

# Setează calea către fișierul de autentificare relativ la script (Windows friendly)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_STATE = os.path.join(SCRIPT_DIR, "auth-state.json")

context_index = 0
contexts = []

def wait_for_captcha(page):
    retries = 3  # Number of retries
    while retries > 0:
        recaptcha_div = page.query_selector('div[class*="g-recaptcha"]')
        if recaptcha_div:
            print("Recaptcha element found")
            return recaptcha_div
        else:
            print("Recaptcha element not found. Retrying...")
            sleep(.2)
        retries -= 1
    return None

def get_email_button(page):
    email_button_selectors = [
        "button:has-text('View email address')",
        "button:has-text('view email address')",
        "button:has-text('Afișează adresa de e-mail')",
        "button:has-text('afișează adresa de e-mail')",
        "button:has-text('Afiseaza adresa de e-mail')",
        "button:has-text('afiseaza adresa de e-mail')",
        "button:has-text('Email')",
        "button:has-text('e-mail')",
        "button:has-text('E-mail')",
        "[aria-label*='email' i]",
        "[aria-label*='e-mail' i]"
    ]

    for selector in email_button_selectors:
        email_button = page.query_selector(selector)
        if email_button and email_button.is_visible():
            print(f"✅ Found email button with selector: {selector}")
            return email_button
    print("❌ Email button not found")
    return None

def get_submit_button(page):
    retries = 3
    submit_button_selectors = [
        "button:has-text('Submit')",
        "button:has-text('Trimite')",
        "button:has-text('Verify')",
        "button:has-text('Verifică')",
        "button:has-text('Continue')",
        "button:has-text('Continuă')",
        "input[type='submit']",
        "button[type='submit']"
    ]
    while retries > 0:
        for selector in submit_button_selectors:
            submit_button = page.query_selector(selector)
            if submit_button and submit_button.is_visible():
                print(f"✅ Found submit button with selector: {selector}")
                return submit_button
        retries -= 1
        sleep(.1)
    print("❌ submit button not found")
    return None

def solve_captcha(page):
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
        return None

    try:
        result = solver.recaptcha(sitekey=data_site_key, url=page.url)
        captcha_solution = result['code']
        print("✅ Recaptcha solution:", captcha_solution)
    except Exception as e:
        print(f"❌ Error solving captcha: {e}")
        return None

    # Injectează tokenul în textarea-ul captcha
    inject_captcha_token(page, captcha_solution)
    sleep(2)
    submit_button = get_submit_button(page)
    if not submit_button:
        print("❌ Could not find submit button after setting captcha token.")
        return None
    submit_button.click()
    sleep(5)
    # Verifică dacă a apărut mesajul de limită
    limit_message = page.query_selector("td:text-is('Email address hidden. You\\'ve reached today\\'s access limit.')")
    if limit_message:
        print("⚠ Daily limit reached for this context.")
        return False
    # Verifică dacă emailul este vizibil
    email_element = page.query_selector("td a#email")
    if email_element and email_element.text_content().strip():
        print(f"✅ Email found: {email_element.text_content().strip()}")
        return True
    print("❌ Failed to find email after submitting captcha. The page might have an error or a different layout.")
    return None

def inject_captcha_token(page, captcha_solution):
    page.evaluate(f"""
        const token = '{captcha_solution}';
        let textarea = document.getElementById('g-recaptcha-response');
        if (!textarea) {{
            textarea = document.createElement('textarea');
            textarea.id = 'g-recaptcha-response';
            textarea.name = 'g-recaptcha-response';
            document.body.appendChild(textarea);
        }}
        textarea.style.display = 'block';
        textarea.style.visibility = 'visible';
        textarea.style.opacity = 1;
        textarea.value = token;
        textarea.removeAttribute('hidden');
        textarea.removeAttribute('aria-hidden');
        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
    """)
    sleep(2)

def run(contexts, url):
    global context_index
    if context_index >= len(contexts):
        print("❌ All available contexts have been used or have reached their daily limit.")
        return "STOP"
    page = contexts[context_index].new_page()
    page.goto(url)
    wait_for_captcha(page)
    btn = get_email_button(page)
    if btn:
        btn.click()
        sleep(2)
        result = solve_captcha(page)
        if result is True:
            print(f"✅ Successfully processed {url}")
            page.close()
            return "CONTINUE"
        elif result is False:
            context_index += 1
            print(f"Switching to next context (index {context_index})")
            page.close()
            return run(contexts, url)
        else:
            print(f"Skipping URL {url} due to an unknown error.")
            page.close()
            return "CONTINUE"
    else:
        print(f"No email button found on {url}. Skipping.")
        page.close()
        return "CONTINUE"

def execute_flow():
    # Verifică dacă fișierul de autentificare există
    if not os.path.exists(AUTH_STATE):
        print(f"❌ Fișierul de autentificare {AUTH_STATE} nu există! Rulează save_profile.py pentru a-l crea.")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-automation",
                "--disable-infobars"
            ]
        )
        context1 = browser.new_context(
            storage_state=AUTH_STATE,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        contexts.append(context1)
        # Citește fișierul Excel din același folder cu scriptul
        excel_file = os.path.join(SCRIPT_DIR, "2_Doc_Completed.xlsx")
        try:
            df = pd.read_excel(excel_file)
            if 'URL' not in df.columns:
                print("Error: 'URL' column not found in the Excel file.")
                return
            for index, row in df.iterrows():
                url = row['URL']
                if pd.notna(url) and url:
                    url = url.rstrip('/')
                    modified_url = f"{url}/about"
                    status = run(contexts, modified_url)
                    if status == "STOP":
                        print("Stopping the process as all contexts are exhausted.")
                        break
                else:
                    print(f"Skipping row {index} because URL is empty or not available")
        except Exception as e:
            print(f"Error: An error occurred while processing the Excel file: {str(e)}")
        browser.close()

if __name__ == "__main__":
    execute_flow()