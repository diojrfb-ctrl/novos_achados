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
COMPONENTES = {
    "ml": buscar_mercado_livre,
    "amazon": buscar_amazon,
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
def formatar_copy_otimizada(p: dict, simplificado: bool = False) -> str:
    try:
        hashtag_cat = extrair_categoria_hashtag(p['titulo'])
        
        # Início da Copy
        copy = f"**{p['titulo']}**\n"
        copy += f"⭐ {p['nota']} ({p['avaliacoes']} opiniões)\n"

        if simplificado:
            # Layout simplificado para Amazon conforme solicitado
            copy += f"✅ **Por apenas R$ {p['preco']}**\n"
        else:
            # Layout completo (Mercado Livre e outros)
            preco_limpo = re.sub(r'[^\d,]', '', p['preco']).replace(',', '.')
            atual_num = float(preco_limpo)

            if p.get('preco_antigo'):
                antigo_limpo = re.sub(r'[^\d,]', '', p['preco_antigo']).replace(',', '.')
                antigo_num = float(antigo_limpo)
                
                if antigo_num > atual_num:
                    porcentagem = int((1 - (atual_num / antigo_num)) * 100)
                    copy += f"💰 De: R$ {p['preco_antigo']}\n"
                    copy += f"📉 ({porcentagem}% de desconto)\n"

            copy += f"✅ **POR: R$ {p['preco']}**\n"

        # Informações complementares comuns
        linha_cartao = f"💳 ou {p['parcelas'].replace('ou', '').strip()}\n" if p.get('parcelas') else ""
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
    args = event.pattern_match.group(1)
    
    if not args or args.lower() not in COMPONENTES:
        opcoes = "/".join(COMPONENTES.keys())
        await event.reply(f"❌ Use: `/testar {opcoes}`")
        return

    site_key = args.lower()
    await event.reply(f"🔍 Testando componente: **{site_key.upper()}**...")

    try:
        busca_func = COMPONENTES[site_key]
        produtos = busca_func(limite=1)

        if not produtos:
            await event.reply(f"⚠️ Nenhum produto encontrado em `{site_key}`.")
            return

        p = produtos[0]
        # Aplica simplificação se for Amazon
        is_amazon = (site_key == "amazon")
        caption = f"🧪 **MODO TESTE: {site_key.upper()}**\n\n" + formatar_copy_otimizada(p, simplificado=is_amazon)

        if p.get("imagem"):
            r = requests.get(p["imagem"], timeout=15)
            foto = io.BytesIO(r.content)
            foto.name = 'teste.jpg'
            await client.send_file(CANAL_TESTE, foto, caption=caption)
        else:
            await client.send_message(CANAL_TESTE, caption)

        await event.reply(f"✅ Enviado para {CANAL_TESTE}")

    except Exception as e:
        await event.reply(f"💥 Erro: {str(e)}")

# ==============================
# LOOP AUTOMÁTICO PRINCIPAL
# ==============================
async def loop_bot():
    await client.start()
    print("🚀 Bot Online!")

    while True:
        for nome_site, busca_func in COMPONENTES.items():
            try:
                produtos = busca_func()
                is_amazon = (nome_site == "amazon")

                for p in produtos:
                    if ja_enviado(p["id"]):
                        continue

                    try:
                        caption = formatar_copy_otimizada(p, simplificado=is_amazon)

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
                        await asyncio.sleep(30) 

                    except Exception as e:
                        continue

            except Exception as loop_error:
                print(f"Erro em {nome_site}: {loop_error}")

        await asyncio.sleep(3600)

# ==============================
# SERVIDOR E EXECUÇÃO
# ==============================
app = Flask(__name__)

@app.route('/')
def health():
    return "OK", 200

async def main():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_bot()

if __name__ == "__main__":
    asyncio.run(main())