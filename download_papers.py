import csv
import requests
import os
import time
import re
from pathlib import Path

def clean_filename(authors, year, title):
    """Create clean filename from paper metadata"""
    # Get first author's last name
    first_author = authors.split(',')[0].strip()
    # Handle "Last, First" format
    if ',' in first_author:
        last_name = first_author.split(',')[0].strip()
    else:
        # Handle "First Last" format
        last_name = first_author.split()[-1]
    
    # Clean title - get first 3-4 words
    title_words = re.sub(r'[^\w\s]', '', title).split()[:4]
    title_part = '_'.join(title_words)
    
    # Create filename: LastName_Year_Title.pdf
    filename = f"{last_name}_{year}_{title_part}.pdf"
    # Remove any remaining problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename

def download_pdf(url, filename, save_dir='pdfs'):
    """Download PDF from URL"""
    Path(save_dir).mkdir(exist_ok=True)
    filepath = os.path.join(save_dir, filename)
    
    # Skip if already exists
    if os.path.exists(filepath):
        print(f"⊙ Already exists: {filename}")
        return True
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"↓ Downloading: {filename}")
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        
        if response.status_code == 200:
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            is_pdf = 'pdf' in content_type or response.content[:4] == b'%PDF'
            
            if is_pdf:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"✓ Success: {filename}")
                return True
            else:
                print(f"✗ Not a PDF: {filename} (Content-Type: {content_type})")
                return False
        else:
            print(f"✗ HTTP {response.status_code}: {filename}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"✗ Timeout: {filename}")
        return False
    except Exception as e:
        print(f"✗ Error: {filename} - {str(e)[:50]}")
        return False

def main():
    # Read CSV
    print("Reading classic_papers.csv...\n")
    papers = []
    
    with open('classic_papers.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        papers = list(reader)
    
    print(f"Found {len(papers)} papers to download\n")
    print("="*60)
    
    successful = []
    failed = []
    
    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}]")
        
        # Generate filename
        filename = clean_filename(
            paper['authors'],
            paper['year'],
            paper['title']
        )
        
        # Download
        success = download_pdf(paper['url'], filename)
        
        if success:
            successful.append(filename)
        else:
            failed.append({
                'filename': filename,
                'url': paper['url'],
                'authors': paper['authors'],
                'title': paper['title']
            })
        
        # Be respectful to servers
        time.sleep(2)
    
    # Summary
    print("\n" + "="*60)
    print(f"\n✓ Successfully downloaded: {len(successful)} PDFs")
    print(f"✗ Failed: {len(failed)} PDFs")
    
    if failed:
        print("\n--- Failed downloads ---")
        for f in failed:
            print(f"\n{f['authors']}: {f['title']}")
            print(f"  URL: {f['url']}")
            print(f"  Filename: {f['filename']}")
    
    # Save failed list for retry
    if failed:
        with open('failed_downloads.txt', 'w', encoding='utf-8') as f:
            for item in failed:
                f.write(f"{item['url']}\t{item['filename']}\n")
        print(f"\n✓ Failed URLs saved to failed_downloads.txt")
    
    print(f"\n✓ PDFs saved to ./pdfs/")

if __name__ == "__main__":
    main()