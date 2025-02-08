from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import requests
import json
import logging
import sys
import re



# Configuration
GROUP_NAME = "<chat_name>"  # add chat name here 
MENTION_TAG = "@name" # change mention tag or have a secret code
OLLAMA_API_URL = "<url>" # ollama local host url 
DEEPSEEK_MODEL = "deepseek-r1:1.5b" # # this code is configured for Deep Seek R1  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def clean_text(text):
    replacements = {
        'ðŸ˜Š': ':)',
        'ðŸ˜': ':)',
        'ğŸ˜': ':)',
        'ä¸»ä¹‰': '',
        '€™': "'",
        '€"': "-",
        'â€"': "-",
        'â€™': "'",
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = ' '.join(text.split())
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\[\s*\]', '', text)
    
    return text.strip()

def clean_message(text):

    if '@' in text:
        text = '@' + text.split('@', 1)[1]

    # Clean text 
    text = re.sub(r'\d{1,2}:\d{1,2}(?:\s*[AaPpMm]{2})?', '', text)
    text = re.sub(rf'@?{MENTION_TAG}\s*', '', text, flags=re.IGNORECASE)
    text = clean_text(text)
    text = ' '.join(text.split())
    
    return text.strip()

def generate_thinking_message(message):
    thinking_templates = [
        "**Thinking...**",
        "**Processing...**",
        "**Analyzing...**",
        "**Let me think...**"
    ]
    import random
    return random.choice(thinking_templates)

def process_deepseek_response(text):
    think_pattern = r'<think>(.*?)</think>'
    thinking_parts = re.findall(think_pattern, text, re.DOTALL)
    thinking = '\n'.join(thinking_parts).strip() if thinking_parts else ""
    
    final_response = re.sub(think_pattern, '', text, flags=re.DOTALL)
    final_response = final_response.strip()
    
    return thinking, final_response

def deepseek_reply(prompt):
    cleaned_prompt = clean_message(prompt)
    
    thinking = generate_thinking_message(cleaned_prompt)
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "prompt": cleaned_prompt
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        full_response = []
        for line in response.text.strip().split('\n'):
            if not line:
                continue
                
            try:
                json_response = json.loads(line)
                if json_response.get("done") is True:
                    break
                    
                response_text = json_response.get("response", "")
                if response_text:
                    full_response.append(response_text)
            except json.JSONDecodeError:
                continue
        
        complete_text = ''.join(full_response)
        thinking_content, final_response = process_deepseek_response(complete_text)
        
        final_response = clean_text(final_response)
        
        return thinking, final_response if final_response else "⚠️ No response generated"
    
    except requests.exceptions.RequestException as e:
        logging.error(f"⚠️ DeepSeek API Request Error: {e}")
        return thinking, "⚠️ Unable to generate a response at this time."
    except Exception as e:
        logging.error(f"⚠️ Unexpected error: {str(e)}")
        return thinking, "⚠️ An unexpected error occurred"

def send_message(driver, text, max_retries=3, retry_delay=2):
    input_box_selectors = [
        "//div[@contenteditable='true'][@data-tab='10']",
        "//footer//div[@contenteditable='true']",
        "//div[contains(@class, '_3Uu1_')]",
        "//div[@title='Type a message']"
    ]
    
    retry_count = 0
    while retry_count < max_retries:
        for selector in input_box_selectors:
            try:
                input_box = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                
                input_box.clear()
                
                try:
                    input_box.send_keys(text)
                except:
                    try:
                        driver.execute_script("arguments[0].textContent = arguments[1]", input_box, text)
                    except:
                        actions = ActionChains(driver)
                        actions.move_to_element(input_box)
                        actions.click()
                        actions.send_keys(text)
                        actions.perform()
                
                time.sleep(1)
                
                try:
                    input_box.send_keys(Keys.ENTER)
                except:
                    try:
                        send_button = driver.find_element(By.XPATH, "//span[@data-icon='send']")
                        send_button.click()
                    except:
                        driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}))", input_box)
                
                logging.info("✅ Message sent successfully")
                return True
                
            except Exception as e:
                logging.warning(f"Failed with selector {selector}: {str(e)}")
                continue
        
        retry_count += 1
        if retry_count < max_retries:
            logging.info(f"Retrying message send (attempt {retry_count + 1}/{max_retries})...")
            time.sleep(retry_delay)
    
    raise Exception("Failed to send message with all available methods")

def find_group(driver):
    try:
        search_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        search_box.click()
        search_box.send_keys(GROUP_NAME)
        time.sleep(2)
        search_box.send_keys(Keys.ENTER)
        logging.info(f"✅ Opened group: {GROUP_NAME}")
    except Exception as e:
        logging.error(f"❌ Failed to open group '{GROUP_NAME}': {e}")
        driver.quit()
        sys.exit(1)


def main():
    driver = webdriver.Chrome()
    driver.get("https://web.whatsapp.com")
    
    input("📷 Scan the QR Code on WhatsApp Web and press Enter when ready.")
    logging.info("✅ Logged into WhatsApp Web successfully.")
    
    find_group(driver)
    
    last_message = ""
    logging.info("✅ Bot is now running... Monitoring messages for mentions of @حمزة.")
    
    while True:
        try:
            messages = driver.find_elements(By.XPATH, "//div[contains(@class, 'message-in')]")
            
            if messages:
                new_message = messages[-1].text
                
                if MENTION_TAG in new_message and new_message != last_message:
                    cleaned_message = clean_message(new_message)
                    logging.info(f"📩 New message mentioning {MENTION_TAG} detected: {cleaned_message}")
                    
                    thinking_msg, response_text = deepseek_reply(cleaned_message)
                    
                    try:
                        send_message(driver, thinking_msg)
                        time.sleep(2)  
                        
                        send_message(driver, response_text)
                        last_message = new_message
                    except Exception as e:
                        logging.error(f"❌ Failed to send reply: {e}")
            
            time.sleep(3)
            
        except Exception as e:
            logging.error(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()