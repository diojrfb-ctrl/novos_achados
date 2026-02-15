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
        # Seleciona os cards de produtos
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break
            link_tag = item.select_one("a")
            if not link_tag: continue
            
            link = link_tag["href"]
            prod_id = extrair_mlb(link)
            if not prod_id: continue

            # --- CAPTURA DE PREÇO CORRIGIDA ---
            
            # 1. Primeiro, buscamos o container do preço ATUAL. 
            # O ML geralmente usa metadata ou classes específicas para o preço de venda.
            # Vamos buscar o preço que NÃO está dentro da tag de preço anterior.
            preco_venda_container = item.select_one(".poly-price__current .andes-money-amount") or \
                                   item.select_one(".ui-search-price__second-line .andes-money-amount") or \
                                   item.select_one(".andes-money-amount:not(.andes-money-amount--previous)")

            # Extração do valor real (Fração + Centavos)
            fração = preco_venda_container.select_one(".andes-money-amount__fraction") if preco_venda_container else None
            centavos = preco_venda_container.select_one(".andes-money-amount__cents") if preco_venda_container else None
            
            valor_final = fração.get_text(strip=True) if fração else "0"
            if centavos:
                valor_final += f",{centavos.get_text(strip=True)}"

            # 2. Preço Antigo (especificamente da classe --previous)
            preco_antigo_tag = item.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
            preco_antigo = preco_antigo_tag.get_text(strip=True) if preco_antigo_tag else None

            # 3. Desconto (Ex: 49% OFF)
            desconto_tag = item.select_one(".andes-money-amount__discount")
            porcentagem = desconto_tag.get_text(strip=True) if desconto_tag else None

            # --- TÍTULO E IMAGEM ---
            titulo_tag = item.select_one(".poly-component__title, .ui-search-item__title")
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Produto sem título"
            
            img_tag = item.select_one("img")
            img_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else None
            if img_url:
                # Melhora a qualidade da imagem
                img_url = img_url.replace("-I.jpg", "-O.jpg").replace("-V.jpg", "-O.jpg")

            # --- PROVA SOCIAL ---
            texto_item = item.get_text(" ", strip=True).lower()
            vendas = "📦 Novo"
            if "vendido" in texto_item:
                if "+500" in texto_item: vendas = "📦 +500 vendidos"
                elif "+10mil" in texto_item: vendas = "📦 +10mil vendidos"
                elif "mil" in texto_item: vendas = "📦 +1.000 vendidos"

            resultados.append({
                "id": prod_id,
                "titulo": titulo,
                "preco": valor_final,
                "preco_antigo": preco_antigo,
                "desconto": porcentagem,
                "imagem": img_url,
                "link": f"{link}&matt_tool={MATT_TOOL}",
                "vendas": vendas,
                "avaliacao": "⭐ 4.8+" if "4." in texto_item else None,
                "parcelas": item.select_one(".poly-component__installments").get_text(strip=True) if item.select_one(".poly-component__installments") else "Confira parcelas",
                "status": "duplicado" if ja_enviado(prod_id) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro ML: {e}")
        return []