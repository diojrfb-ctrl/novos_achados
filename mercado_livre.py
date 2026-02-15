import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def gerar_link_ml(url: str) -> str:
    if "matt_tool=" in url:
        return url
    return f"{url}&matt_tool={MATT_TOOL}" if "?" in url else f"{url}?matt_tool={MATT_TOOL}"

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    # URL de busca limpa
    url = f"https://lista.mercadolivre.com.br/{termo}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Seletores do ML costumam mudar entre 'ui-search-layout__item' e 'ui-search-result__wrapper'
        items = soup.select(".ui-search-layout__item") or soup.select(".ui-search-result__wrapper")

        resultados = []
        for item in items[:limite]:
            link_tag = item.select_one("a.ui-search-link")
            if not link_tag: continue

            link = link_tag["href"]
            prod_id = extrair_mlb(link)
            
            if not prod_id or ja_enviado(prod_id):
                continue

            titulo_tag = item.select_one(".ui-search-item__title")
            preco_tag = item.select_one(".andes-money-amount__fraction")

            if not titulo_tag or not preco_tag: continue

            texto_completo = item.get_text(" ", strip=True).lower()

            resultados.append({
                "id": prod_id,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": gerar_link_ml(link),
                "tem_pix": "pix" in texto_completo,
                "mais_vendido": "vendido" in texto_completo,
                "status": "novo"
            })
        return resultados
    except Exception as e:
        print(f"Falha na raspagem ML: {e}")
        return []