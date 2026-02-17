from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random
import re
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado


def buscar_amazon(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    url = f"https://www.amazon.com.br/s?k={termo}"

    try:
        time.sleep(random.uniform(1.2, 2.5))

        response = requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome124",
            timeout=20
        )

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})

        resultados = []

        for produto in produtos:
            if len(resultados) >= limite:
                break

            asin = produto.get("data-asin")
            if not asin:
                continue

            # ❌ Ignora se já enviado
            if ja_enviado(asin):
                continue

            # =========================
            # PREÇO ATUAL
            # =========================
            container = (
                produto.select_one(".priceToPay")
                or produto.select_one(".a-price")
            )

            # Ignora preço por unidade
            if not container or container.find_parent(class_="pricePerUnit"):
                continue

            whole = container.select_one(".a-price-whole")
            fraction = container.select_one(".a-price-fraction")

            if not whole:
                continue

            valor_inteiro = re.sub(r"\D", "", whole.get_text())
            valor_centavos = (
                re.sub(r"\D", "", fraction.get_text())
                if fraction else "00"
            )

            if not valor_inteiro:
                continue

            valor = f"{valor_inteiro},{valor_centavos}"

            # =========================
            # PREÇO ANTIGO
            # =========================
            antigo = produto.select_one(".a-price.a-text-price .a-offscreen")
            p_antigo = None

            if antigo:
                antigo_texto = antigo.get_text(" ", strip=True)
                antigo_limpo = (
                    antigo_texto
                    .replace("R$", "")
                    .replace(".", "")
                    .replace(",", ".")
                    .strip()
                )
                p_antigo = antigo_limpo

            # =========================
            # TÍTULO
            # =========================
            titulo_tag = produto.select_one("h2 span")
            if not titulo_tag:
                continue

            titulo = titulo_tag.get_text(" ", strip=True)

            # =========================
            # AVALIAÇÃO
            # =========================
            nota_tag = produto.select_one("i.a-icon-star-small span")
            qtd_tag = produto.select_one("span.a-size-base.s-underline-text")

            nota = (
                nota_tag.get_text(" ", strip=True)
                .split()[0]
                .replace(",", ".")
                if nota_tag else "4.7"
            )

            avaliacoes = (
                re.sub(r"\D", "", qtd_tag.get_text())
                if qtd_tag else "50"
            )

            # =========================
            # IMAGEM
            # =========================
            img_tag = produto.select_one(".s-image")
            imagem = img_tag.get("src") if img_tag else None

            # =========================
            # LINK AFILIADO
            # =========================
            link = f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}"

            resultados.append({
                "id": asin,
                "titulo": titulo,
                "preco": valor,
                "preco_antigo": p_antigo,
                "nota": nota,
                "avaliacoes": avaliacoes,
                "imagem": imagem,
                "link": link,
                "parcelas": "Confira no site",
                "frete": "Consulte o frete",
                "estoque": "Disponível"
            })

        return resultados

    except Exception as e:
        print(f"Erro ao buscar Amazon: {e}")
        return []
