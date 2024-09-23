from dotenv import load_dotenv
from bs4 import BeautifulSoup
from llama_index.core import Document
from llama_index.readers.web import SimpleWebPageReader
import pdfplumber
import requests
import os

# Load environment variables
load_dotenv()

def parse_website(website):
    print("Parsing:" + website)
    response = requests.get(website)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = [p.text for p in soup.find_all("p")]
    full_text = "\n".join(text)
    return full_text

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
            pdf_docs.append(Document(text=extracted_text))
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
                web_docs += load_document_from_url(loader, data)
            if key == 'additional_links':
                for link in data:
                    web_docs += load_document_from_url(loader, link)
    return web_docs

