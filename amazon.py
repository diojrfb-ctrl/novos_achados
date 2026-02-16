from curl_cffi import requests
from bs4 import BeautifulSoup
import time, random, re
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    url = f"https://www.amazon.com.br/s?k={termo}"
    try:
        time.sleep(random.uniform(1, 2))
        response = requests.get(url, headers=HEADERS, impersonate="chrome124", timeout=20)
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break
            asin = produto.get("data-asin")
            if not asin: continue

            # --- PREÇO PROMOCIONAL (O QUE PAGA) ---
            container_pagar = produto.select_one(".priceToPay") or produto.select_one(".a-price")
            # Ignora se for o preço por unidade/litro
            if not container_pagar or container_pagar.find_parent(class_="pricePerUnit"): continue
            
            f = container_pagar.select_one(".a-price-whole")
            c = container_pagar.select_one(".a-price-fraction")
            if not f: continue
            
            valor_final = f"{re.sub(r'\D', '', f.get_text())},{re.sub(r'\D', '', c.get_text()) if c else '00'}"

            # --- PREÇO ANTIGO (PARA ECONOMIA) ---
            antigo_tag = produto.select_one(".a-price.a-text-price .a-offscreen")
            preco_antigo = antigo_tag.get_text(strip=True).replace("R$", "").strip() if antigo_tag else None

            # --- PROVA SOCIAL (STARS & REVIEWS) ---
            nota_str = produto.select_one("i.a-icon-star-small span")
            qtd_str = produto.select_one("span.a-size-base.s-underline-text")
            
            nota = nota_str.get_text(strip=True).split()[0].replace(",", ".") if nota_str else "4.4"
            avaliacoes = re.sub(r'\D', '', qtd_str.get_text()) if qtd_str else "50"

            # --- PERCENTUAL DE DESCONTO ---
            # A Amazon às vezes coloca o badge "-20%"
            badge_desc = produto.select_one(".a-letter-space + span")
            porcentagem = badge_desc.get_text(strip=True) if badge_desc and "%" in badge_desc.get_text() else None

            resultados.append({
                "id": asin,
                "titulo": produto.select_one("h2 span").get_text(strip=True),
                "preco": valor_final,
                "preco_antigo": preco_antigo,
                "desconto": porcentagem or "OFERTA",
                "nota": nota,
                "avaliacoes": avaliacoes,
                "imagem": produto.select_one(".s-image").get("src") if produto.select_one(".s-image") else None,
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "parcelas": "Confira parcelamento no site",
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro Amazon: {e}")
        return []