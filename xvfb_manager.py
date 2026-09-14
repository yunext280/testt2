import os
import subprocess
import time

DISPLAY_NUM = ":99"


def _start_xvfb():
    print("Starting Xvfb...")
    subprocess.Popen(
        ["sudo", "Xvfb", DISPLAY_NUM, "-screen", "0", "1280x720x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)
    subprocess.run(["xhost", "+local:"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _kill_all():
    print("Cleaning old processes and preparing environment...")
    subprocess.run(["pkill", "-9", "-f", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "ffmpeg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "pkill", "-9", "-f", "Xvfb"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "rm", "-f", f"/tmp/.X{DISPLAY_NUM.replace(':', '')}-lock"])
    subprocess.run(["sudo", "rm", "-rf", "/tmp/.X11-unix"])
    subprocess.run(["sudo", "mkdir", "-p", "/tmp/.X11-unix"])
    subprocess.run(["sudo", "chown", "root:root", "/tmp/.X11-unix"])
    subprocess.run(["sudo", "chmod", "1777", "/tmp/.X11-unix"])


def start_ffmpeg():
    cmd = [
        'ffmpeg', '-y',
        '-f', 'x11grab',
        '-video_size', '1280x720',
        '-draw_mouse', '0',
        '-i', DISPLAY_NUM,
        '-f', 'image2',
        '-update', '1',
        '-vcodec', 'mjpeg',
        '-q:v', '5',
        'udp://127.0.0.1:9999?pkt_size=60000'
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
