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

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, f"📝 LOG:\n{texto}")
    except Exception as e:
        print(f"Erro ao enviar log: {e}")


# =========================
# ENVIO DE OFERTAS
# =========================

async def enviar_ofertas():
    await enviar_log("Iniciando busca de ofertas...")

    # -------- AMAZON --------
    produtos_amazon = buscar_amazon()
    for p in produtos_amazon:
        try:
            msg = f"🔥 OFERTA AMAZON\n\n"
            msg += f"🛍 {p['titulo']}\n"
            msg += f"💰 R$ {p['preco']}\n"

            if p.get("tem_pix"):
                msg += "⚡️ Desconto especial no Pix!\n"
            
            if p.get("tem_cupom"):
                msg += "🎟 Verifique o cupom na página!\n"

            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])

            await enviar_log(f"Amazon enviado:\n{p['titulo']}")
            await asyncio.sleep(5)  # Delay entre mensagens para evitar spam

        except Exception as e:
            await enviar_log(f"Erro ao postar Amazon: {e}")

    # -------- MERCADO LIVRE --------
    produtos_ml = buscar_mercado_livre()
    for p in produtos_ml:
        try:
            msg = f"🔥 OFERTA MERCADO LIVRE\n\n"
            msg += f"🛍 {p['titulo']}\n"
            msg += f"💰 R$ {p['preco']}\n"

            if p.get("tem_pix"):
                msg += "⚡️ Tem desconto no Pix!\n"

            if p.get("mais_vendido"):
                msg += "🏆 Um dos mais vendidos do site\n"

            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])

            await enviar_log(f"Mercado Livre enviado:\n{p['titulo']}")
            await asyncio.sleep(5)

        except Exception as e:
            await enviar_log(f"Erro ao postar Mercado Livre: {e}")

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
            await enviar_log(f"Erro crítico no loop: {e}")

        # Aguarda 1 hora antes da próxima busca
        await asyncio.sleep(3600)


# =========================
# FLASK (MANTER O BOT ONLINE)
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
    # Rodar Flask numa thread separada
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Rodar o bot assíncrono
    asyncio.run(bot_loop())