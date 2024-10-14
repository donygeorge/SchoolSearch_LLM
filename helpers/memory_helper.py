import json
import os
from config.config_app import CACHE_FOLDER
from helpers.base_helper import ensure_folder_exists


MEMORY_FILE = 'user_memories.json'
MEMORY_FILE_PATH = os.path.join(CACHE_FOLDER, MEMORY_FILE)

def _ensure_memory_file_exists():
    ensure_folder_exists(CACHE_FOLDER)

def get_memories():
    _ensure_memory_file_exists()
    try:
        if os.path.exists(MEMORY_FILE_PATH):
            with open(MEMORY_FILE_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading memories: {e}")
    return []

def get_formatted_memories():
    memories = get_memories()
    return "\n".join([f"- {memory}" for i, memory in enumerate(memories)])

def save_memories(memories):
    _ensure_memory_file_exists()
    print("Saving memories: " + str(memories))
    with open(MEMORY_FILE_PATH, 'w') as f:
        json.dump(memories, f)