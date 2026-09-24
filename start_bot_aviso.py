import os
import decryptor
av = os.path.expanduser("~/aviso_bot.py.enc")
if os.path.exists(av):
    decryptor.dectfil(av, "aviso_bot")
    os.remove(av)
from xvfb_manager import _start_xvfb, _kill_all, start_ffmpeg, DISPLAY_NUM
from selenium_bot import (
    create_driver, should_stop, interruptible_sleep,
    wait_for_ad_watched, notify_ad_ready, _stop_event,
    _driver, _driver_lock, _starting, _ffmpeg_proc
)
import selenium_bot
from aviso_bot import (
    login_aviso, Surfing, scrol_Surfing,
    av_ytub, av_ytub_ref, yt_url, chek_captcha
)

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
            Surfing_ads = Surfing(driver,30)
            for Surfing_ad in Surfing_ads:
                if should_stop():
                    print("STOP: Bot stopped during ad execution")
                    return
                scrol_Surfing(driver,30,Surfing_ad)

            # notify_ad_ready()
            # if not wait_for_ad_watched():
            #     print("STOP: Bot stopped while waiting for ad")
            #     return
            all_tube = av_ytub(driver,30)
            skrol = 0
            for tube in all_tube:
                veryfi = av_ytub_ref(driver,30,tube)
                # if skrol > 0 and skrol % 10 ==0 :
                #     notify_ad_ready()
                #     if not wait_for_ad_watched():
                #         print("STOP: Bot stopped while waiting for ad")
                #         return
                if "data" not in veryfi:
                    while chek_captcha(driver,30//3):
                        interruptible_sleep(1)
                    yt_url(driver,30,veryfi['sek'],veryfi["tub_id"])
                elif veryfi["data"] == 'break':
                    break
                skrol += 1
        else:
            return
        driver.save_screenshot(os.path.expanduser("~/aviso_screenshot.png"))
        _stop_event.wait()
    except Exception as e:
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
