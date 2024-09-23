from dotenv import load_dotenv
from bs4 import BeautifulSoup
from llama_index.core import Document
from llama_index.readers.web import SimpleWebPageReader
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



# Function to extract text using pdfplumber
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

def load_pdfs_from_directory(dir):
    pdf_docs = []
    for filename in os.listdir(dir):
        if filename.endswith(".pdf"):
            file_path = os.path.join(dir, filename)
            extracted_text = extract_text_from_pdf(file_path)
            doc = Document(text=extracted_text)
            doc.metadata = {'source': 'pdf'}
            pdf_docs.append(doc)
            print("Loaded pdf data from: " + file_path)
    return pdf_docs

def load_document_from_url(loader, url):
    print(f"Loading web data from:" + url)
    try:
        return loader.load_data(urls=[url])
    except Exception as e:
        print(f"Error loading {url}: {str(e)}")
        return []

def load_school_links(school_links):
    web_docs = []
    loader = SimpleWebPageReader()
    
    for school in school_links:
        for key, data in school.items():
            print("key: " + key)
            if key not in ['name', 'additional_links']:
                doc = load_document_from_url(loader, data)
                web_docs += doc
            if key == 'additional_links':
                for link in data:
                    doc = load_document_from_url(loader, link)
                    web_docs += doc
    return web_docs

