import re

def extrair_mlb(url: str) -> str | None:
    match = re.search(r"MLB-?(\d+)", url)
    return f"MLB{match.group(1)}" if match else None

def validar_desconto_real(preco_atual: float, preco_antigo: float) -> bool:
    """Retorna False se o desconto for absurdamente alto (>50%), indicando erro."""
    if not preco_antigo or preco_antigo <= 0:
        return True
    desconto = (1 - (preco_atual / preco_antigo)) * 100
    # Descontos acima de 50% geralmente são erro de variação ou bug de scraping
    return desconto < 50