from dotenv import load_dotenv
from bs4 import BeautifulSoup
from llama_index.core import Document
from llama_index.readers.web import SimpleWebPageReader
from datetime import datetime, timedelta
from config_app import CACHE_FILE, CACHE_EXPIRY_DAYS
import json
import pdfplumber
import requests
import os
import re

# Load environment variables
load_dotenv()

def parse_website(website):
    print("Parsing:" + website)
    response = requests.get(website)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = [p.text for p in soup.find_all("p")]
    full_text = "\n".join(text)
    return full_text

def clean_and_preprocess_website_text(html_content):
    # Parse HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()
    
    # Get text content
    text = soup.get_text(separator=' ')
    
    # Remove special characters and excessive whitespace
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    
    # Normalize text
    text = text.lower().strip()
    
    # Optionally, you can add more preprocessing steps like tokenization, lemmatization, etc.
    
    return text

def clean_and_preprocess_website(website_document):
    cleaned_text = clean_and_preprocess_website_text(website_document.text)
    return Document(text=cleaned_text, metadata=website_document.metadata)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {'websites': {}, 'pdfs': {}}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)
        
def is_cache_valid(timestamp):
    cache_date = datetime.fromisoformat(timestamp)
    return datetime.now() - cache_date < timedelta(days=CACHE_EXPIRY_DAYS)


# Function to extract text using pdfplumber
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

def load_pdfs_from_directory(dir):
    cache = load_cache()
    pdf_docs = []
    for filename in os.listdir(dir):
        if filename.endswith(".pdf"):
            file_path = os.path.join(dir, filename)
            if file_path in cache['pdfs'] and is_cache_valid(cache['pdfs'][file_path]['timestamp']):
                print(f"Using cached data for PDF: {file_path}")
                doc = Document(text=cache['pdfs'][file_path]['content'], 
                               metadata=cache['pdfs'][file_path]['metadata'])
                pdf_docs.append(doc)
            else:
                print(f"Loading new PDF: {file_path}")
                extracted_text = extract_text_from_pdf(file_path)
                doc = Document(text=extracted_text)
                doc.metadata = {'source': 'pdf'}
                cache['pdfs'][file_path] = {'content': doc.text, 
                                            'timestamp': datetime.now().isoformat(), 
                                            'metadata': doc.metadata}
                pdf_docs.append(doc)
                
    save_cache(cache)
    return pdf_docs

def load_document_from_url(loader, url):
    print(f"Loading web data from:" + url)
    try:
        docs = loader.load_data(urls=[url])
        if len(docs) == 0:
            print(f"No data found for {url}")
            return None
        elif len(docs) > 1:
            print(f"Loaded {len(docs)} documents from {url} -> i.e more than one document")
        return docs[0]
    except Exception as e:
        print(f"Error loading {url}: {str(e)}")
        return None


def get_school_links(school_links):
    links = []
    
    for school in school_links:
        for key, data in school.items():
            # print("key: " + key)
            if key not in ['name', 'additional_links']:
                links.append(data)
            if key == 'additional_links':
                for link in data:
                    links.append(link)
    return links

def load_school_links(school_links):
    web_docs = []
    loader = SimpleWebPageReader()
    cache = load_cache()
    
    links = get_school_links(school_links)
    
    for link in links:
        if link in cache['websites'] and is_cache_valid(cache['websites'][link]['timestamp']):
            print(f"Using cached data for website: {link}")
            doc = Document(text=cache['websites'][link]['content'], 
                           metadata=cache['websites'][link]['metadata'])
            web_docs.append(doc)
        else:
            print(f"Loading new website: {link}")
            doc = load_document_from_url(loader, link)
            # print("doc: " + str(doc))
            doc = clean_and_preprocess_website(doc)
            cache['websites'][link] = {
                'content': doc.text,
                'timestamp': datetime.now().isoformat(),
                'metadata': doc.metadata
            }
            web_docs.append(doc)
    
    save_cache(cache)
    return web_docs

