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

# ==============================
# INICIALIZAÇÃO DO CLIENTE
# ==============================
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ==============================
# SISTEMA DE LOGS PARA TELEGRAM
# ==============================
async def enviar_log(mensagem: str):
    """Envia uma notificação para o canal de logs e imprime no terminal."""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    texto_final = f"📝 **LOG [{timestamp}]**\n\n{mensagem}"
    print(f"LOG: {mensagem}")
    try:
        if LOG_CANAL:
            await client.send_message(LOG_CANAL, texto_final)
    except Exception as e:
        print(f"Falha ao enviar log para Telegram: {e}")

# ==============================
# REGISTRO DE COMPONENTES
# ==============================
COMPONENTES = {
    "ml": {"busca": buscar_mercado_livre, "simplificado": False},
    "amazon": {"busca": buscar_amazon, "simplificado": True},
    "shopee": {"busca": buscar_shopee, "simplificado": True},
}

# ==============================
# FUNÇÃO AUXILIAR DE ENVIO
# ==============================
async def enviar_para_telegram(p: dict, destino: str, simplificado: bool):
    """Gerencia a formatação, download da imagem e envio do post."""
    try:
        caption = formatar_copy_otimizada(p, simplificado=simplificado)
        
        if p.get("imagem"):
            try:
                r = requests.get(p["imagem"], timeout=15)
                r.raise_for_status()
                foto = io.BytesIO(r.content)
                foto.name = 'post.jpg'
                await client.send_file(destino, foto, caption=caption)
            except Exception as img_err:
                await enviar_log(f"⚠️ Erro imagem em {p['titulo'][:30]}: {img_err}")
                await client.send_message(destino, caption)
        else:
            await client.send_message(destino, caption)
        return True
    except Exception as e:
        await enviar_log(f"❌ Erro crítico envio: {e}")
        return False

# ==============================
# COMANDO DE TESTE (/testar site)
# ==============================
@client.on(events.NewMessage(pattern=r'/testar(?:\s+(\w+))?'))
async def handler_teste(event):
    args = event.pattern_match.group(1)
    opcoes = list(COMPONENTES.keys())
    
    if not args or args.lower() not in COMPONENTES:
        await event.reply(f"❌ Site não encontrado.\nUse: `/testar {' ou '.join(opcoes)}`.")
        return

    site_key = args.lower()
    await event.reply(f"🔍 Buscando item de teste: **{site_key.upper()}**...")

    try:
        busca_func = COMPONENTES[site_key]["busca"]
        produtos = busca_func(limite=1)

        if not produtos:
            await event.reply(f"⚠️ `{site_key}` não retornou nada.")
            return

        p = produtos[0]
        p['titulo'] = f"🧪 [TESTE {site_key.upper()}] {p['titulo']}"
        
        is_simplificado = COMPONENTES[site_key]["simplificado"]
        await enviar_para_telegram(p, CANAL_TESTE, is_simplificado)
        await event.reply(f"✅ Teste enviado para {CANAL_TESTE}!")
        await enviar_log(f"✅ Comando /testar executado para: {site_key}")

    except Exception as e:
        await event.reply(f"💥 Erro: {str(e)}")
        await enviar_log(f"💥 Erro comando /testar {site_key}: {e}")

# ==============================
# LOOP AUTOMÁTICO DE VARREDURA
# ==============================
async def loop_bot():
    await client.start()
    await enviar_log("🚀 **Bot Iniciado com sucesso!**\nMonitorando: ML, Amazon e Shopee.")

    while True:
        for nome_site, config in COMPONENTES.items():
            await enviar_log(f"🔄 Iniciando varredura: {nome_site}")
            try:
                produtos = config["busca"]()
                novos_itens = 0

                for p in produtos:
                    if ja_enviado(p["id"]):
                        continue

                    sucesso = await enviar_para_telegram(p, MEU_CANAL, config["simplificado"])
                    
                    if sucesso:
                        marcar_enviado(p["id"])
                        novos_itens += 1
                        await asyncio.sleep(30) 

                if novos_itens > 0:
                    await enviar_log(f"✅ {novos_itens} novos itens postados da {nome_site}.")

            except Exception as e:
                await enviar_log(f"⚠️ Erro no ciclo {nome_site}: {e}")

        print("⏳ Ciclo finalizado. Dormindo 1 hora...")
        await asyncio.sleep(3600)

# ==============================
# SERVIDOR FLASK (HEALTH CHECK)
# ==============================
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is alive!", 200

# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================
async def main():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🤖 Bot desligado.")