#!/usr/bin/env python3
"""
Cleanup old pending registrations
This should be run periodically (e.g., via cron job) to clean up abandoned registrations
where users closed the tab or never completed payment.

Deletes pending registrations older than 24 hours (same as Stripe session expiry)
"""

from database import SessionLocal, PendingRegistration
from datetime import datetime, timezone, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_pending():
    """Delete pending registrations older than 24 hours"""
    db = SessionLocal()
    
    try:
        # Calculate cutoff time (24 hours ago)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Find old pending registrations
        old_pending = db.query(PendingRegistration).filter(
            PendingRegistration.created_at < cutoff
        ).all()
        
        if old_pending:
            logger.info(f"Found {len(old_pending)} pending registrations older than 24 hours")
            for pending in old_pending:
                logger.info(f"  Deleting: {pending.email} (created {pending.created_at})")
                db.delete(pending)
            
            db.commit()
            logger.info(f"✓ Deleted {len(old_pending)} old pending registrations")
        else:
            logger.info("No old pending registrations to clean up")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("=== Starting pending registrations cleanup ===")
    cleanup_old_pending()
    logger.info("=== Cleanup complete ===")
