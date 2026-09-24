import os
import random
import decryptor
av = os.path.expanduser("~/aviso_bot.py.enc")
if os.path.exists(av):
    decryptor.dectfil(av, "aviso_bot")
    os.remove(av)
from xvfb_manager import _start_xvfb, _kill_all, start_ffmpeg, DISPLAY_NUM
from selenium_bot import (
    create_driver, should_stop, interruptible_sleep,
    wait_for_ad_watched, notify_ad_ready, human_order,
    _stop_event, _driver, _driver_lock, _starting, _ffmpeg_proc
)
import selenium_bot
from aviso_bot import (
    login_aviso, Surfing, scrol_Surfing,
    av_ytub, av_ytub_ref, yt_url, chek_captcha
)

def _run_surf(driver):
    Surfing_ads = Surfing(driver,20)
    for i in human_order(len(Surfing_ads)):
        Surfing_ad = Surfing_ads[i]
        if should_stop():
            print("STOP: Bot stopped during ad execution")
            return False
        scrol_Surfing(driver,20,Surfing_ad)

    # notify_ad_ready()
    # if not wait_for_ad_watched():
    #     print("STOP: Bot stopped while waiting for ad")
    #     return
    return True


def _run_tube(driver):
    all_tube = av_ytub(driver,20)
    skrol = 0
    for i in human_order(len(all_tube)):
        tube = all_tube[i]
        veryfi = av_ytub_ref(driver,20,tube)
        # if skrol > 0 and skrol % 10 ==0 :
        #     notify_ad_ready()
        #     if not wait_for_ad_watched():
        #         print("STOP: Bot stopped while waiting for ad")
        #         return
        if "data" not in veryfi:
            while chek_captcha(driver,30//3):
                interruptible_sleep(1)
            yt_url(driver,20,veryfi['sek'],veryfi["tub_id"])
        elif veryfi["data"] == 'break':
            break
        skrol += 1
    return True


def _bot_worker(user_agent):
    try:
        _kill_all()
        _start_xvfb()
        os.environ["DISPLAY"] = DISPLAY_NUM
        selenium_bot._ffmpeg_proc = start_ffmpeg()
        driver = create_driver(user_agent)
        with selenium_bot._driver_lock:
            selenium_bot._driver = driver
        if login_aviso(driver):
            if should_stop():
                print("STOP: Bot stopped before ad display")
                return
            phases = [_run_surf, _run_tube]
            random.shuffle(phases)
            for phase in phases:
                if not phase(driver):
                    return
        else:
            return
        driver.save_screenshot(os.path.expanduser("~/aviso_screenshot.png"))
        _stop_event.wait()
    except Exception as e:
        if should_stop():
            print("STOP: Bot stopped by user")
        else:
            print(f"ERROR: Bot error during execution: {e}")
    finally:
        print("STOP: Closing bot and cleaning up...")
        if selenium_bot._ffmpeg_proc:
            selenium_bot._ffmpeg_proc.kill()
            selenium_bot._ffmpeg_proc = None
        try:
            if selenium_bot._driver:
                selenium_bot._driver.quit()
        except:
            pass
        _kill_all()
        with selenium_bot._driver_lock:
            selenium_bot._driver = None
            selenium_bot._starting = False
