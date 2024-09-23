import os
from langsmith import traceable
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage


from dotenv import load_dotenv
load_dotenv()

if os.getenv("USE_PRIVATE_LINKS"):
    from private_links import school_links
    print("Using private links")
else:
    from links import school_links# This file should have your list of URLs and info

from helper import load_pdfs_from_directory, load_school_links


def load_all_data():
    # Load PDFs
    pdf_docs = load_pdfs_from_directory('private_data')
    # Load URLs from private_link.py
    web_docs = load_school_links(school_links)
    # Combine all documents
    combined_docs = pdf_docs + web_docs
    return combined_docs

def create_index():
    docs = load_all_data()
    
    # Create a storage context without trying to load existing data
    storage_context = StorageContext.from_defaults()
    
    # Create the index with storage context
    index = VectorStoreIndex.from_documents(docs, storage_context=storage_context)
    
    # Save index to disk
    storage_context.persist(persist_dir="persisted_data")
    return index


# Load the index from disk
def load_index():
    # Load the storage context
    storage_context = StorageContext.from_defaults(persist_dir="persisted_data")
    
    # Load the index from the storage context
    index = load_index_from_storage(storage_context)
    
    return index


if __name__ == "__main__":
    # Create or load the index
    if not os.path.exists("persisted_data/docstore.json"):
        print("Creating new index...")
        index = create_index()
    else:
        print("Loading existing index...")
        index = load_index()

    # Create a query engine from the index
    query_engine = index.as_query_engine()
    
    # Test query
    query = "WHat are the key admission dates for Harker School?"
    response = query_engine.query(query)
    print(response)