"""
Build semantic search index for paper threads.
1. OCR all images to extract text
2. Combine tweet text + OCR text for each paper
3. Generate embeddings using sentence-transformers
4. Save compact JSON for client-side search
"""

import json
import os
from pathlib import Path
import numpy as np

# Paths
BASE_DIR = Path("C:/Users/Owner/Documents/transmissions11.github.io")
PAPERS_JSON = BASE_DIR / "paper-threads" / "papers-indexed.json"
MEDIA_DIR = BASE_DIR / "paper-threads" / "media"
OUTPUT_DIR = BASE_DIR / "paper-threads"
OCR_CACHE = OUTPUT_DIR / "ocr-cache.json"

def load_papers():
    """Load the indexed papers JSON."""
    print("Loading papers...")
    with open(PAPERS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_ocr():
    """Initialize EasyOCR reader."""
    print("Initializing OCR (this may download models on first run)...")
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    print("OCR ready")
    return reader

def ocr_image(reader, image_path):
    """Extract text from an image using EasyOCR."""
    try:
        results = reader.readtext(str(image_path))
        # results is list of (bbox, text, confidence)
        texts = [r[1] for r in results if r[2] > 0.3]  # confidence > 30%
        return ' '.join(texts)
    except Exception as e:
        print(f"  OCR error for {image_path.name}: {e}")
        return ""

def ocr_all_images(reader, papers):
    """OCR all images, using cache to avoid re-processing."""
    # Load cache if exists
    cache = {}
    if OCR_CACHE.exists():
        print("Loading OCR cache...")
        with open(OCR_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f"  {len(cache)} images already processed")

    # Collect all unique image files
    all_images = set()
    for paper in papers['papers']:
        for media_file in paper.get('mediaFiles', []):
            all_images.add(media_file)

    print(f"Total images to process: {len(all_images)}")

    # OCR images not in cache
    new_count = 0
    for i, img_name in enumerate(sorted(all_images)):
        if img_name in cache:
            continue

        img_path = MEDIA_DIR / img_name
        if not img_path.exists():
            cache[img_name] = ""
            continue

        if (i + 1) % 50 == 0 or new_count < 5:
            print(f"  OCR [{i+1}/{len(all_images)}]: {img_name}")

        text = ocr_image(reader, img_path)
        cache[img_name] = text
        new_count += 1

        # Save cache periodically
        if new_count % 100 == 0:
            with open(OCR_CACHE, 'w', encoding='utf-8') as f:
                json.dump(cache, f)
            print(f"  Cache saved ({new_count} new)")

    # Final cache save
    with open(OCR_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f)
    print(f"OCR complete. {new_count} new images processed.")

    return cache

def setup_embedder():
    """Initialize sentence-transformers model."""
    print("Loading embedding model...")
    from sentence_transformers import SentenceTransformer
    # all-MiniLM-L6-v2 is fast and produces 384-dim embeddings
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Embedding model ready")
    return model

def build_paper_texts(papers, ocr_cache):
    """Combine tweet text and OCR text for each paper."""
    print("Building paper texts...")
    paper_texts = []

    for paper in papers['papers']:
        # Collect all tweet text
        tweet_texts = []
        for tweet in paper.get('thread', []):
            text = tweet.get('text', '')
            # Remove t.co links
            text = ' '.join(w for w in text.split() if not w.startswith('https://t.co/'))
            tweet_texts.append(text)

        # Collect OCR text from images
        ocr_texts = []
        for media_file in paper.get('mediaFiles', []):
            if media_file in ocr_cache and ocr_cache[media_file]:
                ocr_texts.append(ocr_cache[media_file])

        # Combine all text
        combined = ' '.join(tweet_texts) + ' ' + ' '.join(ocr_texts)
        combined = ' '.join(combined.split())  # normalize whitespace

        paper_texts.append({
            'id': paper['id'],
            'authors': paper.get('authors', ''),
            'title': paper.get('title', ''),
            'year': paper.get('year'),
            'text': combined,
            'threadLength': paper.get('threadLength', 0),
        })

    return paper_texts

def generate_embeddings(embedder, paper_texts):
    """Generate embeddings for all papers."""
    print(f"Generating embeddings for {len(paper_texts)} papers...")

    texts = [p['text'] for p in paper_texts]

    # Batch encode for efficiency
    embeddings = embedder.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True  # Pre-normalize for faster cosine similarity
    )

    print(f"Embeddings shape: {embeddings.shape}")
    return embeddings

def save_search_index(paper_texts, embeddings):
    """Save search index as compact JSON."""
    output_file = OUTPUT_DIR / "search-index.json"

    # Convert embeddings to list and round to reduce file size
    # 384-dim * 241 papers * 4 bytes = ~370KB uncompressed
    # With 4 decimal places: smaller JSON
    embeddings_list = [[round(float(x), 4) for x in emb] for emb in embeddings]

    index = {
        'version': 1,
        'embedding_dim': embeddings.shape[1],
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
    print(f"Saved search index: {output_file} ({size_mb:.2f} MB)")

def main():
    print("=" * 60)
    print("Building semantic search index for paper threads")
    print("=" * 60)

    # Load papers
    papers = load_papers()
    print(f"Loaded {len(papers['papers'])} papers")

    # Setup OCR and process images
    reader = setup_ocr()
    ocr_cache = ocr_all_images(reader, papers)

    # Build combined texts
    paper_texts = build_paper_texts(papers, ocr_cache)

    # Generate embeddings
    embedder = setup_embedder()
    embeddings = generate_embeddings(embedder, paper_texts)

    # Save search index
    save_search_index(paper_texts, embeddings)

    print("=" * 60)
    print("Done! Search index ready for client-side use.")
    print("=" * 60)

if __name__ == "__main__":
    main()
