#!/usr/bin/env python3
"""
Simple script to run the Flask app from the backend directory
"""

import sys
import os

# Add the current directory to Python path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_app import app

if __name__ == '__main__':
    print("Starting Golf Card Game server...")
    print("Access the game at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")

    app.run(debug=True, host='0.0.0.0', port=5000)