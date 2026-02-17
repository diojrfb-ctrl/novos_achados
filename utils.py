import re

def extrair_mlb(url: str) -> str | None:
    match = re.search(r"MLB-?(\d+)", url)
    return f"MLB{match.group(1)}" if match else None

def limpar_link_ml(url: str, matt_tool: str) -> str:
    """Limpa o link mantendo a compatibilidade total e anexando o matt_tool"""
    # Remove tudo após a interrogação ou sustenido
    url_base = url.split("?")[0].split("#")[0]
    # Retorna a URL base + seu código de afiliado
    return f"{url_base}?matt_tool={matt_tool}"