import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

CACHE_FILE = '.data_cache.json'
SCRAPER_CACHE_FILE = '.scraper_cache.json'
CACHE_EXPIRY_DAYS = 14  # Cache expires after 14 days


def _load_cache(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return None

def _save_cache(cache, file):
    with open(file, 'w') as f:
        json.dump(cache, f)
        
def load_cache():
    cache = _load_cache(CACHE_FILE)
    if cache is None:
        cache = {'websites': {}, 'pdfs': {}}

    return cache

def save_cache(cache):
    _save_cache(cache, CACHE_FILE)
    
def load_scraper_cache():
    cache = _load_cache(SCRAPER_CACHE_FILE)
    if cache is None:
        cache = {}

    return cache

def save_scraper_cache(cache):
    # print(f"Saving scraper cache: {str(cache)}")
    _save_cache(cache, SCRAPER_CACHE_FILE)

        
def is_cache_valid(timestamp):
    cache_date = datetime.fromisoformat(timestamp)
    return datetime.now() - cache_date < timedelta(days=CACHE_EXPIRY_DAYS)