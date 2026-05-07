import subprocess
import time
import sys
import os

def run_backend():
    print("Starting FastAPI Backend...")
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"])

def run_bot():
    print("Starting Telegram Bot...")
    return subprocess.Popen([sys.executable, "bot/bot_main.py"])

if __name__ == "__main__":
    if not os.path.exists("sales_bot.db"):
        print("Initializing database...")
        subprocess.run([sys.executable, "database/db.py"])
    
    backend_proc = run_backend()
    time.sleep(2) # Wait for backend to start
    bot_proc = run_bot()
    
    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend stopped. Restarting...")
                backend_proc = run_backend()
            if bot_proc.poll() is not None:
                print("Bot stopped. Restarting...")
                bot_proc = run_bot()
    except KeyboardInterrupt:
        print("Stopping services...")
        backend_proc.terminate()
        bot_proc.terminate()
        print("Done.")
