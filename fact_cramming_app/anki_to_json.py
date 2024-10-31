import sqlite3
import json
import tempfile
import zipfile
import os
import base64
import re
from bs4 import BeautifulSoup
import shutil

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text().strip()

def find_images_in_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    return [img.get('src') for img in images if img.get('src')]

def convert_anki_to_json(apkg_path, output_path):
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Extracting to temporary directory: {temp_dir}")
    
    # Extract the apkg
    with zipfile.ZipFile(apkg_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Connect to the SQLite database
    conn = sqlite3.connect(os.path.join(temp_dir, 'collection.anki2'))
    cursor = conn.cursor()
    
    # Get media mapping
    media_mapping = {}
    media_db_path = os.path.join(temp_dir, 'media')
    if os.path.exists(media_db_path):
        with open(media_db_path, 'r', encoding='utf-8') as f:
            media_mapping = json.load(f)
            print(f"Found {len(media_mapping)} media files in mapping")
    
    cards = []
    
    # Get all notes
    cursor.execute("SELECT id, flds FROM notes")
    rows = cursor.fetchall()
    
    for idx, row in enumerate(rows):
        note_id, fields_str = row
        fields = fields_str.split('\x1f')
        
        if len(fields) >= 2:
            prompt_html = fields[0]
            answer_html = fields[1]
            
            card = {
                "id": str(note_id),
                "prompt": clean_html(prompt_html),
                "answer": clean_html(answer_html)
            }
            
            # Handle images in prompt
            prompt_images = find_images_in_html(prompt_html)
            if prompt_images:
                for img_src in prompt_images:
                    # Get the actual filename from media mapping
                    media_file = media_mapping.get(img_src, img_src)
                    media_path = os.path.join(temp_dir, media_file)
                    
                    if os.path.exists(media_path):
                        print(f"Found prompt image: {media_file}")
                        with open(media_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                            extension = os.path.splitext(media_file)[1].lower()
                            mime_type = {
                                '.jpg': 'image/jpeg',
                                '.jpeg': 'image/jpeg',
                                '.png': 'image/png',
                                '.gif': 'image/gif'
                            }.get(extension, 'image/jpeg')
                            card["promptImage"] = f"data:{mime_type};base64,{encoded_string}"
                            break  # Only use the first image for now
            
            # Handle images in answer
            answer_images = find_images_in_html(answer_html)
            if answer_images:
                for img_src in answer_images:
                    # Get the actual filename from media mapping
                    media_file = media_mapping.get(img_src, img_src)
                    media_path = os.path.join(temp_dir, media_file)
                    
                    if os.path.exists(media_path):
                        print(f"Found answer image: {media_file}")
                        with open(media_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                            extension = os.path.splitext(media_file)[1].lower()
                            mime_type = {
                                '.jpg': 'image/jpeg',
                                '.jpeg': 'image/jpeg',
                                '.png': 'image/png',
                                '.gif': 'image/gif'
                            }.get(extension, 'image/jpeg')
                            card["answerImage"] = f"data:{mime_type};base64,{encoded_string}"
                            break  # Only use the first image for now
            
            cards.append(card)
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(cards)} cards to {output_path}")
    
    # Clean up
    conn.close()
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python anki_to_json.py <input.apkg> <output.json>")
        sys.exit(1)
    
    convert_anki_to_json(sys.argv[1], sys.argv[2]) 