import re

def extrair_mlb(url: str) -> str | None:
    # Captura o padrão MLB seguido de números
    match = re.search(r"MLB-?(\d+)", url)
    if match:
        return f"MLB{match.group(1)}"
    return None

def limpar_link_ml(url: str, matt_tool: str) -> str:
    """Gera o link mais curto possível que funciona para QUALQUER anúncio"""
    mlb_id = extrair_mlb(url)
    if mlb_id:
        # Formato: mercadolivre.com.br/MLB12345?matt_tool=...
        # Este formato funciona para catálogo e para vendedores comuns
        return f"https://www.mercadolivre.com.br/{mlb_id}?matt_tool={matt_tool}"
    return url