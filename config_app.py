from dotenv import load_dotenv
import os

# Load the environment variables from the .env file
load_dotenv()

config_area = os.getenv("CONFIG_AREA_STRING")
# print("Config area: " + config_area)

CACHE_FILE = '.data_cache.json'
CACHE_EXPIRY_DAYS = 14  # Cache expires after 14 days
