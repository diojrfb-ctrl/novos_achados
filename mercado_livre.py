from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb, limpar_para_link_normal
from redis_client import ja_enviado
import re


def buscar_mercado_livre(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome110",
            timeout=15
        )

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []

        for item in items:
            if len(resultados) >= limite:
                break

            link_tag = item.select_one("a")
            if not link_tag:
                continue

            url_original = link_tag.get("href", "")

            # ❌ BLOQUEIA LINKS CLICK1
            if "click1.mercadolivre.com.br" in url_original:
                continue

            prod_id = extrair_mlb(url_original)
            id_referencia = prod_id if prod_id else url_original

            # ❌ Se já foi enviado, ignora
            if ja_enviado(id_referencia):
                continue

            # Mantém link limpo padrão
            link_final = limpar_para_link_normal(url_original, MATT_TOOL)

            # =========================
            # PREÇO ATUAL
            # =========================
            f = item.select_one(".poly-price__current .andes-money-amount__fraction")
            c = item.select_one(".poly-price__current .andes-money-amount__cents")

            if not f:
                continue

            valor_promo = f.get_text(strip=True)
            if c:
                valor_promo += f",{c.get_text(strip=True)}"

            # =========================
            # PREÇO ANTIGO
            # =========================
            antigo_tag = item.select_one(
                ".andes-money-amount--previous .andes-money-amount__fraction"
            )
            p_antigo = antigo_tag.get_text(strip=True) if antigo_tag else None

            # =========================
            # PARCELAMENTO
            # =========================
            parcela_tag = item.select_one(".poly-price__installments")
            parcela_texto = parcela_tag.get_text(strip=True) if parcela_tag else ""

            # =========================
            # ESTOQUE
            # =========================
            estoque_tag = item.select_one(".poly-component__promotional-info")
            estoque = "Disponível"

            if estoque_tag:
                texto_estoque = estoque_tag.get_text(strip=True)
                if "restam" in texto_estoque.lower():
                    estoque = texto_estoque

            # =========================
            # FRETE
            # =========================
            frete_tag = item.select_one(".poly-component__shipping")
            frete_info = frete_tag.get_text(strip=True) if frete_tag else "Consulte o frete"

            # =========================
            # TÍTULO
            # =========================
            titulo_tag = item.select_one(
                ".poly-component__title, .ui-search-item__title"
            )
            if not titulo_tag:
                continue

            titulo = titulo_tag.get_text(strip=True)

            # =========================
            # IMAGEM
            # =========================
            img_tag = item.select_one("img")
            imagem = img_tag.get("src") if img_tag else None

            # =========================
            # AVALIAÇÕES
            # =========================
            nota_tag = item.select_one(".poly-reviews__rating")
            total_tag = item.select_one(".poly-reviews__total")

            nota = nota_tag.get_text(strip=True) if nota_tag else "4.9"
            avaliacoes = (
                re.sub(r"\D", "", total_tag.get_text())
                if total_tag
                else "100"
            )

            resultados.append({
                "id": id_referencia,
                "titulo": titulo,
                "preco": valor_promo,
                "preco_antigo": p_antigo,
                "parcelas": parcela_texto,
                "frete": frete_info,
                "estoque": estoque,
                "link": link_final,
                "imagem": imagem,
                "nota": nota,
                "avaliacoes": avaliacoes
            })

        return resultados

    except Exception as e:
        print(f"Erro ao buscar no Mercado Livre: {e}")
        return []
