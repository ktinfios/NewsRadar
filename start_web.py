#!/usr/bin/env python3
"""
NewsRadar Web Interface Startup Script
"""

import os
import sys
import webbrowser
from pathlib import Path

def main():
    print("Starting NewsRadar Web Interface...")
    
    # Change to the NewsRadar directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
        
    # Import and run the Flask app
    try:
        from web_app import app
        
        print("Web interface will be available at:")
        print("Local:http://localhost:5000")
        print("To stop the server, press Ctrl+C")
        
        # Try to open browser automatically
        try:
            webbrowser.open('http://localhost:5000')
        except:
            pass  # Browser opening is optional
        
        # Start the Flask application
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting web interface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
