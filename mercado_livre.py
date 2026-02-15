from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    try:
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break
            link_tag = item.select_one("a")
            if not link_tag: continue
            
            link = link_tag["href"]
            prod_id = extrair_mlb(link)
            if not prod_id: continue

            # --- MELHORIA NA CAPTURA DA IMAGEM ---
            img_tag = item.select_one("img")
            img_url = None
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("src")
                if img_url:
                    # Remove extensões webp e variações de miniatura
                    # Forçamos o sufixo -O.jpg que o Telegram reconhece como FOTO
                    img_url = img_url.split("?")[0] # Remove parâmetros extras
                    img_url = img_url.replace("-I.jpg", "-O.jpg").replace("-V.jpg", "-O.jpg").replace("-X.jpg", "-O.jpg")
                    if not img_url.endswith(".jpg"):
                        img_url = img_url.split(".")[0] + ".jpg"

            titulo_tag = item.select_one(".poly-component__title") or item.select_one(".ui-search-item__title")
            preco_tag = item.select_one(".andes-money-amount__fraction")
            parc_tag = item.select_one(".poly-component__installments") or item.select_one(".ui-search-item__group__element")

            if not titulo_tag or not preco_tag: continue

            resultados.append({
                "id": prod_id,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "imagem": img_url,
                "link": f"{link}&matt_tool={MATT_TOOL}",
                "parcelas": parc_tag.get_text(strip=True) if parc_tag else "Consulte parcelas",
                "tem_pix": "pix" in item.get_text().lower(),
                "status": "duplicado" if ja_enviado(prod_id) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro ML: {e}")
        return []