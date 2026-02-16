import re

def extrair_asin(url: str) -> str | None:
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else None

def extrair_mlb(url: str) -> str | None:
    match = re.search(r"MLB-?(\d+)", url)
    if match:
        return f"MLB{match.group(1)}"
    return None