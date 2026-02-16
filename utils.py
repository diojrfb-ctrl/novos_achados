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
    """Gera um link limpo e funcional para qualquer tipo de anúncio do ML"""
    # 1. Tenta identificar se é um produto de catálogo (/p/MLB...)
    if "/p/MLB" in url:
        match_p = re.search(r"MLB\d+", url)
        if match_p:
            return f"https://www.mercadolivre.com.br/p/{match_p.group(0)}?matt_tool={matt_tool}"

    # 2. Se não for catálogo, extrai o ID do anúncio comum (MLB12345)
    match_mlb = re.search(r"MLB-?(\d+)", url)
    if match_mlb:
        id_numerico = match_mlb.group(1)
        # Link encurtado oficial para anúncios comuns
        return f"https://www.mercadolivre.com.br/p/MLB{id_numerico}?matt_tool={matt_tool}"
    
    # 3. Se tudo falhar, limpa os parâmetros de lixo mas mantém a URL base
    url_limpa = url.split("?")[0].split("#")[0]
    return f"{url_limpa}?matt_tool={matt_tool}"