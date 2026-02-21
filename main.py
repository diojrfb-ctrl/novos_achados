import asyncio
import io
import requests
import os
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, CANAL_TESTE, LOG_CANAL
from redis_client import marcar_enviado, ja_enviado
from mercado_livre import buscar_mercado_livre
from amazon import buscar_amazon
from shopee import buscar_shopee
from formatters import formatar_copy_otimizada
from seguranca import eh_produto_seguro

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(mensagem: str):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    texto_final = f"📝 **LOG [{timestamp}]**\n\n{mensagem}"
    print(f"LOG: {mensagem}")
    try:
        if LOG_CANAL:
            await client.send_message(LOG_CANAL, texto_final)
    except Exception:
        pass

COMPONENTES = {
    "ml": {"busca": buscar_mercado_livre, "simplificado": False},
    "amazon": {"busca": buscar_amazon, "simplificado": True},
    "shopee": {"busca": buscar_shopee, "simplificado": True},
}

async def enviar_para_telegram(p: dict, destino: str, simplificado: bool):
    try:
        caption = formatar_copy_otimizada(p, simplificado=simplificado)
        if p.get("imagem"):
            r = requests.get(p["imagem"], timeout=15)
            r.raise_for_status()
            foto = io.BytesIO(r.content)
            foto.name = 'post.jpg'
            await client.send_file(destino, foto, caption=caption)
        else:
            await client.send_message(destino, caption)
        return True
    except Exception as e:
        await enviar_log(f"❌ Erro envio: {e}")
        return False

@client.on(events.NewMessage(pattern=r'/testar(?:\s+(\w+))?'))
async def handler_teste(event):
    args = event.pattern_match.group(1)
    if not args:
        await event.reply("❌ Use: `/testar shopee`, `/testar ml` ou `/testar amazon`")
        return

    site_key = args.lower()
    if site_key not in COMPONENTES:
        await event.reply(f"❌ Site `{site_key}` não cadastrado.")
        return

    await event.reply(f"🔍 Iniciando teste manual: **{site_key.upper()}**")
    try:
        busca_func = COMPONENTES[site_key]["busca"]
        produtos = busca_func(limite=3)

        if not produtos:
            await event.reply(f"⚠️ NENHUM produto retornado de {site_key}. Verifique os logs.")
            return

        for p in produtos:
            is_simplificado = COMPONENTES[site_key]["simplificado"]
            await enviar_para_telegram(p, CANAL_TESTE, is_simplificado)
            await event.reply(f"✅ Item enviado ao canal de teste!")
            break 
    except Exception as e:
        await event.reply(f"💥 Erro no teste: {e}")

async def loop_bot():
    await client.start()
    await enviar_log("🚀 Bot de Ofertas Online!")

    while True:
        for nome_site, config in COMPONENTES.items():
            try:
                # Na Shopee, rotacionamos o termo para diversificar
                termo = "ofertas" if nome_site != "shopee" else "eletronicos"
                produtos = config["busca"](termo=termo)
                
                for p in produtos:
                    if ja_enviado(p["id"]):
                        continue

                    if await enviar_para_telegram(p, MEU_CANAL, config["simplificado"]):
                        marcar_enviado(p["id"])
                        await asyncio.sleep(60) # Intervalo entre posts

            except Exception as e:
                await enviar_log(f"⚠️ Erro ciclo {nome_site}: {e}")

        await asyncio.sleep(3600) # 1 hora entre varreduras

app = Flask(__name__)
@app.route('/')
def health(): return "Bot Ativo", 200

async def main():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_bot()

if __name__ == "__main__":
    asyncio.run(main())