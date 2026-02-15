import re

def extrair_asin(url):
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else None

def extrair_mlb(url):
    match = re.search(r"MLB\d+", url)
    return match.group(0) if match else None
