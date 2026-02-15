import asyncio
import threading
import os
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import (
    API_ID,
    API_HASH,
    STRING_SESSION,
    MEU_CANAL,
    LOG_CANAL
)

from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre


# =========================
# TELEGRAM CLIENT
# =========================

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH
)


# =========================
# FUNÇÃO DE LOG
# =========================

async def enviar_log(texto):
    try:
        await client.send_message(LOG_CANAL, f"📝 LOG:\n{texto}")
    except Exception as e:
        print("Erro ao enviar log:", e)


# =========================
# ENVIO DE OFERTAS
# =========================

async def enviar_ofertas():

    await enviar_log("Iniciando busca de ofertas...")

    # -------- AMAZON --------
    for p in buscar_amazon():
        try:
            msg = f"""🔥 OFERTA AMAZON

🛍 {p['titulo']}
💰 R$ {p['preco']}
"""

            if p.get("tem_pix"):
                msg += "⚡ Desconto no Pix\n"

            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])

            await enviar_log(f"Amazon enviado:\n{p['titulo']}")

            await asyncio.sleep(3)

        except Exception as e:
            await enviar_log(f"Erro Amazon:\n{e}")

    # -------- MERCADO LIVRE --------
    for p in buscar_mercado_livre():
        try:
            msg = f"""🔥 OFERTA MERCADO LIVRE

🛍 {p['titulo']}
💰 R$ {p['preco']}
"""

            if p.get("tem_pix"):
                msg += "⚡ Desconto no Pix\n"

            if p.get("mais_vendido"):
                msg += "🏆 Mais vendido\n"

            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])

            await enviar_log(f"Mercado Livre enviado:\n{p['titulo']}")

            await asyncio.sleep(3)

        except Exception as e:
            await enviar_log(f"Erro Mercado Livre:\n{e}")

    await enviar_log("Busca finalizada.")


# =========================
# LOOP PRINCIPAL DO BOT
# =========================

async def bot_loop():
    await client.start()
    print("Bot iniciado...")
    await enviar_log("✅ Bot iniciado com sucesso.")

    while True:
        try:
            await enviar_ofertas()
        except Exception as e:
            await enviar_log(f"Erro crítico no loop:\n{e}")

        await asyncio.sleep(3600)  # 1 hora


# =========================
# FLASK (OBRIGATÓRIO PRO RENDER)
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de ofertas rodando com sucesso!"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# =========================
# INICIALIZAÇÃO
# =========================

if __name__ == "__main__":

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    asyncio.run(bot_loop())
