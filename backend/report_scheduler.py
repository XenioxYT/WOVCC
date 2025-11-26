"""
Weekly Signup Report Scheduler
Automatically sends weekly signup reports every Sunday at 6:00 PM
"""

from dotenv import load_dotenv

# Load environment variables FIRST before any other imports
load_dotenv()

import schedule
import time
import logging
import argparse
from datetime import datetime
from signup_logger import send_weekly_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_report_job():
    """Job to send weekly report"""
    logger.info("=" * 60)
    logger.info("Running weekly signup report job...")
    logger.info("=" * 60)
    
    try:
        success = send_weekly_report()
        if success:
            logger.info("✓ Weekly report sent successfully!")
        else:
            logger.warning("⚠ Weekly report job completed but no report was sent (possibly no new signups)")
    except Exception as e:
        logger.error(f"✗ Failed to send weekly report: {e}", exc_info=True)


def main():
    """Main scheduler loop"""
    parser = argparse.ArgumentParser(description="Weekly Signup Report Scheduler")
    parser.add_argument("--now", action="store_true", help="Run the report immediately and exit")
    args = parser.parse_args()
    
    if args.now:
        logger.info("Running report immediately due to --now flag")
        send_report_job()
        return
    
    logger.info("=" * 60)
    logger.info("📅 Weekly Signup Report Scheduler Starting")
    logger.info("=" * 60)
    logger.info("Schedule: Every Sunday at 18:00 (6:00 PM)")
    logger.info("Report will include all signups from the past 7 days")
    logger.info("")
    
    # Schedule the job for every Sunday at 6:00 PM
    schedule.every().sunday.at("18:00").do(send_report_job)
    
    logger.info(f"Next scheduled run: {schedule.next_run()}")
    logger.info("Press Ctrl+C to stop the scheduler")
    logger.info("=" * 60)
    
    # Run forever
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("Scheduler stopped by user")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
