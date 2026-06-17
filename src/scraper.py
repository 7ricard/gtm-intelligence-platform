import re

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

MAX_CHARS = 6000


def fetch_company_content(domain: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    paths = ["", "/about", "/pricing"]
    chunks = []

    for path in paths:
        url = f"https://{domain}{path}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception:
            continue

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            chunks.append(text)
        except Exception:
            continue

    combined = " ".join(chunks)
    collapsed = re.sub(r"\s+", " ", combined).strip()
    return collapsed[:MAX_CHARS]
