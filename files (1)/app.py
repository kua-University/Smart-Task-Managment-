"""
Smart Task Management System
Run:  python app.py  →  http://127.0.0.1:5000
"""

import os
import threading
import time
import webbrowser

from flask import Flask

from database import init_db
from routes import register_routes

app = Flask(__name__)
register_routes(app)


def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    init_db()
    print("\n" + "=" * 54)
    print("  Smart Task Management System")
    print("  Based on ASRS Architectural Design Document")
    print("=" * 54)
    print("  → http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop")
    print("=" * 54 + "\n")
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, port=5000)
