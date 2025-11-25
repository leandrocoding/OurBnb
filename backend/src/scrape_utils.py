from celery import Celery
from typing import Dict, List
import json 
scraper_queue = Celery('trigger_app', broker='redis://localhost:6379/0')


# TODO find a clean way to handle the search args, specifically create a specific schema that both ends use. JSON would probaly be the correct format to transfer. 
def trigger_search(args : Dict[str, any], high_prio = True):
    search_task_name = 'scraper.search_job'
    
    print(f"Sending {search_task_name}...")
    
    scraper_queue.send_task(
        search_task_name,
        args=[args],
        queue="high_priority" if high_prio else "default"
    )

def triger_listing_inquery(listing_id : int, high_prio : bool = False):
   
    listing_task_name = 'scraper.listing_job'
    
    print(f"Sending {listing_task_name}...")
    
    result = scraper_queue.send_task(
        listing_task_name,
        args=["1289024964833416671"],
        queue="high_priority" if high_prio else "default"
    )
    print(f"Job dispatched. ID: {result.id}")

   

if __name__ == "__main__":
    dispatch_jobs()