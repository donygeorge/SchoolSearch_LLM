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

def load_pdf_from_file(cache, file_name, dir_path, school_name):
    if file_name.endswith(".pdf"):
        file_path = os.path.join(dir_path, file_name)
        if file_path in cache['pdfs'] and is_cache_valid(cache['pdfs'][file_path]['timestamp']):
            print(f"Using cached data for PDF: {file_path}")
            doc = Document(text=cache['pdfs'][file_path]['content'], 
                            metadata=cache['pdfs'][file_path]['metadata'])
            return doc
        else:
            print(f"Loading new PDF: {file_path}")
            extracted_text = extract_text_from_pdf(file_path)
            doc = Document(text=extracted_text)
            if school_name:
                doc.metadata = {"source": file_name, 'type': 'pdf', 'school': school_name.lower()}
            else:
                doc.metadata = {"source": file_name, 'type': 'pdf'}
            cache['pdfs'][file_path] = {'content': doc.text, 
                                        'timestamp': datetime.now().isoformat(), 
                                        'metadata': doc.metadata}
            return doc
    return None

def load_pdfs_from_directory(dir):
    cache = load_cache()
    pdf_docs = []
    
    for item in os.listdir(dir):
        item_path = os.path.join(dir, item)
        if os.path.isdir(item_path):
            school_name = item
            for sub_item in os.listdir(item_path):
                sub_item_doc = load_pdf_from_file(cache, sub_item, item_path, school_name)
                if sub_item_doc:
                    pdf_docs.append(sub_item_doc)
        else:
            item_doc = load_pdf_from_file(cache, item, dir, None)
            if item_doc:
                pdf_docs.append(item_doc)
                
    save_cache(cache)
    return pdf_docs
