import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def extrair_mlb(url: str) -> str | None:
    match = re.search(r"MLB-?(\d+)", url)
    return f"MLB{match.group(1)}" if match else None

def limpar_para_link_normal(url: str, matt_tool: str) -> str:
    """Anexa o matt_tool à URL original, preservando todos os parâmetros necessários."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    
    # Adiciona ou atualiza o seu código de afiliado
    qs['matt_tool'] = [matt_tool]
    
    nova_query = urlencode(qs, doseq=True)
    
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        nova_query,
        parsed.fragment
    ))