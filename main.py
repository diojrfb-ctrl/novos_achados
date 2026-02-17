import asyncio
import io
import requests
import os
import threading
import re
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Módulos locais
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, CANAL_TESTE
from mercado_livre import buscar_mercado_livre
from amazon import buscar_amazon
from redis_client import marcar_enviado, ja_enviado

# ==============================
# CONFIGURAÇÃO DO CLIENTE
# ==============================
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# Dicionário para gerenciar os scrapers disponíveis
# Facilita a expansão para novos sites como Shopee, Magalu, etc.
COMPONENTES = {
    "ml": buscar_mercado_livre,
    "amazon": buscar_amazon,
    # "shopee": buscar_shopee, <-- Adicione aqui após criar o arquivo
}

# ==============================
# CATEGORIZAÇÃO AUTOMÁTICA
# ==============================
def extrair_categoria_hashtag(titulo: str) -> str:
    titulo_low = titulo.lower()

    categorias = {
        "Cozinha": ["panela", "fritadeira", "airfryer", "prato", "copo", "talher", "cozinha"],
        "Games": ["ps5", "xbox", "nintendo", "jogo", "gamer", "console"],
        "Eletronicos": ["smartphone", "celular", "iphone", "televisao", "tv", "monitor", "fone"],
        "Suplementos": ["whey", "creatina", "suplemento", "vitamin", "albumina", "protein"],
        "Informatica": ["notebook", "laptop", "teclado", "mouse", "ssd", "memoria"],
        "Casa": ["toalha", "lençol", "aspirador", "iluminação", "móvel", "sofa"]
    }

    for cat, keywords in categorias.items():
        if any(kw in titulo_low for kw in keywords):
            return f" #{cat}"

    return ""

# ==============================
# FORMATAÇÃO DA COPY
# ==============================
def formatar_copy_otimizada(p: dict) -> str:
    try:
        # Limpeza de strings para conversão numérica
        preco_limpo = re.sub(r'[^\d,]', '', p['preco']).replace(',', '.')
        atual_num = float(preco_limpo)

        linha_preco_antigo = ""
        linha_desconto = ""

        if p.get('preco_antigo'):
            antigo_limpo = re.sub(r'[^\d,]', '', p['preco_antigo']).replace(',', '.')
            antigo_num = float(antigo_limpo)
            
            if antigo_num > atual_num:
                porcentagem = int((1 - (atual_num / antigo_num)) * 100)
                linha_preco_antigo = f"💰 De: R$ {p['preco_antigo']}\n"
                linha_desconto = f"📉 ({porcentagem}% de desconto)\n"

        linha_cartao = ""
        if p.get('parcelas'):
            parcela_limpa = p['parcelas'].replace("ou", "").strip()
            linha_cartao = f"💳 ou {parcela_limpa}\n"

        hashtag_cat = extrair_categoria_hashtag(p['titulo'])

        copy = f"**{p['titulo']}**\n"
        copy += f"⭐ {p['nota']} ({p['avaliacoes']} opiniões)\n"
        copy += linha_preco_antigo
        copy += f"✅ **POR: R$ {p['preco']}**\n"
        copy += linha_desconto
        copy += linha_cartao
        copy += f"📦 Frete: {p['frete']}\n"
        copy += f"🔥 Estoque: {p['estoque']}\n\n"
        copy += f"🔗 **LINK DA OFERTA:**\n"
        copy += f"{p['link']}\n\n"
        copy += f"➡️ #Ofertas{hashtag_cat}"

        return copy

    except Exception as e:
        print(f"Erro na formatação: {e}")
        return f"**{p['titulo']}**\n\n✅ POR: R$ {p['preco']}\n\n🔗 {p['link']}"

# ==============================
# COMANDO DE TESTE (/testar)
# ==============================
@client.on(events.NewMessage(pattern=r'/testar(?:\s+(\w+))?'))
async def handler_teste(event):
    # Obtém o argumento (ex: ml, amazon)
    args = event.pattern_match.group(1)
    
    if not args or args.lower() not in COMPONENTES:
        opcoes = "/".join(COMPONENTES.keys())
        await event.reply(f"❌ Comando inválido. Use: `/testar {opcoes}`")
        return

    site_key = args.lower()
    await event.reply(f"🔍 Buscando item de teste em **{site_key.upper()}**...")

    try:
        # Chama a função de busca correspondente pedindo apenas 1 item
        # No modo teste, não checamos ja_enviado para garantir que o post apareça
        busca_func = COMPONENTES[site_key]
        produtos = busca_func(limite=1)

        if not produtos:
            await event.reply(f"⚠️ Nenhum produto encontrado no scraper `{site_key}`.")
            return

        p = produtos[0]
        caption = f"🧪 **MODO TESTE: {site_key.upper()}**\n\n" + formatar_copy_otimizada(p)

        if p.get("imagem"):
            r = requests.get(p["imagem"], timeout=15)
            r.raise_for_status()
            foto = io.BytesIO(r.content)
            foto.name = 'teste.jpg'
            await client.send_file(CANAL_TESTE, foto, caption=caption)
        else:
            await client.send_message(CANAL_TESTE, caption)

        await event.reply(f"✅ Teste enviado com sucesso para {CANAL_TESTE}!")

    except Exception as e:
        await event.reply(f"💥 Erro ao testar componente: {str(e)}")

# ==============================
# LOOP AUTOMÁTICO PRINCIPAL
# ==============================
async def loop_bot():
    await client.start()
    print("🚀 Bot de Ofertas Online e aguardando comandos!")

    while True:
        for nome_site, busca_func in COMPONENTES.items():
            try:
                print(f"🔄 Iniciando varredura: {nome_site}")
                produtos = busca_func()

                for p in produtos:
                    # No loop automático, verificamos se já foi postado (Redundância)
                    if ja_enviado(p["id"]):
                        continue

                    try:
                        caption = formatar_copy_otimizada(p)

                        if p.get("imagem"):
                            try:
                                r = requests.get(p["imagem"], timeout=15)
                                r.raise_for_status()
                                foto = io.BytesIO(r.content)
                                foto.name = 'post.jpg'
                                await client.send_file(MEU_CANAL, foto, caption=caption)
                            except:
                                await client.send_message(MEU_CANAL, caption)
                        else:
                            await client.send_message(MEU_CANAL, caption)

                        marcar_enviado(p["id"])
                        print(f"✅ Enviado: {p['titulo'][:40]}...")

                        await asyncio.sleep(30) # Delay entre posts

                    except Exception as e:
                        print(f"Erro ao postar item {p.get('id')}: {e}")
                        continue

            except Exception as loop_error:
                print(f"Erro no ciclo de {nome_site}: {loop_error}")

        print("⏳ Ciclo completo. Aguardando 1 hora...")
        await asyncio.sleep(3600)

# ==============================
# SERVIDOR E EXECUÇÃO
# ==============================
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is Running", 200

async def main():
    port = int(os.environ.get("PORT", 10000))

    # Thread para o Flask (Health Check do Render/Railway)
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port),
        daemon=True
    ).start()

    # Inicia o loop do bot e mantém o cliente rodando para ouvir comandos
    await loop_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot desligado.")