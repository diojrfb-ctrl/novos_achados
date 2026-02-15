import re
import random
import logging
from curl_cffi import requests
from bs4 import BeautifulSoup

# Configuração de logs para monitorar o que acontece no Render
logging.basicConfig(level=logging.INFO)

class AmazonScraper:
    def __init__(self, store_id):
        self.store_id = store_id
        # Lista de User-Agents para rotacionar (Robustez contra bloqueio)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        self.termos_promocionais = [
            "ofertas relampago", "eletronicos em promocao", 
            "cozinha liquidacao", "smartphone desconto",
            "casa inteligente alexa", "perifericos gamer"
        ]

    def extrair_ofertas(self):
        termo = random.choice(self.termos_promocionais)
        url = f"https://www.amazon.com.br/s?k={termo.replace(' ', '+')}&pct-off=15-&s=review-rank"
        
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://www.google.com.br/"
        }

        try:
            # impersonate="chrome120" ajuda a passar pelo firewall da Amazon
            res = requests.get(url, headers=headers, impersonate="chrome120", timeout=30)
            
            if res.status_code == 503:
                logging.warning("⚠️ Amazon enviou 503 (Serviço Indisponível). Reduzindo velocidade.")
                return []
            
            if res.status_code != 200:
                logging.error(f"❌ Erro HTTP {res.status_code} na Amazon")
                return []

            soup = BeautifulSoup(res.text, "html.parser")
            produtos = []
            
            # Busca robusta: tenta várias classes comuns de resultados
            itens = soup.find_all("div", {"data-component-type": "s-search-result"})
            
            for item in itens:
                link_tag = item.find("a", href=True)
                titulo_tag = item.find("h2")
                img_tag = item.find("img", {"class": "s-image"})
                
                # Preços com fallback caso a classe mude
                preco_atual_inteiro = item.find("span", {"class": "a-price-whole"})
                preco_antigo_tag = item.find("span", {"class": "a-offscreen"})

                if link_tag and titulo_tag and preco_atual_inteiro:
                    href = link_tag['href']
                    # Regex robusto para pegar ASIN em qualquer tipo de URL da Amazon
                    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", href)
                    
                    if asin_match:
                        asin = asin_match.group(1)
                        
                        valor_atual = f"R$ {preco_atual_inteiro.get_text().strip()}"
                        valor_antigo = preco_antigo_tag.get_text().strip() if preco_antigo_tag else ""
                        
                        if valor_antigo == valor_atual: valor_antigo = ""

                        produtos.append({
                            "id": asin,
                            "titulo": titulo_tag.get_text().strip()[:90],
                            "preco": valor_atual,
                            "preco_antigo": valor_antigo,
                            "imagem": img_tag['src'] if img_tag else None,
                            "url": f"https://www.amazon.com.br/dp/{asin}?tag={self.store_id}"
                        })
                
                if len(produtos) >= 3: break
            return produtos

        except Exception as e:
            logging.error(f"❌ Falha crítica no Scraper: {e}")
            return []