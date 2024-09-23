from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests

# Load environment variables
load_dotenv()

def parse_website(website):
    print("Parsing:" + website)
    response = requests.get(website)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = [p.text for p in soup.find_all("p")]
    full_text = "\n".join(text)
    return full_text
