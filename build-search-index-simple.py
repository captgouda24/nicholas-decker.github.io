"""
Build semantic search index for paper threads (tweet text only, no OCR).
Fast version that generates embeddings from tweet text.
OCR can be added later as an enhancement.
"""

import json
import sys
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Paths
BASE_DIR = Path("C:/Users/Owner/Documents/transmissions11.github.io")
PAPERS_JSON = BASE_DIR / "paper-threads" / "papers-indexed.json"
OUTPUT_DIR = BASE_DIR / "paper-threads"

def load_papers():
    """Load the indexed papers JSON."""
    print("Loading papers...", flush=True)
    with open(PAPERS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_embedder():
    """Initialize sentence-transformers model."""
    print("Loading embedding model (this may download ~90MB on first run)...", flush=True)
    from sentence_transformers import SentenceTransformer
    # all-MiniLM-L6-v2 is fast and produces 384-dim embeddings
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Embedding model ready", flush=True)
    return model

def build_paper_texts(papers):
    """Build text for each paper from tweet content."""
    print("Building paper texts...", flush=True)
    paper_texts = []

    for paper in papers['papers']:
        # Collect all tweet text
        tweet_texts = []
        for tweet in paper.get('thread', []):
            text = tweet.get('text', '')
            # Remove t.co links
            text = ' '.join(w for w in text.split() if not w.startswith('https://t.co/'))
            tweet_texts.append(text)

        # Combine all text
        combined = ' '.join(tweet_texts)
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
        normalize_embeddings=True  # Pre-normalize for faster cosine similarity
    )

    print(f"Embeddings shape: {embeddings.shape}", flush=True)
    return embeddings

def save_search_index(paper_texts, embeddings):
    """Save search index as compact JSON."""
    output_file = OUTPUT_DIR / "search-index.json"

    # Convert embeddings to list and round to reduce file size
    embeddings_list = [[round(float(x), 4) for x in emb] for emb in embeddings]

    index = {
        'version': 1,
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
    print("Building semantic search index (tweet text only)", flush=True)
    print("=" * 60, flush=True)

    # Load papers
    papers = load_papers()
    print(f"Loaded {len(papers['papers'])} papers", flush=True)

    # Build combined texts (no OCR)
    paper_texts = build_paper_texts(papers)

    # Generate embeddings
    embedder = setup_embedder()
    embeddings = generate_embeddings(embedder, paper_texts)

    # Save search index
    save_search_index(paper_texts, embeddings)

    print("=" * 60, flush=True)
    print("Done! Search index ready.", flush=True)
    print("Note: OCR text not included. Run OCR separately if needed.", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
