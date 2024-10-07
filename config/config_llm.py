import os
from dotenv import load_dotenv
load_dotenv()

configurations = {
    "mistral_7B": {
        "endpoint_url": os.getenv("MISTRAL_7B_ENDPOINT"),
        "api_key": os.getenv("RUNPOD_API_KEY"),
        "model": "mistralai/Mistral-7B-v0.1"
    },
    "openai_gpt-4": {
        "endpoint_url": os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4o-mini"
    }
}

# Choose configuration
config_key = "openai_gpt-4"
#config_key = "mistral_7B"

# Get selected configuration
config = configurations[config_key]

# https://platform.openai.com/docs/models/gpt-4o
model_kwargs = {
   "model": config["model"],
   "temperature": 0.3,
   "max_tokens": 2000
}