import os
import json
from langsmith import traceable
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine, TransformQueryEngine
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

if os.getenv("USE_PRIVATE_LINKS"):
    from private_links import school_links
    print("Using private links")
else:
    from links import school_links# This file should have your list of URLs and info

from helpers.web_helper import load_non_root_links, load_crawled_links
from helpers.pdf_helper import load_pdfs_from_directory

def get_schools_with_data():
    list =  [school["name"] for school in school_links]
    return "\n".join(f"- {school}" for school in list)
        
def load_all_data():
    # Load PDFs
    pdf_docs = load_pdfs_from_directory('private_data')
    
    # Load URLs from private_link.py
    web_docs = load_non_root_links(school_links)

    # Load URLs from crawling root links
    crawled_docs = load_crawled_links(school_links)

    # Combine all documents
    combined_docs = pdf_docs + web_docs + crawled_docs
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


def get_query_engine():
    if not os.path.exists("persisted_data/docstore.json"):
        print("Creating new index...")
        index = create_index()
    else:
        print("Loading existing index...")
        index = load_index()

    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=10,
    )
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        node_postprocessors=[],
        response_mode="compact"  # This will include source nodes in the response
    )
    return query_engine

def get_sources(source_nodes, max_sources=3, relevance_threshold=0.8):
    sources = []
    for node in source_nodes:
        source = {
            "content": node.node.get_content(),
            "metadata": node.node.metadata,
            "score": node.score
        }
        sources.append(source)
    
    # Sort sources by relevance score in descending order
    sorted_sources = sorted(sources, key=lambda x: x['score'], reverse=True)
    
    # Filter sources above the relevance threshold
    relevant_sources = [s for s in sorted_sources if s['score'] >= relevance_threshold]
    
    # Take the top source or up to 3 highly relevant sources
    filtered_sources = relevant_sources[:max_sources] if len(relevant_sources) > 1 else sorted_sources[:1]
    return filtered_sources

    
    

def format_response_with_sources(answer, sources):
    formatted_response = f"Answer: {answer}\n\nSources:\n"
        
    for i, source in enumerate(sources, 1):
        # print(f'{i}. Source: {str(source)}')
        
        formatted_response += f"\n{i}. Content: {source['content'][:100]}..."  # Truncate for brevity
        
        # Include available metadata
        if 'source' in source['metadata']:
            formatted_response += f"\n   Source: {source['metadata']['source']}"
        if 'school' in source['metadata']:
            formatted_response += f"\n   School: {source['metadata']['school']}"
        if 'type' in source['metadata']:
            formatted_response += f"\n   Type: {source['metadata']['type']}"
        
        formatted_response += f"\n   Relevance Score: {source['score']:.2f}\n"
    
    return formatted_response

if __name__ == "__main__":
    query_engine = get_query_engine()
    
    # Test query
    queries = [
               "What are the fees for the Harker School?",
            #    "What are the key admissions requirements for Harker School?",
            #    "Who is the admission  in charge for the Harker School?",
            #    "What is the average class size for Harker School?", 
            #    "What are the key admission dates for Harker School?",
            #    "How large is the class room for Harker School?",
            #    "What is the address of the kindergarden for Harker School?",
            #    "What are the fees for the Keys School?",
            #    "What is the average class size for the Keys School?",
            #    "What is the address of the kindergarden for the Keys School?",
            #    "What is the address of the kindergarden for Helios School?"
            ];
    for query in queries:
        response = query_engine.query(query)
        
        # The main response text
        answer = response.response
        
        # Get the source references
        sources = get_sources(response.source_nodes)
        
        print("Query: " + query)
        print("Response: " + format_response_with_sources(answer, sources))
        print("")
