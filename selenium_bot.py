import json
import os
import threading
import time
import urllib.request
from xvfb_manager import DISPLAY_NUM
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

_stop_event = threading.Event()

_driver = None
_starting = False
_driver_lock = threading.Lock()
_ffmpeg_proc = None
_bot_thread = None

def create_driver(user_agent=None):

    options = Options()
    options.binary_location = "/usr/bin/chromium"

    prefs = {"profile.default_content_setting_values.notifications": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--lang=en")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_experimental_option("detach", True)
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("disable-blink-features")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-gpu')
    options.add_argument("--log-level=3")
    options.add_experimental_option('w3c', True)
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument('--disable-logging')
    options.add_argument("--mute-audio")
    options.add_argument("--no-sandbox")
    options.add_argument('--window-size=1280,720')
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")

    # crx_path = os.path.expanduser("~/NopeCHA.crx")
    # if os.path.exists(crx_path):
    #     options.add_extension(crx_path)
    # else:
    #     print(f"NopeCHA.crx not found at {crx_path}")

    service = Service(executable_path="/usr/bin/chromedriver")
    service.env = {"DISPLAY": DISPLAY_NUM}
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def load_cookies(driver, filepath):
    with open(filepath) as f:
        cookies = json.load(f)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Cookie add failed: {cookie.get('name')}: {e}")

def should_stop():
    return _stop_event.is_set()

def interruptible_sleep(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if _stop_event.is_set():
            return
        time.sleep(min(0.5, end - time.time()))

def wait_for_ad_watched():
    path = os.path.expanduser("~/ad_watched.json")
    if os.path.exists(path):
        os.remove(path)
    while not _stop_event.is_set():
        if os.path.exists(path):
            os.remove(path)
            return True
        interruptible_sleep(1)
    return False

def notify_ad_ready():
    try:
        port_path = os.path.expanduser("~/flask.port")
        token_path = os.path.expanduser("~/flask.token")
        if not os.path.exists(port_path):
            return
        port = open(port_path).read().strip()
        token = ""
        if os.path.exists(token_path):
            token = open(token_path).read().strip()
        url = f"http://127.0.0.1:{port}/bot/ad_ready?token={token}"
        req = urllib.request.Request(url, data=b'{}', method='POST')
        req.add_header('Content-Type', 'application/json')
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"notify_ad_ready failed: {e}")

def close_tap(driver:webdriver) -> None:
        try:
            handles = driver.window_handles 
            if len(handles) >1:
                for cls in range(len(handles)-1,-1,-1):
                    driver.switch_to.window(driver.window_handles[cls])
                    if cls >0:
                        driver.close()
        except:
            pass     

def complete_page(driver, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        if _stop_event.is_set():
            return False
        try:
            page_state = driver.execute_script("return document.readyState;")
            if page_state == "complete":
                return True
        except:
            return False
        interruptible_sleep(1)
    return False

def check_h_captcha(driver):
    hcaptcha_selectors = [
        "iframe[src*='hcaptcha']",
        "iframe[title*='hCaptcha']",
        ".h-captcha",
        "[data-hcaptcha-widget-id]"
    ]
    
    for selector in hcaptcha_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements and elements[0].is_displayed():
                return True
        except Exception:
            pass
            
    return False


def start_bot(user_agent=None):
    global _bot_thread
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "start_bot_aviso.py")):
        print("ERROR: start_bot_aviso.py not found!")
        return False
    from start_bot_aviso import _bot_worker
    if not user_agent:
        ua_path = os.path.expanduser("~/user_agent.json")
        if os.path.exists(ua_path):
            with open(ua_path) as f:
                user_agent = json.load(f).get("user_agent", "")
    with _driver_lock:
        if _driver is not None:
            return False
        _starting = True
        _stop_event.clear()
    thread = threading.Thread(target=_bot_worker, args=(user_agent,), daemon=True)
    thread.start()
    _bot_thread = thread
    return True

def stop_bot():
    global _bot_thread
    _stop_event.set()
    from xvfb_manager import _kill_all
    _kill_all()
    if _bot_thread is not None and _bot_thread is not threading.current_thread():
        _bot_thread.join(timeout=10)
    _bot_thread = None

def is_running():
    with _driver_lock:
        return _starting or _driver is not None
