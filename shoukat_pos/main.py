#!/usr/bin/env python3
"""
Shoukat Sons Garments POS - Main Entry Point.

This is the application entry point that handles first-run initialization
and launches the main UI application.

Full first-run wizard implementation in Section 8.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    """
    Main entry point for the POS application.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # First-run wizard stub - full implementation in Section 8
    # This will check if this is the first run and guide through setup
    
    try:
        # Initialize database connection manager
        from database.connection import ConnectionManager
        
        cm = ConnectionManager()
        
        # Stub: In Section 8, this will check FIRST_RUN_FLAG_FILE
        # and run the first-run wizard if needed
        
        # Launch main UI application
        print("Shoukat Sons Garments POS - Starting...")
        print("Database initialized successfully.")
        
        from ui.app import POSApp
        
        app = POSApp()
        app.mainloop()
        
        return 0
        
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
