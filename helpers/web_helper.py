from dotenv import load_dotenv
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from llama_index.core import Document
from llama_index.readers.web import SimpleWebPageReader
from datetime import datetime
from helpers.cache_helper import load_cache, save_cache, is_cache_valid
from helpers.cache_helper import load_scraper_cache, save_scraper_cache

import requests
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
            if key not in ['name', 'additional_links', 'root']:
                links.append(data)
            elif key == 'additional_links':
                for link in data:
                    links.append(link)
    return links

def get_school_root_links(school_links):
    links = []
    
    for school in school_links:
        for key, data in school.items():
            # print("key: " + key)
            if key == 'root':
                links.append(data)

    return links


def load_link(link, loader, cache):
    doc = None
    if link in cache['websites'] and is_cache_valid(cache['websites'][link]['timestamp']):
        print(f"Using cached data for website: {link}")
        doc = Document(text=cache['websites'][link]['content'], 
                        metadata=cache['websites'][link]['metadata'])
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
    
    return doc, cache
        

def load_school_links(links):
    web_docs = []
    loader = SimpleWebPageReader()
    cache = load_cache()
        
    for link in links:
        doc, cache = load_link(link, loader, cache)
        web_docs.append(doc)
    
    save_cache(cache)
    return web_docs

def crawl_links(root_link, max_pages = 100):
    links = []
    
    root_domain = urlparse(root_link).netloc
    cache = load_scraper_cache()
    cache_key = f"{root_domain}_{max_pages}"
    
    if cache_key in cache and is_cache_valid(cache[cache_key]['timestamp']):
        print(f"Using cached data for root link: {root_link}: found {len(cache[cache_key]['links'])} links")
        return cache[cache_key]['links']
    
    to_visit = [root_link]
    visited = set()
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.google.com'
    }
    
    while len(to_visit) > 0 and len(links) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        
        links.append(url)

        try:
            print(f"Scraping {url}")
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find new links
                for link in soup.find_all('a', href=True):
                    new_url = urljoin(url, link['href'])
                    # print("new_url: " + new_url)
                    if is_relevant_to_root_url(new_url, root_domain) and new_url not in visited:
                        to_visit.append(new_url)
            else:
                print(f"Skipping {url} because it returned status code {response.status_code}")

            visited.add(url)

        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
    
    # Update cache with new results
    cache[cache_key] = {
        'links': links,
        'timestamp': datetime.now().isoformat()
    }
    save_scraper_cache(cache)

    return links


def load_crawled_links(school_links):
    crawled_docs = []
    
    # root links
    root_links = get_school_root_links(school_links)
    for link in root_links:
        links = crawl_links(link)
        print(f"For root link: {link}, found {len(links)}")
        
        school_docs = load_school_links(links)
        crawled_docs.extend(school_docs)

    return crawled_docs


def is_relevant_to_root_url(url, root_domain):
    """Check if the URL is valid and belongs to the same domain."""
    parsed = urlparse(url)
    # Check if the URL belongs to the same domain
    if not (bool(parsed.netloc) and parsed.netloc.endswith(root_domain)):
        return False
    
    # Ignore specific file types
    ignored_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    if any(url.lower().endswith(ext) for ext in ignored_extensions):
        return False
    
    # Check if the page is relevant
    relevant_patterns = [
        r'/about', r'/admission', r'/academics', r'/programs',
        r'/faculty', r'/staff', r'/students', r'/parents',
        r'/calendar', r'/events', r'/news', r'/contact',
        r'/apply', r'/tuition', r'/financial-aid', r'/scholarships',
        r'/curriculum', r'/extracurricular', r'/athletics',
        r'/facilities', r'/campus', r'/transportation', r'/lower'
    ]
    
    # If the URL path is empty or just '/', consider it relevant (likely the homepage)
    if parsed.path in ('', '/'):
        return True
    
    return any(re.search(pattern, parsed.path, re.IGNORECASE) for pattern in relevant_patterns)
