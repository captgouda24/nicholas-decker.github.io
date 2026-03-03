"""
Build semantic search index with OCR text extraction.
Runs OCR on all images and combines with tweet text for better search.
"""

import json
import sys
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Paths
BASE_DIR = Path("C:/Users/Owner/Documents/transmissions11.github.io")
PAPERS_JSON = BASE_DIR / "paper-threads" / "papers-indexed.json"
MEDIA_DIR = BASE_DIR / "paper-threads" / "media"
OUTPUT_DIR = BASE_DIR / "paper-threads"
OCR_CACHE = OUTPUT_DIR / "ocr-cache.json"

def load_papers():
    """Load the indexed papers JSON."""
    print("Loading papers...", flush=True)
    with open(PAPERS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_ocr():
    """Initialize EasyOCR reader."""
    print("Loading OCR model (this may download ~100MB on first run)...", flush=True)
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    print("OCR model ready", flush=True)
    return reader

def load_ocr_cache():
    """Load cached OCR results."""
    if OCR_CACHE.exists():
        with open(OCR_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_ocr_cache(cache):
    """Save OCR cache."""
    with open(OCR_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f)

def run_ocr_on_images(reader, papers):
    """Run OCR on all images, with caching."""
    cache = load_ocr_cache()

    # Collect all unique image files
    all_images = set()
    for paper in papers['papers']:
        for tweet in paper.get('thread', []):
            for media in tweet.get('media', []):
                all_images.add(media)

    print(f"Found {len(all_images)} unique images", flush=True)

    # Process images not in cache
    new_count = 0
    cached_count = 0
    error_count = 0

    for i, img_name in enumerate(sorted(all_images)):
        if img_name in cache:
            cached_count += 1
            continue

        img_path = MEDIA_DIR / img_name
        if not img_path.exists():
            cache[img_name] = ""
            error_count += 1
            continue

        try:
            result = reader.readtext(str(img_path), detail=0)
            text = ' '.join(result)
            cache[img_name] = text
            new_count += 1

            # Progress update every 50 images
            if new_count % 50 == 0:
                print(f"  OCR progress: {new_count} new, {cached_count} cached, {error_count} errors", flush=True)
                save_ocr_cache(cache)  # Save periodically

        except Exception as e:
            cache[img_name] = ""
            error_count += 1

    # Final save
    save_ocr_cache(cache)
    print(f"OCR complete: {new_count} new, {cached_count} cached, {error_count} errors", flush=True)

    return cache

def setup_embedder():
    """Initialize sentence-transformers model."""
    print("Loading embedding model...", flush=True)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Embedding model ready", flush=True)
    return model

def build_paper_texts(papers, ocr_cache):
    """Build text for each paper from tweet content + OCR."""
    print("Building paper texts with OCR...", flush=True)
    paper_texts = []

    for paper in papers['papers']:
        # Collect all tweet text
        tweet_texts = []
        ocr_texts = []

        for tweet in paper.get('thread', []):
            text = tweet.get('text', '')
            # Remove t.co links
            text = ' '.join(w for w in text.split() if not w.startswith('https://t.co/'))
            tweet_texts.append(text)

            # Get OCR text for images
            for media in tweet.get('media', []):
                ocr_text = ocr_cache.get(media, '')
                if ocr_text:
                    ocr_texts.append(ocr_text)

        # Combine all text
        combined = ' '.join(tweet_texts + ocr_texts)
        combined = ' '.join(combined.split())  # normalize whitespace

        paper_texts.append({
            'id': paper['id'],
            'authors': paper.get('authors', ''),
            'title': paper.get('title', ''),
            'year': paper.get('year'),
            'text': combined,
            'threadLength': paper.get('threadLength', 0),
        })

    print(f"Built {len(paper_texts)} paper texts", flush=True)
    return paper_texts

def generate_embeddings(embedder, paper_texts):
    """Generate embeddings for all papers."""
    print(f"Generating embeddings for {len(paper_texts)} papers...", flush=True)

    texts = [p['text'] for p in paper_texts]

    # Batch encode for efficiency
    embeddings = embedder.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    print(f"Embeddings shape: {embeddings.shape}", flush=True)
    return embeddings

def save_search_index(paper_texts, embeddings):
    """Save search index as compact JSON."""
    output_file = OUTPUT_DIR / "search-index.json"

    # Convert embeddings to list and round to reduce file size
    embeddings_list = [[round(float(x), 4) for x in emb] for emb in embeddings]

    index = {
        'version': 2,  # Version 2 includes OCR
        'embedding_dim': int(embeddings.shape[1]),
        'papers': [
            {
                'id': p['id'],
                'authors': p['authors'],
                'title': p['title'],
                'year': p['year'],
                'threadLength': p['threadLength'],
            }
            for p in paper_texts
        ],
        'embeddings': embeddings_list,
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(index, f)

    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"Saved search index: {output_file} ({size_mb:.2f} MB)", flush=True)

def main():
    print("=" * 60, flush=True)
    print("Building semantic search index WITH OCR", flush=True)
    print("=" * 60, flush=True)

    # Load papers
    papers = load_papers()
    print(f"Loaded {len(papers['papers'])} papers", flush=True)

    # Run OCR
    reader = setup_ocr()
    ocr_cache = run_ocr_on_images(reader, papers)

    # Build combined texts
    paper_texts = build_paper_texts(papers, ocr_cache)

    # Generate embeddings
    embedder = setup_embedder()
    embeddings = generate_embeddings(embedder, paper_texts)

    # Save search index
    save_search_index(paper_texts, embeddings)

    print("=" * 60, flush=True)
    print("Done! Search index with OCR ready.", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
