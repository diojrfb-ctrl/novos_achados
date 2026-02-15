import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://lista.mercadolivre.com.br/{termo}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Tenta os dois tipos de containers comuns do ML
        items = soup.select(".ui-search-layout__item") or soup.select(".ui-search-result__wrapper")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break

            link_tag = item.select_one("a.ui-search-link")
            if not link_tag: continue
            link = link_tag["href"]
            
            prod_id = extrair_mlb(link)
            if not prod_id: continue

            titulo_tag = item.select_one(".ui-search-item__title")
            preco_tag = item.select_one(".andes-money-amount__fraction")
            
            if not titulo_tag or not preco_tag: continue

            status = "duplicado" if ja_enviado(prod_id) else "novo"
            texto_todo = item.get_text(" ").lower()

            resultados.append({
                "id": prod_id,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": f"{link}&matt_tool={MATT_TOOL}",
                "tem_pix": "pix" in texto_todo,
                "status": status
            })
        return resultados
    except:
        return []