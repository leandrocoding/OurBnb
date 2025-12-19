import os
import logging
from celery import Celery
from typing import Optional

logger = logging.getLogger(__name__)

# Redis configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

scraper_queue = Celery('trigger_app', broker=REDIS_URL)


def trigger_search_for_user_destinations(user_id: int, page_count: int = 4) -> list[str]:
    """
    Trigger search jobs for all destinations associated with a user's groups.
    
    Args:
        user_id: User ID to trigger searches for
        page_count: Number of pages to scrape per destination (default 4)
        
    Returns:
        List of job ID strings
    """
    from db import get_cursor
    
    # Get all destination IDs for groups the user belongs to
    with get_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT d.id as destination_id
            FROM destinations d
            JOIN groups g ON g.id = d.group_id
            JOIN users u ON u.group_id = g.id
            WHERE u.id = %s
        """, (user_id,))
        destinations = cur.fetchall()
    
    job_ids = []
    for dest in destinations:
        job_id = trigger_search_job(
            user_id=user_id,
            destination_id=dest['destination_id'],
            page_start=1,
            page_end=page_count,
            high_prio=True
        )
        job_ids.append(job_id)
    
    logger.info(f"Triggered {len(job_ids)} search jobs for user {user_id}")
    return job_ids


def trigger_search_job(
    user_id: int,
    destination_id: int,
    page_start: int = 1,
    page_end: int = 2,
    high_prio: bool = True
) -> str:
    """
    Trigger a search job for the scraper worker.
    
    Args:
        user_id: User ID to get filters from
        destination_id: Destination ID to get location and group info from
        page_start: Starting page number (default 1)
        page_end: Maximum ending page number (default 2, actual may be less)
        high_prio: Whether to use high priority queue
        
    Returns:
        Job ID string
    """
    search_task_name = 'scraper.search_job'
    
    job_args = {
        "user_id": user_id,
        "destination_id": destination_id,
        "page_start": page_start,
        "page_end": page_end,
    }
    
    logger.debug(f"Sending {search_task_name} with args: {job_args}")
    
    result = scraper_queue.send_task(
        search_task_name,
        args=[job_args],
        queue="high_priority" if high_prio else "default"
    )
    
    logger.debug(f"Job dispatched. ID: {result.id}")
    return result.id


def trigger_listing_inquiry(listing_id: str, high_prio: bool = False) -> str:
    """
    Trigger a listing detail scrape job.
    
    Args:
        listing_id: Airbnb listing ID
        high_prio: Whether to use high priority queue
        
    Returns:
        Job ID string
    """
    listing_task_name = 'scraper.listing_job'
    
    logger.debug(f"Sending {listing_task_name} for listing {listing_id}")
    
    result = scraper_queue.send_task(
        listing_task_name,
        args=[listing_id],
        queue="high_priority" if high_prio else "default"
    )
    
    logger.debug(f"Job dispatched. ID: {result.id}")
    return result.id


if __name__ == "__main__":
    # Test triggering a job
    trigger_search_job(user_id=1, destination_id=1, page_start=1, page_end=2)
