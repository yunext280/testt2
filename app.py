import os, socket, json, threading, time
import requests
from flask import Flask, request, abort, render_template, jsonify, send_file, Response
from installer import is_service_ready, run_install_script

# Bot init: if the libs are missing at startup, fall back to a dummy bot to avoid a crash
LIBS_INSTALLED = is_service_ready("aviso")
if LIBS_INSTALLED:
    try:
        import selenium_bot
    except ImportError:
        LIBS_INSTALLED = False

if not LIBS_INSTALLED:
    class DummySeleniumBot:
        @staticmethod
        def start_bot(*args, **kwargs): return False
        @staticmethod
        def stop_bot(*args, **kwargs): pass
        @staticmethod
        def is_running(): return False
    selenium_bot = DummySeleniumBot()

app = Flask(__name__)
TOKEN = os.environ.get("TOKEN", "")

latest_frame = None
ad_pending = False
installing_service = None
install_progress = 0

VERSION = "0"
try:
    with open(os.path.expanduser("~/version.md")) as f:
        VERSION = f.read().strip()
except:
    pass

def read_captcha_solv():
    try:
        with open(os.path.expanduser("~/captcha_solv.json")) as f:
            return json.load(f)
    except Exception:
        return {}

@app.before_request
def check_token():
    if request.path.startswith("/static/"):
        return
    if request.args.get("token") != TOKEN:
        abort(403)

@app.route("/")
def index():
    return render_template("index.html", version=VERSION, token=TOKEN)

@app.route("/aviso")
def aviso():
    aviso_done = os.path.exists(os.path.expanduser("~/aviso_cookies.json"))
    # yt_done = os.path.exists(os.path.expanduser("~/youtube_cookies.json"))
    bot_started = False
    sel_path = os.path.expanduser("~/sel_bot.json")
    if os.path.exists(sel_path):
        with open(sel_path) as f:
            data = json.load(f)
            bot_started = data.get("start", False)
    ready = is_service_ready("aviso")
    solv = read_captcha_solv()
    return render_template("aviso.html", version=VERSION,
                           aviso_done=aviso_done,  # yt_done=yt_done,
                           bot_started=bot_started,
                           libs_installed=ready,
                           captcha_key=solv.get("captcha_key", ""),
                           captcha_balance=solv.get("balance_solv", ""),
                           token=TOKEN)

@app.route("/seotime")
def seotime():
    return render_template("seotime.html", version=VERSION)

@app.route("/set_user_agent", methods=["POST"])
def set_user_agent():
    data = request.get_json(force=True)
    ua = data.get("user_agent", "")
    if ua:
        with open(os.path.expanduser("~/user_agent.json"), "w") as f:
            json.dump({"user_agent": ua}, f)
    return jsonify({"status": "ok"})

@app.route("/set_cookies", methods=["POST"])
def set_cookies():
    site = request.args.get("site", "unknown")
    try:
        data = request.get_json(force=True)
        path = os.path.expanduser(f"~/{site}_cookies.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/set_captcha_key", methods=["POST"])
def set_captcha_key():
    try:
        data = request.get_json(force=True)
        key = data.get("captcha_key", "").strip()
        if not key:
            return jsonify({"status": "error", "message": "Empty key"}), 400
        path = os.path.expanduser("~/captcha_solv.json")
        store = read_captcha_solv()
        store["captcha_key"] = key
        with open(path, "w") as f:
            json.dump(store, f, indent=2)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/captcha_balance", methods=["POST"])
def captcha_balance():
    store = read_captcha_solv()
    key = store.get("captcha_key", "")
    if not key:
        return jsonify({"balance": None})
    full_key = key
    try:
        resp = requests.get(
            "https://ru2.sctg.xyz/res.php?",
            params={"key": full_key, "action": "getbalance"},
            timeout=15,
        )
        balance = resp.text.strip()
    except Exception:
        balance = ""
    store["balance_solv"] = balance
    path = os.path.expanduser("~/captcha_solv.json")
    with open(path, "w") as f:
        json.dump(store, f, indent=2)
    return jsonify({"balance": balance if balance else None})

