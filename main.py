import asyncio
import threading
import os
import io
import requests
import re
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Importações dos seus módulos
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, MATT_TOOL
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

# Configurações de Canais
CANAL_TESTE = "@seu_canal_de_teste" # Mude para o seu canal de testes

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# --- LÓGICA DE INTELIGÊNCIA ---

def definir_tag(titulo: str) -> str:
    t = titulo.lower()
    if any(x in t for x in ["tv", "smart", "iphone", "nintendo", "pc", "gamer", "monitor"]): return "Tecnologia"
    if any(x in t for x in ["limpeza", "casa", "cozinha", "fritadeira", "piscina", "cadeira"]): return "Casa"
    if any(x in t for x in ["shampoo", "creme", "protetor", "perfume"]): return "Beleza"
    return "Ofertas"

def calcular_score(p: dict) -> int:
    """Calcula se o produto é uma oportunidade real (0 a 100)"""
    score = 0
    
    # 1. Desconto (Prioridade Máxima)
    try:
        desc_val = int(re.search(r'\d+', p.get('desconto', '0')).group())
        if desc_val >= 40: score += 45
        elif desc_val >= 20: score += 25
    except: pass

    # 2. Avaliação Social (Filtro de Qualidade)
    try:
        nota = float(str(p.get('nota', '0')).replace(',', '.'))
        avaliacoes = int(p.get('avaliacoes', 0))
        
        if nota >= 4.5: score += 25
        elif nota >= 4.2: score += 15
        elif nota < 4.0: score -= 50 # Penaliza produtos ruins
        
        if avaliacoes > 100: score += 20
        elif avaliacoes > 50: score += 10
    except: pass

    # 3. Ticket Médio (Produtos mais caros geram mais comissão e interesse)
    try:
        preco_num = float(p['preco'].replace('.', '').replace(',', '.'))
        if preco_num > 200: score += 10
    except: pass

    return score

def gerar_copy(p: dict, plataforma: str) -> str:
    """Gera copy com gatilhos mentais e cálculos de economia"""
    tag = definir_tag(p['titulo'])
    preco_atual_str = p['preco'].replace('.', '').replace(',', '.')
    preco_atual = float(preco_atual_str)
    
    # Título e Prova Social
    copy = f"💥 **OPORTUNIDADE DE OURO DETECTADA!**\n\n"
    copy += f"🔥 **{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    
    # Lógica de Preço e Economia
    if p.get('preco_antigo'):
        try:
            preco_velho = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            economia = preco_velho - preco_atual
            if economia > 1:
                copy += f"💰 ~~R$ {p['preco_antigo']}~~\n"
                copy += f"✅ **POR APENAS: R$ {p['preco']}**\n"
                copy += f"📉 **VOCÊ ECONOMIZA: R$ {economia:.2f}** ({p['desconto']})\n"
            else:
                copy += f"✅ **PREÇO ESPECIAL: R$ {p['preco']}**\n"
        except:
            copy += f"✅ **OFERTA: R$ {p['preco']}**\n"
    else:
        copy += f"✅ **OFERTA: R$ {p['preco']}**\n"

    copy += f"\n💳 {p.get('parcelas', 'Confira parcelamento no site')}\n"
    
    # Gatilhos por plataforma
    if plataforma == "AMZ":
        copy += f"🚚 *Frete GRÁTIS para membros Prime*\n"
    else:
        copy += f"🚀 *Envio rápido garantido*\n"
        
    copy += f"⚠️ *Estoque limitado, pode subir a qualquer momento!*\n\n"
    
    # Link com UTM para rastreamento
    link_final = f"{p['link']}&utm_source=telegram&utm_campaign={tag.lower()}"
    
    copy += f"🔗 **COMPRE NO SITE OFICIAL:**\n{link_final}\n\n"
    copy += f"➡️ #{tag} #OfertaVerificada"
    
    return copy

# --- PROCESSAMENTO ---

async def processar_plataforma(nome_log: str, produtos: list[dict], modo_teste: bool = False, destino: str = MEU_CANAL):
    for p in produtos:
        # Pula se já enviado (exceto em modo teste)
        if p.get('status') == "duplicado" and not modo_teste:
            continue
            
        # Sistema de Score
        score = calcular_score(p)
        if score < 60 and not modo_teste:
            print(f"⏩ Ignorado (Score {score}): {p['titulo'][:30]}...")
            continue

        try:
            caption = gerar_copy(p, nome_log)
            
            enviado = False
            if p.get("imagem"):
                r = requests.get(p["imagem"], timeout=15)
                if r.status_code == 200:
                    foto = io.BytesIO(r.content)
                    foto.name = 'produto.jpg'
                    await client.send_file(destino, foto, caption=caption, parse_mode='md')
                    enviado = True
            
            if not enviado:
                await client.send_message(destino, caption, parse_mode='md')

            # Pós-envio
            if not modo_teste:
                marcar_enviado(p["id"])
                print(f"✅ Postado: {p['titulo'][:30]} (Score: {score})")
                await asyncio.sleep(20) # Cooldown contra flood do Telegram
            else:
                await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ Erro ao postar {p.get('id')}: {e}")

# --- COMANDOS E LOOP ---

@client.on(events.NewMessage(pattern='/testar'))
async def teste_handler(event):
    await event.respond("🚀 Iniciando varredura de teste (Score > 0)...")
    
    ml = buscar_mercado_livre("ofertas", limite=2)
    await processar_plataforma("ML", ml, modo_teste=True, destino=CANAL_TESTE)
    
    amz = buscar_amazon("eletronicos", limite=2)
    await processar_plataforma("AMZ", amz, modo_teste=True, destino=CANAL_TESTE)
    
    await event.respond(f"✅ Teste finalizado em {CANAL_TESTE}")

async def loop_principal():
    await client.start()
    print("🤖 Bot iniciado e monitorando...")
    
    while True:
        try:
            # Monitora Mercado Livre
            print("🔎 Buscando no Mercado Livre...")
            produtos_ml = buscar_mercado_livre()
            await processar_plataforma("ML", produtos_ml)
            
            await asyncio.sleep(30) # Intervalo entre lojas

            # Monitora Amazon
            print("🔎 Buscando na Amazon...")
            produtos_amz = buscar_amazon()
            await processar_plataforma("AMZ", produtos_amz)
            
        except Exception as e:
            print(f"⚠️ Erro no loop: {e}")
            
        print("😴 Ciclo finalizado. Aguardando 1 hora...")
        await asyncio.sleep(3600)

# --- WEB SERVER (HEALTH CHECK) ---

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot de Ofertas Online", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Roda o servidor web em background para o Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Inicia o loop do Telethon
    loop = asyncio.get_event_loop()
    loop.run_until_complete(loop_principal())