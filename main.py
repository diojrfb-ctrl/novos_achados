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

# --- SISTEMA DE CATEGORIAS ---
CATEGORIAS = {
    "🎮 #Gamer": ["gamer", "teclado", "mouse", "headset", "ps5", "xbox", "nintendo", "placa de vídeo", "monitor", "rtx", "jogo"],
    "📱 #Eletronicos": ["smartphone", "celular", "iphone", "carregador", "fone", "bluetooth", "tablet", "notebook", "pc", "alexa", "xiaomi"],
    "🏠 #Casa": ["cozinha", "fritadeira", "air fryer", "aspirador", "móvel", "decoração", "iluminação", "cama", "ventilador", "maquina de lavar"],
    "🚗 #Automotivo": ["carro", "pneu", "óleo", "automotivo", "moto", "capacete", "limpeza automotiva", "suporte"],
    "👟 #Moda": ["tênis", "sapato", "camiseta", "calça", "roupa", "mochila", "relógio", "óculos", "nike", "adidas"],
    "🛠 #Ferramentas": ["furadeira", "parafusadeira", "ferramenta", "martelo", "jogo de chaves", "trena", "bosch", "dewalt"],
    "🧴 #Beleza": ["perfume", "creme", "shampoo", "maquiagem", "skincare", "barbeador", "secador", "chapinha"],
    "🥦 #Mercado": ["bis", "chocolate", "suplemento", "whey", "creatina", "bebida", "café", "limpeza", "fralda", "leite", "growth"],
    "⚽ #Esporte": ["bola", "academia", "pesos", "bicicleta", "garrafa", "esporte", "camping", "chuteira"]
}

def identificar_categoria(titulo: str) -> str:
    titulo_lower = titulo.lower()
    for cat, keywords in CATEGORIAS.items():
        if any(kw in titulo_lower for kw in keywords):
            return cat
    return "📦 #Variedades"

# --- CLIENTE TELEGRAM ---
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro ao enviar log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    if not produtos:
        # Se falhou, avisamos no log mas o bot continua tentando no próximo ciclo
        if nome == "AMAZON":
            await enviar_log(f"⚠️ **{nome}**: Captura falhou (Provável bloqueio de IP).")
        return

    novos = [p for p in produtos if p.get('status') == "novo"]
    
    # Relatório técnico no Log
    await enviar_log(f"📊 **{nome}**: {len(novos)} novas ofertas.")

    for p in novos:
        try:
            categoria_full = identificar_categoria(p['titulo'])
            tag_unica = categoria_full.split(" ")[1]

            # Montagem do Caption (Legenda da Imagem)
            caption = (
                f"{categoria_full}\n\n"
                f"🛍 **{p['titulo']}**\n"
                f"────────────────────\n\n"
                f"💰 **POR APENAS: R$ {p['preco']}**\n"
            )

            if p.get("tem_pix"):
                caption += "⚡️ *Preço especial no PIX/Boleto*\n"
            
            caption += (
                f"\n🔥 **CORRA! O PREÇO PODE MUDAR**\n"
                f"🛒 **COMPRE AQUI:** {p['link']}\n\n"
                f"────────────────────\n"
                f"🔍 Ver mais parecidos: {tag_unica}"
            )

            if not modo_teste:
                # Envio Real para o Canal
                if p.get("imagem"):
                    await client.send_file(MEU_CANAL, p["imagem"], caption=caption)
                else:
                    await client.send_message(MEU_CANAL, caption)
                
                marcar_enviado(p["id"])
                
                # Cooldown Humano: entre 2 e 5 minutos
                atraso = random.randint(120, 300)
                print(f"[LOG] {nome} postado. Pausando {atraso}s...")
                await asyncio.sleep(atraso)
            else:
                # No teste, mandamos para o canal de LOG para você conferir
                if p.get("imagem"):
                    await client.send_file(LOG_CANAL, p["imagem"], caption=f"🧪 **TESTE VISUAL**\n{caption}")
                else:
                    await enviar_log(f"🧪 **TESTE (SEM FOTO)**\n{caption}")
                await asyncio.sleep(2)

        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar item {p.get('id')}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Iniciando varredura de teste...")
    await executar_ciclo(modo_teste=True)

async def executar_ciclo(modo_teste: bool = False):
    # Executa Amazon e depois Mercado Livre
    await processar_plataforma("AMAZON", buscar_amazon(), modo_teste)
    await processar_plataforma("MERCADO LIVRE", buscar_mercado_livre(), modo_teste)

async def main():
    await client.start()
    await enviar_log("✅ **Bot Online!** Categorias, Fotos e Anti-Spam configurados.")
    
    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            await enviar_log(f"🚨 Erro no ciclo: {e}")
        
        # Espera 1 hora para a próxima varredura geral
        await asyncio.sleep(3600)

# Servidor Flask para o Render não desligar o bot
app = Flask(__name__)
@app.route("/")
def home(): return "Bot de Ofertas Online"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    asyncio.run(main())