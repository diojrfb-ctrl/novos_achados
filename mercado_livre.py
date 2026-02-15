from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    
    try:
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break

            link_tag = item.select_one("a")
            if not link_tag or not link_tag.get("href"): continue
            
            link = link_tag["href"]
            if "click.mercadolivre" in link: continue 
            
            prod_id = extrair_mlb(link)
            if not prod_id: continue

            # Captura da Imagem Otimizada
            img_tag = item.select_one("img")
            img_url = None
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("src")
                # Força a imagem de alta resolução (Original) para evitar "figurinha"
                if img_url and "D_NQ_NP" in img_url:
                    img_url = img_url.replace("-I.jpg", "-O.jpg").replace("-V.jpg", "-O.jpg")

            titulo_tag = item.select_one(".ui-search-item__title") or \
                         item.select_one(".poly-component__title")
            
            preco_tag = item.select_one(".andes-money-amount__fraction")
            
            # Captura de parcelamento
            parc_tag = item.select_one(".poly-component__installments") or \
                       item.select_one(".ui-search-item__group__element")

            if not titulo_tag or not preco_tag: continue

            status = "duplicado" if ja_enviado(prod_id) else "novo"
            texto_completo = item.get_text(" ", strip=True).lower()

            resultados.append({
                "id": prod_id,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "imagem": img_url,
                "link": f"{link}&matt_tool={MATT_TOOL}",
                "parcelas": parc_tag.get_text(strip=True) if parc_tag else "Consulte parcelas",
                "tem_pix": "pix" in texto_completo,
                "status": status
            })
            
        return resultados
    except Exception as e:
        print(f"[DEBUG ML] Erro crítico: {e}")
        return []