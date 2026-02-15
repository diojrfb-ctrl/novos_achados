import asyncio, threading, os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask

from config import *
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def definir_tag(titulo: str) -> str:
    t = titulo.lower()
    if any(x in t for x in ["iphone", "celular", "samsung", "xiaomi"]): return "Smartphone"
    if any(x in t for x in ["gamer", "mouse", "teclado", "placa"]): return "Gamer"
    if any(x in t for x in ["cerveja", "vinho", "whisky", "bis", "chocolate"]): return "Mercado"
    if any(x in t for x in ["piscina", "cadeira", "mesa", "limpeza", "fritadeira"]): return "Casa"
    return "Ofertas"

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    novos = [p for p in produtos if p.get('status') == "novo"]
    
    # Log de relatório no canal de logs
    await client.send_message(LOG_CANAL, f"📊 **RELATÓRIO {nome}:** {len(novos)} novos encontrados.")

    for p in novos:
        tag = definir_tag(p['titulo'])
        
        # Montagem da Mensagem
        caption = (
            f"🔥 **{p['titulo']}**\n\n"
            f"💰 **R$ {p['preco']}**\n"
            f"💳 {p['parcelas']}\n"
        )
        if p['tem_pix']: caption += "⚡️ Desconto especial no PIX!\n"
        
        caption += f"\n🔗 **Compre aqui:** {p['link']}\n\n"
        caption += f"➡️ Ver mais parecidos: #{tag}"

        try:
            # Envia com FOTO
            if p['imagem']:
                await client.send_file(MEU_CANAL, p['imagem'], caption=caption)
            else:
                await client.send_message(MEU_CANAL, caption)
            
            marcar_enviado(p["id"])
            
            # INTERVALO DE 10 SEGUNDOS para não bombardear o usuário
            await asyncio.sleep(10) 
            
        except Exception as e:
            print(f"Erro ao postar: {e}")

async def executar_ciclo(modo_teste=False):
    await processar_plataforma("AMAZON", buscar_amazon(), modo_teste)
    await processar_plataforma("MERCADO LIVRE", buscar_mercado_livre(), modo_teste)

async def main():
    await client.start()
    while True:
        await executar_ciclo()
        await asyncio.sleep(3600) # 1 hora entre varreduras

# Servidor Flask para o Render
app = Flask(__name__)
@app.route("/")
def h(): return "Bot ON"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(main())