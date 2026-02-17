import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def extrair_mlb(url: str) -> str | None:
    match = re.search(r"MLB-?(\d+)", url)
    return f"MLB{match.group(1)}" if match else None

def limpar_para_link_normal(url: str, matt_tool: str) -> str:
    """Mantém a URL original (com nome do produto) e anexa o matt_tool"""
    # Se for link de clique (patrocinado), ele geralmente não tem o slug.
    # Mas para links normais de busca, isso aqui limpa o excesso:
    parsed = urlparse(url)
    # Mantém apenas o seu parâmetro de afiliado
    nova_query = urlencode({'matt_tool': matt_tool})
    
    # Reconstrói mantendo o path original (ex: /nome-produto-venda-MLB123)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        nova_query,
        ''
    ))