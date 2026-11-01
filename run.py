import os
import sys
import socket
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from backend.config import settings


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a TCP port is currently occupied on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_available_port(start_port: int = 8555, max_attempts: int = 50) -> int:
    """Finds the next unreserved, free port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p):
            return p
    return start_port


def open_browser_delayed(url: str, delay_sec: float = 1.2):
    """Opens browser after server has started listening."""
    time.sleep(delay_sec)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[!] Could not launch default browser automatically: {e}")
        print(f"[*] Please open your browser and navigate manually to: {url}")


def main():
    target_port = settings.PORT

    # If configured port is busy or was the default 8000, find next free port starting from 8555
    if target_port == 8000 or is_port_in_use(target_port):
        free_port = find_available_port(start_port=8555)
        print(f"\n[!] Notice: Port {target_port} is reserved or in use.")
        print(f"[*] Automatically assigned available port: {free_port}\n")
        target_port = free_port
        settings.PORT = free_port

    server_url = f"http://127.0.0.1:{target_port}/?token={settings.SESSION_TOKEN}"

    print("=" * 72)
    print("   Windows Hardware Diagnostics & Optimizer (Hook 31)")
    print(f"   📍 Web Interface: {server_url}")
    print(f"   🔑 Session Security Token: {settings.SESSION_TOKEN}")
    print(f"   🤖 AI Engine Model: {settings.OPENCODE_GO_MODEL}")
    print("=" * 72)
    print("\n[*] Starting FastAPI local server... (Press Ctrl+C to stop)\n")

    # Launch browser in a background thread
    threading.Thread(target=open_browser_delayed, args=(server_url,), daemon=True).start()

    # Run Uvicorn directly in foreground
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=target_port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
