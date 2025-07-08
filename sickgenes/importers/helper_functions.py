import json
import requests
from pathlib import Path
from urllib.parse import urlparse

def get_json_from_source(source_path):
    """
    Get JSON data from either a URL or file path.
    
    Args:
        source_path (str): Either a URL or file path to JSON data
        
    Returns:
        dict: Parsed JSON data
    """
    def is_url(path):
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    if is_url(source_path):
        # Handle URL
        response = requests.get(source_path)
        response.raise_for_status()
        return response.json()
    else:
        # Handle file path
        file_path = Path(source_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {source_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
        
def output_progress(processed_count, stdout):
    if stdout:
        if processed_count % 100 == 0:
            stdout.write(f"\rProcessed {processed_count} items", ending='')