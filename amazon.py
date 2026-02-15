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

            # --- CAPTURA EXCLUSIVA DO PREÇO FINAL ---
            # Focamos no container 'priceToPay' que é único para o valor do fechamento
            container_pagar = produto.select_one(".priceToPay")
            
            # Se não encontrar o container específico, tentamos o a-price que NÃO seja preço por unidade
            if not container_pagar:
                todas_tags_preco = produto.select(".a-price")
                preco_valido = None
                for p in todas_tags_preco:
                    # Ignora se estiver dentro de 'pricePerUnit' ou for o preço riscado 'a-text-price'
                    if p.find_parent(class_="pricePerUnit") or p.find_parent(class_="a-text-price"):
                        continue
                    preco_valido = p
                    break
                container_pagar = preco_valido

            if not container_pagar: continue

            fração = container_pagar.select_one(".a-price-whole")
            centavos = container_pagar.select_one(".a-price-fraction")
            
            if not fração: continue
            
            # Limpeza radical de caracteres não numéricos
            valor_fração = re.sub(r'\D', '', fração.get_text())
            valor_centavos = re.sub(r'\D', '', centavos.get_text()) if centavos else "00"
            
            valor_final = f"{valor_fração},{valor_centavos}"

            # --- TÍTULO E IMAGEM ---
            titulo_tag = produto.select_one("h2 span")
            img_tag = produto.select_one(".s-image")
            if not titulo_tag: continue

            texto_todo = produto.get_text().lower()
            
            # --- PROVA SOCIAL ---
            vendas = "📦 Novo"
            if "compras no mês passado" in texto_todo:
                match_vendas = re.search(r"([\d\+]+ mil?|[\d\+]+) compras no mês passado", texto_todo)
                if match_vendas:
                    vendas = f"📦 {match_vendas.group(1)} compras no mês passado"

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": valor_final,
                "preco_antigo": None, # Removido conforme solicitado
                "desconto": "OFERTA",
                "imagem": img_tag.get("src") if img_tag else None,
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "parcelas": "Consulte no site",
                "vendas": vendas,
                "avaliacao": "⭐ Ver avaliações" if "estrelas" in texto_todo else None,
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro Amazon: {e}")
        return []