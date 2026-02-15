import asyncio
import threading
import os
import random
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import (
    API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
)

from redis_client import marcar_enviado, ja_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

# --- SISTEMA DE CATEGORIAS ---
CATEGORIAS = {
    "🎮 #Gamer": ["gamer", "teclado", "mouse", "headset", "ps5", "xbox", "nintendo", "placa de vídeo", "monitor", "rtx"],
    "📱 #Eletronicos": ["smartphone", "celular", "iphone", "carregador", "fone", "bluetooth", "tablet", "notebook", "pc", "alexa"],
    "🏠 #Casa": ["cozinha", "fritadeira", "air fryer", "aspirador", "móvel", "decoração", "iluminação", "cama", "piscina", "mor"],
    "🚗 #Automotivo": ["carro", "pneu", "óleo", "automotivo", "moto", "capacete"],
    "👟 #Moda": ["tênis", "sapato", "camiseta", "calça", "roupa", "reógio"],
    "🥦 #Mercado": ["bis", "chocolate", "suplemento", "whey", "creatina", "bebida", "café", "fralda"]
}

def identificar_categoria(titulo: str) -> str:
    titulo_lower = titulo.lower()
    for cat, keywords in CATEGORIAS.items():
        if any(kw in titulo_lower for kw in keywords):
            return cat
    return "📦 #Variedades"

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(texto):
    try:
        await client.send_message(LOG_CANAL, f"📝 LOG:\n{texto}")
    except: pass

async def processar_plataforma(nome, busca_func, modo_teste=False):
    await enviar_log(f"Iniciando varredura: {nome}")
    produtos = busca_func()
    
    if not produtos:
        await enviar_log(f"⚠️ {nome}: Nenhum produto novo ou falha na captura.")
        return

    for p in produtos:
        try:
            # Dupla checagem para evitar repetição
            if ja_enviado(p['id']): continue

            categoria_full = identificar_categoria(p['titulo'])
            tag_unica = categoria_full.split(" ")[1]

            # MONTAGEM DA LEGENDA (CAPTION)
            caption = (
                f"{categoria_full}\n\n"
                f"🛍 **{p['titulo']}**\n"
                f"────────────────────\n\n"
                f"💰 **POR APENAS: R$ {p['preco']}**\n"
            )
            if p.get("tem_pix"): caption += "⚡️ *Desconto no PIX/Boleto*\n"
            
            caption += (
                f"\n🛒 **COMPRE AQUI:**\n{p['link']}\n\n"
                f"────────────────────\n"
                f"🔍 Ver mais parecidos: {tag_unica}"
            )

            # ENVIO FORMATADO
            if not modo_teste:
                if p.get("imagem"):
                    # Envia a foto COM a legenda
                    await client.send_file(MEU_CANAL, p["imagem"], caption=caption)
                else:
                    await client.send_message(MEU_CANAL, caption)
                
                marcar_enviado(p["id"])
                # Cooldown para não ser bloqueado pelo Telegram
                await asyncio.sleep(random.randint(120, 300))
            else:
                await client.send_file(LOG_CANAL, p.get("imagem"), caption=f"🧪 TESTE:\n{caption}")
                await asyncio.sleep(2)

        except Exception as e:
            await enviar_log(f"Erro em {nome}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def test_handler(event):
    await event.reply("🧪 Testando visual com fotos...")
    await processar_plataforma("AMAZON", buscar_amazon, modo_teste=True)
    await processar_plataforma("MERCADO LIVRE", buscar_mercado_livre, modo_teste=True)

async def main():
    await client.start()
    while True:
        await processar_plataforma("AMAZON", buscar_amazon)
        await processar_plataforma("MERCADO LIVRE", buscar_mercado_livre)
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route("/")
def home(): return "Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(main())