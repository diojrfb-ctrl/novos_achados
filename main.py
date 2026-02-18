import asyncio
import io
import requests
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Módulos locais
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, CANAL_TESTE
from redis_client import marcar_enviado, ja_enviado
from mercado_livre import buscar_mercado_livre
from amazon import buscar_amazon
from formatters import formatar_copy_otimizada

# Inicialização do Cliente
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ==============================
# REGISTRO DE COMPONENTES
# ==============================
# Sempre que criar um site novo, basta adicionar aqui.
COMPONENTES = {
    "ml": {"busca": buscar_mercado_livre, "simplificado": False},
    "amazon": {"busca": buscar_amazon, "simplificado": True},
}

async def enviar_para_telegram(p: dict, destino: str, simplificado: bool):
    """Gerencia o download da imagem e envio do post."""
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
        print(f"Erro no envio para {destino}: {e}")
        return False

# ==============================
# COMANDO DE TESTE (/testar site)
# ==============================
@client.on(events.NewMessage(pattern=r'/testar(?:\s+(\w+))?'))
async def handler_teste(event):
    args = event.pattern_match.group(1)
    opcoes = list(COMPONENTES.keys())
    
    if not args or args.lower() not in COMPONENTES:
        await event.reply(f"❌ Site não encontrado. Use: `/testar {' ou '.join(opcoes)}`.")
        return

    site_key = args.lower()
    await event.reply(f"🔍 Testando **{site_key.upper()}** no canal de testes...")

    try:
        # Busca apenas 1 item para validação
        busca_func = COMPONENTES[site_key]["busca"]
        produtos = busca_func(limite=1)

        if not produtos:
            await event.reply(f"⚠️ O componente `{site_key}` não retornou nenhum item agora.")
            return

        p = produtos[0]
        # Adiciona prefixo para saber que é teste
        p['titulo'] = f"🧪 [TESTE] {p['titulo']}"
        
        is_simplificado = COMPONENTES[site_key]["simplificado"]
        await enviar_para_telegram(p, CANAL_TESTE, is_simplificado)
        await event.reply(f"✅ Enviado para {CANAL_TESTE}!")

    except Exception as e:
        await event.reply(f"💥 Falha técnica no teste: {str(e)}")

# ==============================
# LOOP AUTOMÁTICO
# ==============================
async def loop_bot():
    await client.start()
    print("🚀 Bot de Ofertas Online e escutando comandos!")

    while True:
        for nome_site, config in COMPONENTES.items():
            print(f"🔄 Varrendo: {nome_site}")
            try:
                produtos = config["busca"]()

                for p in produtos:
                    if ja_enviado(p["id"]):
                        continue

                    sucesso = await enviar_para_telegram(p, MEU_CANAL, config["simplificado"])
                    
                    if sucesso:
                        marcar_enviado(p["id"])
                        await asyncio.sleep(30) # Delay para não ser banido pelo Telegram

            except Exception as e:
                print(f"Erro no ciclo {nome_site}: {e}")

        print("⏳ Ciclo finalizado. Aguardando 1 hora...")
        await asyncio.sleep(3600)

# ==============================
# SERVIDOR DE SAÚDE E EXECUÇÃO
# ==============================
app = Flask(__name__)

@app.route('/')
def health(): return "Bot Running", 200

async def main():
    port = int(os.environ.get("PORT", 10000))
    # Flask em thread separada para não travar o loop do bot
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_bot()

if __name__ == "__main__":
    asyncio.run(main())