import re

def extrair_asin(url):
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else None

def extrair_mlb(url):
    # Procura pelo padrão MLB seguido de números
    match = re.search(r"MLB-?\d+", url)
    if match:
        return match.group(0).replace("-", "")
    return None

def limpar_link_ml(url, matt_tool):
    """Gera um link curto e limpo para o Mercado Livre"""
    mlb_id = extrair_mlb(url)
    if mlb_id:
        # Formato curto oficial que passa confiança
        return f"https://www.mercadolivre.com.br/p/{mlb_id}?matt_tool={matt_tool}"
    return url