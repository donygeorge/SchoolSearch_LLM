from dotenv import load_dotenv

from langsmith import traceable
from langsmith import Client
from langsmith.wrappers import wrap_openai

from data_evaluation import school_data_without_context

# Load environment variables
load_dotenv()

client = Client()
dataset_name = "school_data_without_context"
dataset_description = "Generic school questions about the Bay Area without context"

# Check if the dataset already exists
existing_datasets = client.list_datasets()
dataset = next((ds for ds in existing_datasets if ds.name == dataset_name), None)


if dataset is None:
    # If dataset does not exist, create a new one
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description=dataset_description
    )


client.create_examples(
    inputs=[{"question": data["input"]} for data in school_data_without_context],
    outputs=[{"answer": data["output"]} for data in school_data_without_context],
    dataset_id=dataset.id,
)
