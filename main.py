import asyncio, threading, os, io, requests
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

# Canal de Teste
CANAL_TESTE = "@canaltesteachados"

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Ofertas Online!", 200

@app.route('/health')
def health():
    return "OK", 200

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def definir_tag(titulo: str) -> str:
    t = titulo.lower()
    if any(x in t for x in ["piscina", "casa", "cozinha", "cadeira"]): return "Casa"
    if any(x in t for x in ["tv", "smart", "led", "monitor"]): return "Eletrônicos"
    if any(x in t for x in ["gamer", "ps5", "nintendo", "xbox"]): return "Gamer"
    return "Ofertas"

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False, canal_destino: str = MEU_CANAL):
    novos = produtos if modo_teste else [p for p in produtos if p.get('status') == "novo"]
    
    for p in novos:
        try:
            tag = definir_tag(p['titulo'])
            caption = f"🔥 **{p['titulo']}**\n"
            if p.get('avaliacao'): caption += f"{p['avaliacao']}\n"
            caption += f"{p['vendas']}\n\n"
            
            if p.get('preco_antigo'):
                desc = p['desconto'] if p.get('desconto') else "OFERTA"
                caption += f"💰 ~~R$ {p['preco_antigo']}~~\n"
                caption += f"✅ **R$ {p['preco']}** ({desc})\n"
            else:
                caption += f"💰 **R$ {p['preco']}**\n"
                
            caption += f"💳 {p['parcelas']}\n"
            caption += f"\n🔗 **Compre aqui:** {p['link']}\n\n"
            caption += f"➡️ Clique aqui para ver mais parecidos ➡️ #{tag}"

            enviado = False
            if p.get("imagem"):
                try:
                    r = requests.get(p["imagem"], timeout=10)
                    if r.status_code == 200:
                        foto = io.BytesIO(r.content)
                        foto.name = 'produto.jpg'
                        await client.send_file(canal_destino, foto, caption=caption, parse_mode='md')
                        enviado = True
                except: pass
            
            if not enviado:
                await client.send_message(canal_destino, caption, parse_mode='md')
            
            if not modo_teste: 
                marcar_enviado(p["id"])
                await asyncio.sleep(15)
            else:
                await asyncio.sleep(2)

        except Exception as e:
            print(f"Erro ao postar item: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def teste_handler(event):
    await event.respond("🚀 Iniciando captura de teste...")
    produtos_ml = buscar_mercado_livre("ofertas", limite=2)
    await processar_plataforma("TESTE ML", produtos_ml, modo_teste=True, canal_destino=CANAL_TESTE)
    await event.respond(f"✅ Teste concluído em {CANAL_TESTE}")

async def loop_ofertas():
    while True:
        try:
            print("🔎 Iniciando busca automática...")
            p_ml = buscar_mercado_livre()
            await processar_plataforma("ML", p_ml)
            
            p_amz = buscar_amazon()
            await processar_plataforma("AMZ", p_amz)
        except Exception as e:
            print(f"Erro no loop: {e}")
        
        print("😴 Aguardando 1 hora...")
        await asyncio.sleep(3600)

async def start_bot():
    await client.start()
    # Cria a tarefa do loop de ofertas para rodar em background
    asyncio.create_task(loop_ofertas())
    print("🤖 Bot de Telegram iniciado!")
    await client.run_until_disconnected()

def run_flask():
    # O Render fornece a porta na variável de ambiente PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Inicia o Flask em uma thread separada
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Inicia o loop do Telethon
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass