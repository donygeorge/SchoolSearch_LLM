from dotenv import load_dotenv
import os

# Load the environment variables from the .env file
load_dotenv()

config_area = os.getenv("CONFIG_AREA_STRING")
# print("Config area: " + config_area)