import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def extrair_mlb(url: str) -> str | None:
    match = re.search(r"MLB-?(\d+)", url)
    return f"MLB{match.group(1)}" if match else None

def limpar_link_ml_completo(url: str, matt_tool: str) -> str:
    """Mantém a URL original funcional, removendo lixo e injetando o matt_tool."""
    parsed = urlparse(url)
    # Mantém apenas o seu matt_tool como parâmetro
    query = {'matt_tool': matt_tool}
    
    # Reconstrói a URL mantendo o path original (evita o erro 404)
    url_limpa = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        urlencode(query),
        '' # Remove fragmentos (#...)
    ))
    return url_limpa