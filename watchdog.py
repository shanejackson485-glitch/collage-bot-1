import subprocess
import time
import socket
import os
import signal

bot_process = None

def internet_connected(host="1.1.1.1", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def start_bot():
    global bot_process
    if bot_process is None or bot_process.poll() is not None:
        print("[WATCHDOG] Starting bot...")
        bot_process = subprocess.Popen(["python", "collage.py"])
    else:
        print("[WATCHDOG] Bot is already running.")

def stop_bot():
    global bot_process
    if bot_process is not None and bot_process.poll() is None:
        print("[WATCHDOG] Stopping bot due to no internet...")
        bot_process.terminate()
        try:
            bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_process.kill()
    bot_process = None

def main():
    while True:
        if internet_connected():
            start_bot()
        else:
            stop_bot()
        time.sleep(500)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_bot()
        print("[WATCHDOG] Exiting.")