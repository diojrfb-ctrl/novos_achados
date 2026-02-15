from curl_cffi import requests
from bs4 import BeautifulSoup
import time, random, re
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://www.amazon.com.br/s?k={termo}"
    try:
        time.sleep(random.uniform(1, 3))
        response = requests.get(url, headers=HEADERS, impersonate="chrome124", timeout=20)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break
            asin = produto.get("data-asin")
            if not asin: continue

            # Seletores de Imagem, Título e Preço
            img_tag = produto.select_one(".s-image")
            titulo_tag = produto.select_one("h2 span")
            preco_tag = produto.select_one(".a-price-whole")
            
            if not titulo_tag or not preco_tag: continue

            texto_todo = produto.get_text().lower()
            
            # Extração de Parcelamento (Regex simples)
            parcelas = "Consulte parcelamento no site"
            match_parc = re.search(r"em até (\d+x)", texto_todo)
            if match_parc: parcelas = f"Em até {match_parc.group(1)} no cartão"

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "imagem": img_tag.get("src") if img_tag else None,
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "parcelas": parcelas,
                "tem_pix": "pix" in texto_todo or "15%" in texto_todo,
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro Amazon: {e}")
        return []