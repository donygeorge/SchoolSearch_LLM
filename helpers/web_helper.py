from dotenv import load_dotenv
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from llama_index.core import Document
from datetime import datetime
from helpers.cache_helper import load_cache, save_cache, is_cache_valid
from helpers.cache_helper import load_scraper_cache, save_scraper_cache

import requests
import re
import time
import random

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

def create_session_with_retries():
    session = requests.Session()
    retries = Retry(total=3,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

class CustomWebPageReader:
    def __init__(self):
        self.session = create_session_with_retries()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        }

    def load_data(self, urls):
        documents = []
        for url in urls:
            try:
                response = self.session.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                html = response.text
                
                # Parse the HTML content
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract text content
                text = soup.get_text(separator='\n', strip=True)
                
                documents.append(Document(text=text, extra_info={"url": url}))
            except requests.RequestException as e:
                print(f"Error fetching {url}: {str(e)}")
        return documents

def load_document_from_url(loader, url, max_retries=2, retry_count=0):
    print(f"Loading web data from: {url} (Attempt {retry_count + 1})")
    
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
        
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403:
            if retry_count < max_retries:
                print(f"Received 403 Forbidden. Waiting and retrying... (Attempt {retry_count + 2})")
                time.sleep(random.uniform(5, 10))  # Wait for 5-10 seconds
                return load_document_from_url(loader, url, max_retries, retry_count + 1)  # Retry
            else:
                print(f"Max retries reached for {url}. Giving up.")
        
        return None


def load_link(link, loader, cache, school_name=None):
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
        
        if doc.metadata is None:
            doc.metadata = {}
        
        # Update metadata
        doc.metadata.update({
            "source": link,
            "type": "website"
        })

        if school_name:
            doc.metadata['school'] = school_name.lower()

        cache['websites'][link] = {
            'content': doc.text,
            'timestamp': datetime.now().isoformat(),
            'metadata': doc.metadata
        }
    
    return doc, cache
        

def load_school_links(links, school_name = None):
    web_docs = []
    loader = CustomWebPageReader()
    cache = load_cache()
        
    for link in links:
        doc, cache = load_link(link, loader, cache, school_name)
        web_docs.append(doc)
    
    save_cache(cache)
    return web_docs


def load_non_root_links(school_links):
    docs = []
    for school in school_links:
        school_name = school['name']
        links = []
        for key, data in school.items():
            # print("key: " + key)
            if key not in ['name', 'additional_links', 'root']:
                links.append(data)
            elif key == 'additional_links':
                for link in data:
                    links.append(link)
        returned_docs = load_school_links(links, school_name)
        docs.extend(returned_docs)
    return docs


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
    
    for school in school_links:
        school_name = school['name']
        if 'root' in school:
            root_link = school['root']
            links = crawl_links(root_link)
            print(f"For root link: {root_link}, found {len(links)}")
            school_docs = load_school_links(links, school_name)
            crawled_docs.extend(school_docs)
        else:
            print(f"No root link found for {school_name}")

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
