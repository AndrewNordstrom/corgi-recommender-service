#!/usr/bin/env python3
"""
Setup script for in-memory SQLite database
"""

import os
import logging

# Force in-memory SQLite mode
os.environ["USE_IN_MEMORY_DB"] = "true"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('setup')

def main():
    logger.info("Setting up in-memory database...")
    
    try:
        # Import DB modules
        from db.connection import get_db_connection
        from db.schema import init_db
        
        # Initialize the in-memory database
        with get_db_connection() as conn:
            init_db(conn)
        
        # Setup completed successfully
        logger.info("In-memory database setup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during database setup: {e}")
        return False

if __name__ == "__main__":
    main()