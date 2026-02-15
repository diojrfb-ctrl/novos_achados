import os
import asyncio
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Importando nossos componentes
from database import DB
from scrapers import AmazonScraper

load_dotenv()

# Configurações do Telegram
client = TelegramClient(
    StringSession(os.getenv("STRING_SESSION")),
    int(os.getenv("API_ID")),
    os.getenv("API_HASH")
)

db = DB()
amazon = AmazonScraper(os.getenv("StoreID"))


async def postar_oferta(oferta):
    badge = "⭐ **DESTAQUE**\n" if oferta.get("premium") else ""
    msg = (
        f"{badge}"
        f"🛍 **{oferta['titulo']}**\n\n"
        f"💰 **Por apenas: {oferta['preco']}**\n\n"
        f"🚚 Frete GRÁTIS Prime\n"
        f"🛒 **Link:** {oferta['url']}\n\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    try:
        if oferta['imagem']:
            await client.send_file(os.getenv("MEU_CANAL"), file=oferta['imagem'], caption=msg)
        else:
            await client.send_message(os.getenv("MEU_CANAL"), msg)
        return True
    except Exception as e:
        print(f"Erro ao postar: {e}")
        return False


async def loop_principal():
    await client.connect()
    print("🚀 Bot Componentizado Online!")

    while True:
        print("🔎 Varrendo Amazon...")
        ofertas = amazon.extrair_ofertas()

        for oferta in ofertas:
            if not db.ja_postado("amazon", oferta['id']):
                sucesso = await postar_oferta(oferta)
                if sucesso:
                    db.salvar_postado("amazon", oferta['id'])
                    print(f"✅ Postado: {oferta['id']}")
                    await asyncio.sleep(30)  # Delay entre posts

        espera = random.randint(1200, 2400)
        print(f"⏳ Dormindo {espera // 60} min...")
        await asyncio.sleep(espera)


if __name__ == "__main__":
    asyncio.run(loop_principal())