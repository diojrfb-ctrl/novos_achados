import asyncio
import io
import requests
import os
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession

# Seus módulos locais
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre
from redis_client import marcar_enviado

# ==============================
# TELEGRAM CLIENT
# ==============================
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)


# ==============================
# CATEGORIZAÇÃO AUTOMÁTICA
# ==============================
def extrair_categoria_hashtag(titulo: str) -> str:
    titulo_low = titulo.lower()

    categorias = {
        "Cozinha": ["panela", "fritadeira", "airfryer", "prato", "copo", "talher", "cozinha"],
        "Games": ["ps5", "xbox", "nintendo", "jogo", "gamer", "console"],
        "Eletronicos": ["smartphone", "celular", "iphone", "televisao", "tv", "monitor", "fone"],
        "Suplementos": ["whey", "creatina", "suplemento", "vitamin", "albumina", "protein"],
        "Informatica": ["notebook", "laptop", "teclado", "mouse", "ssd", "memoria"],
        "Casa": ["toalha", "lençol", "aspirador", "iluminação", "móvel", "sofa"]
    }

    for cat, keywords in categorias.items():
        if any(kw in titulo_low for kw in keywords):
            return f" #{cat}"

    return ""


# ==============================
# FORMATAÇÃO DA COPY
# ==============================
def formatar_copy_otimizada(p: dict) -> str:
    try:
        atual_num = float(p['preco'].replace('.', '').replace(',', '.'))

        linha_preco_antigo = ""
        linha_desconto = ""

        if p.get('preco_antigo'):
            antigo_num = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            if antigo_num > atual_num:
                porcentagem = int((1 - (atual_num / antigo_num)) * 100)
                linha_preco_antigo = f"💰 De: R$ {p['preco_antigo']}\n"
                linha_desconto = f"📉 ({porcentagem}% de desconto no Pix)\n"

        linha_cartao = ""
        if p.get('parcelas'):
            parcela_limpa = p['parcelas'].replace("ou", "").strip()
            linha_cartao = f"💳 ou {parcela_limpa}\n"

        hashtag_cat = extrair_categoria_hashtag(p['titulo'])

        copy = f"{p['titulo']}\n"
        copy += f"⭐ {p['nota']} ({p['avaliacoes']} opiniões)\n"
        copy += linha_preco_antigo
        copy += f"✅ POR: R$ {p['preco']}\n"
        copy += linha_desconto
        copy += linha_cartao
        copy += f"📦 Frete: {p['frete']}\n"
        copy += f"🔥 Estoque: {p['estoque']}\n\n"
        copy += f"🔗 LINK DA OFERTA:\n"
        copy += f"{p['link']}\n\n"
        copy += f"➡️ #Ofertas #MercadoLivre{hashtag_cat}"

        return copy

    except Exception as e:
        print(f"Erro na formatação: {e}")
        return f"{p['titulo']}\n\n✅ POR: R$ {p['preco']}\n\n🔗 {p['link']}"


# ==============================
# LOOP PRINCIPAL
# ==============================
async def loop_bot():
    await client.start()
    print("🚀 Bot de Ofertas Online!")

    while True:
        try:
            produtos = buscar_mercado_livre()

            if not produtos:
                print("Nenhum produto encontrado neste ciclo.")

            for p in produtos:
                try:
                    caption = formatar_copy_otimizada(p)

                    # Envio com imagem se existir
                    if p.get("imagem"):
                        try:
                            r = requests.get(p["imagem"], timeout=15)
                            r.raise_for_status()

                            foto = io.BytesIO(r.content)
                            foto.name = 'post.jpg'

                            await client.send_file(
                                MEU_CANAL,
                                foto,
                                caption=caption
                            )
                        except Exception as img_error:
                            print(f"Erro ao baixar imagem: {img_error}")
                            await client.send_message(MEU_CANAL, caption)
                    else:
                        await client.send_message(MEU_CANAL, caption)

                    marcar_enviado(p["id"])
                    print(f"✅ Enviado: {p['titulo'][:50]}")

                    await asyncio.sleep(25)  # Delay anti-spam

                except Exception as e:
                    print(f"Erro no item {p.get('id')}: {e}")
                    continue

        except Exception as loop_error:
            print(f"Erro no ciclo principal: {loop_error}")

        print("⏳ Aguardando próximo ciclo...")
        await asyncio.sleep(3600)  # 1 hora


# ==============================
# SERVIDOR PARA RENDER
# ==============================
app = Flask(__name__)

@app.route('/')
def health():
    return "OK", 200


async def main():
    port = int(os.environ.get("PORT", 10000))

    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port),
        daemon=True
    ).start()

    await loop_bot()


if __name__ == "__main__":
    asyncio.run(main())
