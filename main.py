import os
import asyncio
import random
import threading
import logging
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

from database import DB
from scrapers import AmazonScraper

load_dotenv()

# Logger para o Render
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Sistema Robusto Online!", 200

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

client = TelegramClient(
    StringSession(os.getenv("STRING_SESSION")), 
    int(os.getenv("API_ID")), 
    os.getenv("API_HASH")
)

db = DB()
amazon = AmazonScraper(os.getenv("StoreID"))

async def postar_oferta(oferta):

    badge = "⚡ OFERTA RELÂMPAGO ⚡\n\n" if oferta["relampago"] else ""

    msg = (
        f"{badge}"
        f"🔥 **SUPER ACHADINHO AMAZON** 🔥\n\n"
        f"🛍 **{oferta['titulo']}**\n\n"
        f"💰 De: ~~{oferta['preco_antigo']}~~\n" if oferta['preco_antigo'] else ""
    )

    msg += (
        f"✅ **Por: {oferta['preco']}**\n"
        f"🔥 {oferta['desconto']}% OFF\n\n"
        f"⭐ {oferta['rating']} | 🗳 {oferta['reviews']} avaliações\n\n"
        f"🛒 **Comprar Agora:** {oferta['url']}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    try:
        if oferta['imagem']:
            await client.send_file(os.getenv("MEU_CANAL"), file=oferta['imagem'], caption=msg)
        else:
            await client.send_message(os.getenv("MEU_CANAL"), msg)
        return True
    except Exception as e:
        logging.error(f"Erro ao postar: {e}")
        return False

    # Formatação limpa e profissional
    preco_final = f"✅ **Por: {oferta['preco']}**"
    if oferta['preco_antigo']:
        preco_final = f"❌ De: ~~{oferta['preco_antigo']}~~\n" + preco_final

    msg = (
        f"🔥 **ACHADINHO AMAZON** 🔥\n\n"
        f"🛍 **{oferta['titulo']}**\n\n"
        f"{preco_final}\n\n"
        f"🚚 Frete GRÁTIS Prime\n"
        f"🛒 **Link de Compra:** {oferta['url']}\n\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    
    try:
        if oferta['imagem']:
            await client.send_file(os.getenv("MEU_CANAL"), file=oferta['imagem'], caption=msg)
        else:
            await client.send_message(os.getenv("MEU_CANAL"), msg)
        return True
    except Exception as e:
        logging.error(f"Erro ao postar no Telegram: {e}")
        return False

async def loop_principal():
    logging.info("🚀 Conectando ao Telegram...")
    await client.connect()
    
    while True:
        try:
            # Busca ofertas
            ofertas = amazon.extrair_ofertas()
            
            if not ofertas:
                logging.info("📭 Nenhuma oferta válida encontrada nesta rodada.")
            
            for oferta in ofertas:
                # Verifica no Redis se já foi postado (Camada de Robustez 2)
                if not db.ja_postado("amazon", oferta['id']):
                    if await postar_oferta(oferta):
                        db.salvar_postado("amazon", oferta['id'])
                        logging.info(f"📢 Sucesso: {oferta['id']} enviado.")
                        # Delay anti-spam
                        await asyncio.sleep(random.randint(30, 60)) 

        except Exception as e:
            logging.critical(f"💥 Erro inesperado no loop principal: {e}")
            await asyncio.sleep(60) # Espera um minuto antes de tentar se recuperar

        # Intervalo variável para simular comportamento humano
        espera = random.randint(900, 1800)
        logging.info(f"⏳ Dormindo {espera//60} minutos até a próxima varredura.")
        await asyncio.sleep(espera)

if __name__ == "__main__":
    # Servidor Flask em Thread separada para não travar o bot
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()
    
    try:
        asyncio.run(loop_principal())
    except Exception as e:
        logging.error(f"O bot parou forçadamente: {e}")