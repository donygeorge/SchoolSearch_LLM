from dotenv import load_dotenv
from datetime import datetime
from llama_index.core import Document
from helpers.cache_helper import load_cache, save_cache, is_cache_valid
import pdfplumber
import os

load_dotenv()

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
