import os
import asyncio
import random
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

from database import DB
from scrapers import AmazonScraper

load_dotenv()

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot de Promoções Online!", 200

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
    # Lógica de Preço: Exibe o preço antigo riscado se disponível
    if oferta['preco_antigo']:
        texto_preco = f"❌ De: ~~{oferta['preco_antigo']}~~\n✅ **Por: {oferta['preco']}**"
    else:
        texto_preco = f"💰 **Preço: {oferta['preco']}**"

    msg = (
        f"🔥 **OFERTA DETECTADA** 🔥\n\n"
        f"🛍 **{oferta['titulo']}**\n\n"
        f"{texto_preco}\n\n"
        f"🚚 Frete GRÁTIS Prime\n"
        f"🛒 **COMPRE AQUI:** {oferta['url']}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *Preços sujeitos a alteração.*"
    )
    
    try:
        if oferta['imagem']:
            await client.send_file(os.getenv("MEU_CANAL"), file=oferta['imagem'], caption=msg)
        else:
            await client.send_message(os.getenv("MEU_CANAL"), msg)
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")
        return False

async def loop_principal():
    await client.connect()
    print("🚀 Bot Caçador de Promoções Iniciado!")

    while True:
        try:
            ofertas = amazon.extrair_ofertas()
            for oferta in ofertas:
                if not db.ja_postado("amazon", oferta['id']):
                    if await postar_oferta(oferta):
                        db.salvar_postado("amazon", oferta['id'])
                        print(f"📢 Promoção enviada: {oferta['id']}")
                        await asyncio.sleep(45) 

        except Exception as e:
            print(f"⚠️ Erro no loop: {e}")

        espera = random.randint(1200, 2400)
        print(f"⏳ Dormindo {espera//60} min...")
        await asyncio.sleep(espera)

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    asyncio.run(loop_principal())