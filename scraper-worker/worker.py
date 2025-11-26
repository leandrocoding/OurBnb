from scrape import search_airbnb
from scrape_listing import get_listing_data
from typing import Dict, Any
import json
import time
from random import randint

from celery import Celery

app = Celery("airbnb_workers", broker= "redis://localhost:6379/0")

@app.task(name='scraper.search_job') 
def search_worker(args : Dict[str, Any]):
    
    location = args.get("location")
    guest_count = args.get("guests")
    checkin = args.get("checkin")
    checkout = args.get("checkout")
    max_pages = args.get("max_pages")
    # TODO add aditional search parameters
    if(not (location and guest_count and checkin and checkout)):
        print("Missing required data in search, args dump: ", json.dumps(args) )
        return "Failed"

    search_airbnb(location = location, guests =guest_count, checkin = checkin, checkout=checkout, max_pages = max_pages or 2)

    # location, guests, checkin, checkout
    print(f"Scraping search for {location}")
    time.sleep(randint(1,4)) # sleep 1-4 seconds after job completion to hopefully not trigger any rate limits. 
    # ... implementation ...
    return "Done"

@app.task(name='scraper.listing_job')
def listing_worker(room_id):
    print(f"Scraping listing {room_id}")
    get_listing_data(room_id)
    time.sleep(randint(1,4))
    
    return "Done"