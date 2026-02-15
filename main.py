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

from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

# --- MAPEAMENTO DE CATEGORIAS ---
CATEGORIAS = {
    "🎮 #Gamer": ["gamer", "teclado", "mouse", "headset", "ps5", "xbox", "nintendo", "placa de vídeo", "monitor", "rtx"],
    "📱 #Eletronicos": ["smartphone", "celular", "iphone", "carregador", "fone", "bluetooth", "tablet", "notebook", "pc", "alexa"],
    "🏠 #Casa": ["cozinha", "fritadeira", "air fryer", "aspirador", "móvel", "decoração", "iluminação", "cama", "ventilador"],
    "🚗 #Automotivo": ["carro", "pneu", "óleo", "automotivo", "moto", "capacete", "limpeza automotiva", "suporte"],
    "👟 #Moda": ["tênis", "sapato", "camiseta", "calça", "roupa", "mochila", "relógio", "óculos", "nike", "adidas"],
    "🛠 #Ferramentas": ["furadeira", "parafusadeira", "ferramenta", "martelo", "jogo de chaves", "trena", "bosch"],
    "🧴 #Beleza": ["perfume", "creme", "shampoo", "maquiagem", "skincare", "barbeador", "secador"],
    "🥦 #Mercado": ["bis", "chocolate", "suplemento", "whey", "creatina", "bebida", "café", "limpeza", "fralda", "leite"],
    "⚽ #Esporte": ["bola", "academia", "pesos", "bicicleta", "garrafa", "esporte", "camping"]
}

def identificar_categoria(titulo: str) -> str:
    titulo_lower = titulo.lower()
    for cat, keywords in CATEGORIAS.items():
        if any(kw in titulo_lower for kw in keywords):
            return cat
    return "📦 #Variedades"

# --- CONFIGURAÇÃO DO CLIENTE ---
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except:
        print(f"Erro log: {texto}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    if not produtos:
        await enviar_log(f"❌ **{nome}**: Falha na captura de dados ou site bloqueado.")
        return

    novos = [p for p in produtos if p.get('status') == "novo"]
    await enviar_log(f"📊 **{nome}**: {len(novos)} ofertas novas encontradas.")

    for p in novos:
        try:
            categoria_full = identificar_categoria(p['titulo'])
            tag_unica = categoria_full.split(" ")[1]

            # --- CONSTRUÇÃO DO LAYOUT ---
            caption = (
                f"{categoria_full}\n\n"
                f"🛍 **{p['titulo']}**\n"
                f"────────────────────\n\n"
                f"💰 **POR APENAS: R$ {p['preco']}**\n"
            )

            if p.get("tem_pix"):
                caption += "⚡️ *Preço especial no PIX/Boleto*\n"
            if p.get("tem_cupom"):
                caption += "🎟 *Ative o cupom na página*\n"
            
            caption += (
                f"\n🔥 **CORRA! O PREÇO PODE MUDAR**\n"
                f"🛒 **COMPRE AQUI:** {p['link']}\n\n"
                f"────────────────────\n"
                f"🔍 Ver mais parecidos: {tag_unica}"
            )

            if not modo_teste:
                # Envio com foto (caption vira a legenda)
                if p.get("imagem"):
                    await client.send_file(MEU_CANAL, p["imagem"], caption=caption)
                else:
                    await client.send_message(MEU_CANAL, caption)
                
                marcar_enviado(p["id"])
                
                # Cooldown de 2 a 5 min
                delay = random.randint(120, 300)
                print(f"[LOG] Postado. Aguardando {delay}s...")
                await asyncio.sleep(delay)
            else:
                # Preview no canal de Log
                if p.get("imagem"):
                    await client.send_file(LOG_CANAL, p["imagem"], caption=f"🧪 **TESTE VISUAL**\n{caption}")
                else:
                    await enviar_log(f"🧪 **TESTE SEM FOTO**\n{caption}")
                await asyncio.sleep(5)

        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar {p.get('id')}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Iniciando varredura de teste com fotos...")
    await executar_ciclo(modo_teste=True)

async def executar_ciclo(modo_teste: bool = False):
    # Amazon
    amz = buscar_amazon()
    await processar_plataforma("AMAZON", amz, modo_teste)
    # ML
    ml = buscar_mercado_livre()
    await processar_plataforma("MERCADO LIVRE", ml, modo_teste)

async def main():
    await client.start()
    await enviar_log("✅ **Bot Online!** Fotos e Categorias ativas.")
    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            await enviar_log(f"🚨 Erro Loop: {e}")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route("/")
def home(): return "Bot Ativo"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(main())