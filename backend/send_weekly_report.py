#!/usr/bin/env python3
"""
Run weekly signup report once (for cron job)
This sends the report immediately without scheduling loop.
"""

import os
import sys
from dotenv import load_dotenv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import and send report
from signup_logger import send_weekly_report
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Running weekly signup report (cron job)")
    success = send_weekly_report()
    if success:
        logger.info("Report sent successfully")
        sys.exit(0)
    else:
        logger.error("Report failed to send")
        sys.exit(1)
