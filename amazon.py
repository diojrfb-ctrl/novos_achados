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

            # --- ESTRATÉGIA PARA PREÇO REAL (O QUE PAGA) ---
            # 1. Procuramos primeiro o container específico do preço de fechamento
            container_pagar = produto.select_one(".priceToPay")
            
            if container_pagar:
                # Se achou o container oficial, pegamos o preço lá dentro
                fração = container_pagar.select_one(".a-price-whole")
                centavos = container_pagar.select_one(".a-price-fraction")
            else:
                # Fallback: tenta pegar o preço principal, mas GARANTE que não seja o 'pricePerUnit'
                # O preço real na Amazon geralmente tem a classe 'a-size-base-plus' ou similar no grid
                precos_gerais = produto.select(".a-price")
                fração, centavos = None, None
                for p in precos_gerais:
                    # Se o preço estiver dentro de algo que indique peso/unidade, ignoramos
                    if p.find_parent(class_="pricePerUnit") or p.find_parent(class_="a-text-price"):
                        continue
                    fração = p.select_one(".a-price-whole")
                    centavos = p.select_one(".a-price-fraction")
                    if fração: break

            if not fração: continue
            
            # Limpeza do valor
            valor_final = fração.get_text(strip=True).replace(".", "").replace(",", "")
            if centavos:
                valor_final += f",{centavos.get_text(strip=True)}"

            # --- PREÇO ANTIGO (RISCADO) ---
            # Ele fica em um container que tem a classe 'a-text-price' e NÃO tem 'priceToPay'
            preco_antigo_tag = produto.select_one(".a-price.a-text-price .a-offscreen")
            preco_antigo = None
            if preco_antigo_tag:
                preco_antigo = preco_antigo_tag.get_text(strip=True).replace("R$", "").strip()

            # --- TÍTULO E IMAGEM ---
            titulo_tag = produto.select_one("h2 span")
            img_tag = produto.select_one(".s-image")
            if not titulo_tag: continue

            texto_todo = produto.get_text().lower()
            
            # --- PROVA SOCIAL (EX: 10 MIL COMPRAS) ---
            vendas = "📦 Novo"
            if "compras no mês passado" in texto_todo:
                # Tenta extrair o número (ex: 10 mil)
                match_vendas = re.search(r"([\d\+]+ mil?|[\d\+]+) compras no mês passado", texto_todo)
                if match_vendas:
                    vendas = f"📦 {match_vendas.group(1)} compras no mês passado"

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": valor_final,
                "preco_antigo": preco_antigo,
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