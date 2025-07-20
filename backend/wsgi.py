#!/usr/bin/env python3
"""
WSGI entry point for Gunicorn
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Starting Flask app...")
    from web_app import app
    print("✅ Flask app imported successfully")
except Exception as e:
    print(f"❌ Error importing Flask app: {e}")
    import traceback
    traceback.print_exc()
    raise

if __name__ == "__main__":
    app.run()