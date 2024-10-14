import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from config.config_app import CACHE_FOLDER
from helpers.base_helper import ensure_folder_exists

load_dotenv()

CACHE_FILE = 'data_cache.json'
CACHE_FILE_PATH = os.path.join(CACHE_FOLDER, CACHE_FILE)
SCRAPER_CACHE_FILE = 'scraper_cache.json'
SCRAPER_CACHE_FILE_PATH = os.path.join(CACHE_FOLDER, SCRAPER_CACHE_FILE)
CACHE_EXPIRY_DAYS = 30  # Cache expires after 30 days


def _ensure_cache_folder_exists():
    ensure_folder_exists(CACHE_FOLDER)

def _load_cache(file):
    _ensure_cache_folder_exists()
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return None

def _save_cache(cache, file):
    _ensure_cache_folder_exists()
    with open(file, 'w') as f:
        json.dump(cache, f)
        
def load_cache():
    cache = _load_cache(CACHE_FILE_PATH)
    if cache is None:
        cache = {'websites': {}, 'pdfs': {}}

    return cache

def save_cache(cache):
    _save_cache(cache, CACHE_FILE_PATH)
    
def load_scraper_cache():
    cache = _load_cache(SCRAPER_CACHE_FILE_PATH)
    if cache is None:
        cache = {}

    return cache

def save_scraper_cache(cache):
    # print(f"Saving scraper cache: {str(cache)}")
    _save_cache(cache, SCRAPER_CACHE_FILE_PATH)

        
def is_cache_valid(timestamp):
    cache_date = datetime.fromisoformat(timestamp)
    return datetime.now() - cache_date < timedelta(days=CACHE_EXPIRY_DAYS)