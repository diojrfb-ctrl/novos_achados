import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, unquote

def extrair_mlb(url: str) -> str | None:
    match = re.search(r"MLB-?(\d+)", url)
    return f"MLB{match.group(1)}" if match else None


def limpar_para_link_normal(url: str, matt_tool: str) -> str:
    """
    Converte links click1 para link oficial do produto
    e adiciona matt_tool mantendo domínio confiável.
    """
    try:
        # 🔹 Se for link click1, extrair a URL real
        if "click1.mercadolivre.com.br" in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            if "url" in params:
                url = unquote(params["url"][0])

        # 🔹 Remove parâmetros desnecessários de tracking pesado
        parsed = urlparse(url)

        # Mantém apenas path principal (remove searchTracking, sid, etc.)
        path_limpo = parsed.path

        # 🔹 Extrai ID MLB para garantir URL limpa
        mlb_id = extrair_mlb(url)
        if mlb_id:
            path_limpo = f"/p/{mlb_id}"

        # 🔹 Reconstrói query apenas com matt_tool
        query = urlencode({"matt_tool": matt_tool})

        return urlunparse((
            "https",
            "www.mercadolivre.com.br",
            path_limpo,
            "",
            query,
            ""
        ))

    except Exception:
        return url
