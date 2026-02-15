import os
import asyncio
import random
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Importando seus componentes (devem estar na mesma pasta)
from database import DB
from scrapers import AmazonScraper

load_dotenv()

# --- SERVIDOR DE SAÚDE PARA O RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot de Achadinhos está online e rodando!", 200

def run_health_server():
    # O Render fornece a porta automaticamente na variável PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- LÓGICA DO BOT ---
client = TelegramClient(
    StringSession(os.getenv("STRING_SESSION")), 
    int(os.getenv("API_ID")), 
    os.getenv("API_HASH")
)

db = DB()
amazon = AmazonScraper(os.getenv("StoreID"))

async def postar_oferta(oferta):
    badge = "⭐ **PRODUTO EM ALTA**\n" if oferta.get("premium") else ""
    msg = (
        f"{badge}"
        f"🛍 **{oferta['titulo']}**\n\n"
        f"💰 **Por apenas: {oferta['preco']}**\n\n"
        f"✅ Vendido e Entregue pela Amazon\n"
        f"🚚 Frete GRÁTIS Prime\n\n"
        f"🛒 **COMPRE AQUI:** {oferta['url']}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *Preços sujeitos a alteração.*"
    )
    
    try:
        if oferta['imagem']:
            await client.send_file(os.getenv("MEU_CANAL"), file=oferta['imagem'], caption=msg)
        else:
            await client.send_message(os.getenv("MEU_CANAL"), msg)
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar para o Telegram: {e}")
        return False

async def loop_principal():
    print("🚀 Conectando ao Telegram...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ SESSÃO INVÁLIDA! Gere uma nova STRING_SESSION.")
        return

    print("✅ Bot autenticado e escaneando ofertas!")

    while True:
        try:
            print(f"🔎 Iniciando varredura na Amazon...")
            ofertas = amazon.extrair_ofertas()
            
            for oferta in ofertas:
                if not db.ja_postado("amazon", oferta['id']):
                    sucesso = await postar_oferta(oferta)
                    if sucesso:
                        db.salvar_postado("amazon", oferta['id'])
                        print(f"📢 Oferta postada: {oferta['id']}")
                        # Delay entre posts para evitar ban do Telegram
                        await asyncio.sleep(40) 

        except Exception as e:
            print(f"⚠️ Erro no loop de busca: {e}")

        # Tempo de espera entre varreduras (20 a 40 min)
        espera = random.randint(1200, 2400)
        print(f"⏳ Próxima varredura em {espera//60} minutos...")
        await asyncio.sleep(espera)

if __name__ == "__main__":
    # 1. Inicia o servidor Flask em uma thread separada (para o Render)
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # 2. Inicia o bot principal
    try:
        asyncio.run(loop_principal())
    except (KeyboardInterrupt, SystemExit):
        print("Bot desligado.")