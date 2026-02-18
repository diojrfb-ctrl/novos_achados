import asyncio
import io
import requests
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Módulos locais (Certifique-se de que os arquivos existam na mesma pasta)
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, CANAL_TESTE
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
# REGISTRO DE COMPONENTES
# ==============================
# Centraliza a configuração de cada site. 
# 'simplificado': True faz com que apareça apenas "Por apenas R$..." (Amazon/Shopee)
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
        # Chama a função de formatação do formatters.py
        caption = formatar_copy_otimizada(p, simplificado=simplificado)
        
        if p.get("imagem"):
            try:
                r = requests.get(p["imagem"], timeout=15)
                r.raise_for_status()
                foto = io.BytesIO(r.content)
                foto.name = 'post.jpg'
                await client.send_file(destino, foto, caption=caption)
            except Exception as img_err:
                print(f"Erro na imagem, enviando apenas texto: {img_err}")
                await client.send_message(destino, caption)
        else:
            await client.send_message(destino, caption)
        return True
    except Exception as e:
        print(f"Erro crítico no envio para {destino}: {e}")
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
    await event.reply(f"🔍 Buscando 1 item de teste em: **{site_key.upper()}**...")

    try:
        # Busca apenas 1 item (limite=1) para teste rápido
        busca_func = COMPONENTES[site_key]["busca"]
        produtos = busca_func(limite=1)

        if not produtos:
            await event.reply(f"⚠️ O componente `{site_key}` não retornou nenhum produto agora.")
            return

        p = produtos[0]
        # Marca visual para diferenciar no canal de teste
        p['titulo'] = f"🧪 [TESTE {site_key.upper()}] {p['titulo']}"
        
        is_simplificado = COMPONENTES[site_key]["simplificado"]
        
        # Envia para o CANAL_TESTE definido no config.py
        await enviar_para_telegram(p, CANAL_TESTE, is_simplificado)
        await event.reply(f"✅ Teste da {site_key.upper()} enviado para {CANAL_TESTE}!")

    except Exception as e:
        await event.reply(f"💥 Falha técnica no teste: {str(e)}")

# ==============================
# LOOP AUTOMÁTICO DE VARREDURA
# ==============================
async def loop_bot():
    await client.start()
    print("🚀 Bot de Ofertas Online e escutando comandos!")

    while True:
        for nome_site, config in COMPONENTES.items():
            print(f"🔄 Varrendo agora: {nome_site}")
            try:
                # Executa a função de busca do componente
                produtos = config["busca"]()

                for p in produtos:
                    # Verifica se o ID do produto já está no Redis
                    if ja_enviado(p["id"]):
                        continue

                    # Tenta enviar para o canal principal
                    sucesso = await enviar_para_telegram(p, MEU_CANAL, config["simplificado"])
                    
                    if sucesso:
                        marcar_enviado(p["id"])
                        print(f"✅ Postado: {p['titulo'][:40]}...")
                        # Delay de segurança para o Telegram não bloquear o bot (FloodWait)
                        await asyncio.sleep(30) 

            except Exception as e:
                print(f"Erro no ciclo do site {nome_site}: {e}")

        print("⏳ Varredura completa. Próximo ciclo em 1 hora.")
        await asyncio.sleep(3600) # 1 hora de intervalo

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
    # Porta para o Render ou Railway
    port = int(os.environ.get("PORT", 10000))
    
    # Inicia o Flask em uma thread separada para não bloquear o bot
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    
    # Inicia o loop do bot do Telegram
    await loop_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🤖 Bot desligado.")