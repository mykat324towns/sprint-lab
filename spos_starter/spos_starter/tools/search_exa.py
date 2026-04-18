import os
from dotenv import load_dotenv

load_dotenv()

try:
    from exa_py import Exa
except ImportError:
    raise SystemExit("Missing dependency: exa-py. Run: pip install exa-py")

def search(query: str, num_results: int = 5):
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY is missing in .env")
    exa = Exa(api_key=api_key)
    return exa.search_and_contents(query, num_results=num_results)

if __name__ == "__main__":
    results = search("max velocity sprint force expression early stance")
    print(results)
