"""
Corpus scraper: fetches and caches content from the three support sites.
Run once to populate the data/ folder.
"""
import os
import json
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SupportTriageBot/1.0; "
        "+https://github.com/support-triage)"
    )
}

SEED_URLS = {
    "hackerrank": [
        "https://support.hackerrank.com/hc/en-us",
        "https://support.hackerrank.com/hc/en-us/categories/115001777512",
        "https://support.hackerrank.com/hc/en-us/categories/115001893191",
    ],
    "claude": [
        "https://support.claude.com/en/",
        "https://support.claude.com/en/collections/9990566-getting-started",
    ],
    "visa": [
        "https://www.visa.co.in/support.html",
        "https://www.visa.co.in/pay-with-visa/find-a-card/travel-currency.html",
    ],
}

MAX_PAGES_PER_SITE = 50
DELAY = 1.0  # seconds between requests


def url_to_filename(url: str) -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    slug = urlparse(url).path.strip("/").replace("/", "_")[:50]
    return f"{slug}_{h}.json"


def fetch_page(url: str) -> dict | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        # Remove nav/footer/script noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collect internal links
        links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if urlparse(href).netloc == urlparse(url).netloc:
                links.append(href)
        return {"url": url, "text": text, "links": list(set(links))}
    except Exception as e:
        print(f"  [WARN] Could not fetch {url}: {e}")
        return None


def crawl_site(name: str, seeds: list[str]) -> list[dict]:
    site_dir = os.path.join(DATA_DIR, name)
    os.makedirs(site_dir, exist_ok=True)

    visited = set()
    queue = list(seeds)
    pages = []

    # Base domains allowed
    base_domains = {urlparse(s).netloc for s in seeds}

    while queue and len(visited) < MAX_PAGES_PER_SITE:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        cache_file = os.path.join(site_dir, url_to_filename(url))
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                page = json.load(f)
            print(f"  [CACHE] {url}")
        else:
            print(f"  [FETCH] {url}")
            page = fetch_page(url)
            if page:
                with open(cache_file, "w") as f:
                    json.dump(page, f, indent=2)
            time.sleep(DELAY)

        if page:
            pages.append(page)
            for link in page.get("links", []):
                if urlparse(link).netloc in base_domains and link not in visited:
                    queue.append(link)

    print(f"  => {name}: {len(pages)} pages collected")
    return pages


def build_chunks(pages: list[dict], source: str) -> list[dict]:
    """Split page text into paragraph-sized chunks."""
    chunks = []
    for page in pages:
        url = page["url"]
        paragraphs = [p.strip() for p in page["text"].split("\n\n") if len(p.strip()) > 80]
        for i, para in enumerate(paragraphs):
            chunks.append({
                "source": source,
                "url": url,
                "chunk_id": f"{source}_{hashlib.md5(para.encode()).hexdigest()[:8]}",
                "text": para[:1500],  # cap chunk length
            })
    return chunks


def main():
    all_chunks = []
    for name, seeds in SEED_URLS.items():
        print(f"\nCrawling {name} ...")
        pages = crawl_site(name, seeds)
        chunks = build_chunks(pages, name)
        print(f"  => {len(chunks)} chunks from {name}")
        all_chunks.extend(chunks)

    out_path = os.path.join(DATA_DIR, "corpus.json")
    with open(out_path, "w") as f:
        json.dump(all_chunks, f, indent=2)
    print(f"\nTotal chunks: {len(all_chunks)} → saved to {out_path}")


if __name__ == "__main__":
    main()
