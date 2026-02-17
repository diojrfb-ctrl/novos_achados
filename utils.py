import re

def extrair_mlb(url: str) -> str | None:
    # Captura o padrão MLB seguido de números
    match = re.search(r"MLB-?(\d+)", url)
    if match:
        return f"MLB{match.group(1)}"
    return None

def gerar_link_real(url_bruta: str, matt_tool: str) -> str:
    """Ignora links de cliques e gera um link direto funcional."""
    mlb_id = extrair_mlb(url_bruta)
    if mlb_id:
        # Este formato é o 'link universal' do ML que nunca quebra
        # Ele redireciona automaticamente para a página correta do produto
        return f"https://www.mercadolivre.com.br/p/{mlb_id}?matt_tool={matt_tool}"
    return url_bruta