@app.route("/install_deps", methods=["POST"])
def install_deps():
    global installing_service, install_progress, LIBS_INSTALLED, selenium_bot
    data = request.get_json(force=True) if request.is_json else {}
    service = data.get("service", "aviso")

    if is_service_ready(service):
        return jsonify({"status": "already_installed"})

    if installing_service:
        return jsonify({"status": "installing", "service": installing_service, "progress": install_progress})

    def update_prog(val):
        global install_progress
        install_progress = val

    def worker():
        global installing_service, LIBS_INSTALLED, selenium_bot
        installing_service = service
        try:
            run_install_script(service, progress_callback=update_prog)
            if is_service_ready("aviso"):
                LIBS_INSTALLED = True
                try:
                    import selenium_bot as real_bot
                    selenium_bot = real_bot
                except ImportError:
                    pass
        except Exception as e:
            print(f"Installation error: {e}")
        finally:
            installing_service = None

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "started", "progress": install_progress})

@app.route("/bot/start", methods=["POST"])
def bot_start():
    global ad_pending
    if not is_service_ready("aviso"):
        return jsonify({"status": "error", "message": "Required dependencies not installed"}), 400

    ad_path = os.path.expanduser("~/ad_watched.json")
    try:
        os.remove(ad_path)
    except OSError:
        pass
    ad_pending = False
    data = request.get_json(force=True)
    user_agent = data.get("user_agent", "")
    started = selenium_bot.start_bot(user_agent)
    sel_path = os.path.expanduser("~/sel_bot.json")
    with open(sel_path, "w") as f:
        json.dump({"start": started}, f)
    return jsonify({"status": "ok" if started else "already_running"})

@app.route("/bot/stop", methods=["POST"])
def bot_stop():
    global latest_frame
    selenium_bot.stop_bot()
    sel_path = os.path.expanduser("~/sel_bot.json")
    with open(sel_path, "w") as f:
        json.dump({"start": False}, f)
    latest_frame = None
    ss_path = os.path.expanduser("~/aviso_screenshot.png")
    try:
        os.remove(ss_path)
    except OSError:
        pass
    return jsonify({"status": "ok"})

@app.route("/bot/ad_watched", methods=["POST"])
def bot_ad_watched():
    global ad_pending
    ad_pending = False
    path = os.path.expanduser("~/ad_watched.json")
    with open(path, "w") as f:
        json.dump({"watched": True, "time": time.time()}, f)
    return jsonify({"status": "ok"})

@app.route("/bot/ad_ready", methods=["POST"])
def bot_ad_ready():
    global ad_pending
    ad_pending = True
    return jsonify({"status": "ok"})

@app.route("/screenshot/aviso")
def screenshot_aviso():
    path = os.path.expanduser("~/aviso_screenshot.png")
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return "", 404

def listen_udp():
    global latest_frame
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 9999))
    sock.settimeout(1)
    buf = b''
    while True:
        try:
            data, _ = sock.recvfrom(65535)
            if not data:
                continue
            if b'\xff\xd8' in data:
                buf = data[data.find(b'\xff\xd8'):]
            else:
                buf += data
            if b'\xff\xd9' in buf:
                latest_frame = buf[:buf.find(b'\xff\xd9')+2]
                buf = b''
        except socket.timeout:
            continue
        except:
            pass

@app.route("/video_feed")
def video_feed():
    def gen():
        global latest_frame
        while True:
            if latest_frame is not None:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
            time.sleep(0.04)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/stream_status")
def stream_status():
    return jsonify({
        "active": latest_frame is not None and selenium_bot.is_running(),
        "bot_running": selenium_bot.is_running(),
        "aviso_valid": os.path.exists(os.path.expanduser("~/aviso_cookies.json")),
        # "yt_valid": os.path.exists(os.path.expanduser("~/youtube_cookies.json")),
        "libs_installed": is_service_ready("aviso"),
        "installing_libs": installing_service is not None,
        "installing_service": installing_service,
        "install_progress": install_progress,
        "ad_pending": ad_pending
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot_running": selenium_bot.is_running(),
        "libs_installed": is_service_ready("aviso"),
        "version": VERSION
    })

def auto_restart_bot():
    import json as _json
    if not is_service_ready("aviso"):
        return
    sel_path = os.path.expanduser("~/sel_bot.json")
    if os.path.exists(sel_path):
        try:
            with open(sel_path) as f:
                data = _json.load(f)
                if data.get("start", False):
                    selenium_bot.start_bot()
        except:
            pass

if __name__ == "__main__":
    threading.Thread(target=listen_udp, daemon=True).start()
    threading.Thread(target=auto_restart_bot, daemon=True).start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    with open(os.path.expanduser("~/flask.port"), "w") as f:
        f.write(str(port))
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)
