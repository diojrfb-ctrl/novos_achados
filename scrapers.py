import re
import random
import logging
from curl_cffi import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)

class AmazonScraper:
    def __init__(self, store_id):
        self.store_id = store_id

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

        # Agora incluindo página de ofertas reais
        self.urls_busca = [
            "https://www.amazon.com.br/deals",
            "https://www.amazon.com.br/gp/goldbox",
            "https://www.amazon.com.br/s?k=ofertas+relampago&pct-off=30-",
            "https://www.amazon.com.br/s?k=eletronicos+em+promocao&pct-off=35-"
        ]

    # -------------------------
    # FUNÇÃO DE SCORE
    # -------------------------
    def calcular_score(self, desconto, rating, reviews, relampago):
        score = 0

        if relampago:
            score += 50

        if desconto >= 40:
            score += 35
        elif desconto >= 30:
            score += 25
        elif desconto >= 20:
            score += 15

        if rating >= 4.5:
            score += 20
        elif rating >= 4.0:
            score += 10

        if reviews >= 1000:
            score += 20
        elif reviews >= 300:
            score += 10

        return score

    # -------------------------
    # EXTRAÇÃO PRINCIPAL
    # -------------------------
    def extrair_ofertas(self):
        url = random.choice(self.urls_busca)

        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://www.google.com.br/"
        }

        try:
            res = requests.get(url, headers=headers, impersonate="chrome120", timeout=30)

            if res.status_code != 200:
                logging.warning(f"Erro HTTP {res.status_code}")
                return []

            soup = BeautifulSoup(res.text, "html.parser")
            itens = soup.find_all("div", {"data-component-type": "s-search-result"})

            produtos = []

            for item in itens:

                link_tag = item.find("a", href=True)
                titulo_tag = item.find("h2")
                img_tag = item.find("img", {"class": "s-image"})

                preco_whole = item.find("span", {"class": "a-price-whole"})
                preco_fraction = item.find("span", {"class": "a-price-fraction"})
                preco_antigo_tag = item.find("span", {"class": "a-offscreen"})
                rating_tag = item.find("span", {"class": "a-icon-alt"})
                reviews_tag = item.find("span", {"class": "a-size-base s-underline-text"})

                if not (link_tag and titulo_tag and preco_whole):
                    continue

                # ASIN
                asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", link_tag['href'])
                if not asin_match:
                    continue

                asin = asin_match.group(1)

                # PREÇO ATUAL
                preco_atual_str = preco_whole.get_text().strip()
                if preco_fraction:
                    preco_atual_str += "," + preco_fraction.get_text().strip()

                preco_atual = float(
                    preco_atual_str.replace(".", "").replace(",", ".")
                )

                # PREÇO ANTIGO
                preco_antigo = 0
                if preco_antigo_tag:
                    try:
                        valor = preco_antigo_tag.get_text().replace("R$", "").strip()
                        preco_antigo = float(valor.replace(".", "").replace(",", "."))
                    except:
                        preco_antigo = 0

                # DESCONTO REAL
                desconto = 0
                if preco_antigo > preco_atual:
                    desconto = int((preco_antigo - preco_atual) / preco_antigo * 100)

                # RATING
                rating = 0
                if rating_tag:
                    try:
                        rating = float(rating_tag.get_text().split(" ")[0].replace(",", "."))
                    except:
                        rating = 0

                # REVIEWS
                reviews = 0
                if reviews_tag:
                    try:
                        reviews = int(reviews_tag.get_text().replace(".", ""))
                    except:
                        reviews = 0

                # DETECTAR PROMOÇÃO RELÂMPAGO
                relampago = bool(
                    item.find(string=lambda t: t and "Relâmpago" in t)
                )

                score = self.calcular_score(desconto, rating, reviews, relampago)

                produtos.append({
                    "id": asin,
                    "titulo": titulo_tag.get_text().strip()[:90],
                    "preco": f"R$ {preco_atual_str}",
                    "preco_antigo": f"R$ {preco_antigo:.2f}" if preco_antigo > 0 else "",
                    "desconto": desconto,
                    "rating": rating,
                    "reviews": reviews,
                    "relampago": relampago,
                    "score": score,
                    "imagem": img_tag['src'] if img_tag else None,
                    "url": f"https://www.amazon.com.br/dp/{asin}?tag={self.store_id}"
                })

            # Ordena pelo melhor score
            produtos = sorted(produtos, key=lambda x: x["score"], reverse=True)

            return produtos[:3]

        except Exception as e:
            logging.error(f"Erro no scraper: {e}")
            return []
