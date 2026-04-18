import os
from dotenv import load_dotenv

load_dotenv()

try:
    from firecrawl import FirecrawlApp
except ImportError:
    raise SystemExit("Missing dependency: firecrawl-py. Run: pip install firecrawl-py")

def scrape(url: str):
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY is missing in .env")
    app = FirecrawlApp(api_key=api_key)
    return app.scrape_url(url)

if __name__ == "__main__":
    print(scrape("https://example.com"))
