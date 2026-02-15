import asyncio, threading, os, io, requests
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def definir_tag(titulo: str) -> str:
    t = titulo.lower()
    if any(x in t for x in ["piscina", "casa", "cozinha", "mesa", "cadeira"]): return "Casa"
    if any(x in t for x in ["tv", "smart tv", "led", "monitor"]): return "Eletrônicos"
    if any(x in t for x in ["gamer", "ps5", "nintendo", "pc"]): return "Gamer"
    return "Ofertas"

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    novos = [p for p in produtos if p.get('status') == "novo"]
    for p in novos:
        try:
            tag = definir_tag(p['titulo'])
            
            # Montagem da Mensagem Detalhada
            caption = f"🔥 **{p['titulo']}**\n"
            if p.get('avaliacao'): caption += f"{p['avaliacao']}\n"
            if p.get('vendas'): caption += f"{p['vendas']}\n"
            
            if p.get('preco_antigo'):
                caption += f"\n❌ De: ~~R$ {p['preco_antigo']}~~\n"
                caption += f"✅ **Por: R$ {p['preco']}** ({p['desconto']})\n"
            else:
                caption += f"\n💰 **R$ {p['preco']}**\n"
            
            caption += f"💳 {p['parcelas']}\n"
            caption += f"\n🔗 **Compre aqui:** {p['link']}\n\n"
            caption += f"➡️ Clique aqui para ver mais parecidos ➡️ #{tag}"

            # Envio com imagem baixada para garantir exibição
            if p.get("imagem"):
                r = requests.get(p["imagem"], timeout=10)
                if r.status_code == 200:
                    foto = io.BytesIO(r.content)
                    foto.name = 'produto.jpg'
                    await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
                else:
                    await client.send_message(MEU_CANAL, caption, parse_mode='md')
            
            if not modo_teste:
                marcar_enviado(p["id"])
            await asyncio.sleep(15) # Anti-spam

        except Exception as e:
            print(f"Erro ao postar: {e}")

async def executar_ciclo(modo_teste: bool = False):
    await processar_plataforma("AMAZON", buscar_amazon(), modo_teste)
    await processar_plataforma("MERCADO LIVRE", buscar_mercado_livre(), modo_teste)

async def main():
    await client.start()
    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            print(f"Erro no loop: {e}")
        await asyncio.sleep(3600)

if __name__ == "__main__":
    # Inicia Flask (simplicado para o exemplo)
    asyncio.run(main())