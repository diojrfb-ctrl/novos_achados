import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH
)

async def enviar_ofertas():

    # AMAZON
    for p in buscar_amazon():

        msg = f"""
🔥 OFERTA AMAZON

🛍 {p['titulo']}
💰 R$ {p['preco']}
"""

        if p["tem_pix"]:
            msg += "⚡ Desconto no Pix\n"

        msg += f"\n🔗 Comprar:\n{p['link']}"

        await client.send_message(MEU_CANAL, msg)
        marcar_enviado(p["id"])
        await asyncio.sleep(3)

    # MERCADO LIVRE
    for p in buscar_mercado_livre():

        msg = f"""
🔥 OFERTA MERCADO LIVRE

🛍 {p['titulo']}
💰 R$ {p['preco']}
"""

        if p["tem_pix"]:
            msg += "⚡ Desconto no Pix\n"

        if p["mais_vendido"]:
            msg += "🏆 Mais vendido\n"

        msg += f"\n🔗 Comprar:\n{p['link']}"

        await client.send_message(MEU_CANAL, msg)
        marcar_enviado(p["id"])
        await asyncio.sleep(3)

async def main():
    await client.start()
    print("Bot iniciado...")

    while True:
        try:
            await enviar_ofertas()
        except Exception as e:
            print("Erro:", e)

        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
