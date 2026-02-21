import asyncio
import io
import requests
import os
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Módulos locais
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, CANAL_TESTE, LOG_CANAL
from redis_client import marcar_enviado, ja_enviado
from mercado_livre import buscar_mercado_livre
from amazon import buscar_amazon
from shopee import buscar_shopee
from formatters import formatar_copy_otimizada

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# FUNÇÃO DE LOG MELHORADA
async def enviar_log(mensagem: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    texto_final = f"📝 **LOG [{timestamp}]**\n{mensagem}"
    print(f"LOG: {mensagem}")
    if LOG_CANAL:
        try:
            # Garante que o cliente está conectado antes de enviar
            if not client.is_connected():
                await client.connect()
            await client.send_message(LOG_CANAL, texto_final)
        except Exception as e:
            print(f"Erro ao enviar log para Telegram: {e}")

# Função para os outros arquivos usarem sem precisar de await
def disparar_log_sync(mensagem):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(enviar_log(mensagem))

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
        await event.reply("❌ Use: `/testar shopee`")
        return

    site_key = args.lower()
    if site_key not in COMPONENTES:
        await event.reply(f"❌ Site `{site_key}` não cadastrado.")
        return

    await event.reply(f"🔍 Iniciando teste manual: **{site_key.upper()}**")
    
    busca_func = COMPONENTES[site_key]["busca"]
    # Passamos o termo "celular" no teste para garantir que a API tenha o que buscar
    produtos = busca_func(termo="celular", limite=1)

    if not produtos:
        await event.reply(f"⚠️ NENHUM produto retornado. Verifique o Canal de Logs agora.")
        return

    for p in produtos:
        await enviar_para_telegram(p, CANAL_TESTE, COMPONENTES[site_key]["simplificado"])
        await event.reply(f"✅ Item enviado ao canal de teste!")

async def loop_bot():
    if not client.is_connected():
        await client.start()
    
    await enviar_log("🚀 Bot de Ofertas Online Iniciado!")

    while True:
        for nome_site, config in COMPONENTES.items():
            try:
                termo = "ofertas" if nome_site != "shopee" else "smartphone"
                produtos = config["busca"](termo=termo, limite=10)
                
                for p in produtos:
                    if ja_enviado(p["id"]): continue
                    if await enviar_para_telegram(p, MEU_CANAL, config["simplificado"]):
                        marcar_enviado(p["id"])
                        await asyncio.sleep(60)

            except Exception as e:
                await enviar_log(f"⚠️ Erro ciclo {nome_site}: {e}")

        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route('/')
def health(): return "Bot Ativo", 200

async def main():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_bot()

if __name__ == "__main__":
    asyncio.run(main())