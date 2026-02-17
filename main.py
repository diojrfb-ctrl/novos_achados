import asyncio, io, requests, os, threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession

# Importações dos seus módulos locais
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre
from redis_client import marcar_enviado

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def extrair_categoria_hashtag(titulo: str) -> str:
    """Extrai uma hashtag de categoria baseada em palavras-chave no título."""
    titulo_low = titulo.lower()
    categorias = {
        "Cozinha": ["panela", "fritadeira", "airfryer", "prato", "copo", "talher", "cozinha"],
        "Games": ["ps5", "xbox", "nintendo", "jogo", "gamer", "placa de vídeo", "console"],
        "Eletronicos": ["smartphone", "celular", "iphone", "televisao", "tv", "monitor", "fone"],
        "Suplementos": ["whey", "creatina", "suplemento", "vitamin", "albumina"],
        "Informatica": ["notebook", "laptop", "teclado", "mouse", "ssd", "memoria"],
        "Casa": ["toalha", "lençol", "aspirador", "iluminação", "móvel", "sofa"]
    }
    
    for cat, keywords in categorias.items():
        if any(kw in titulo_low for kw in keywords):
            return f" #{cat}"
    return "" # Retorna vazio se não identificar

def formatar_copy_otimizada(p: dict) -> str:
    """Formata a mensagem seguindo o template sugerido com lógica condicional."""
    try:
        # 1. Tratamento de Preços e Desconto
        atual_num = float(p['preco'].replace('.', '').replace(',', '.'))
        linha_preco_antigo = ""
        linha_desconto = ""

        if p.get('preco_antigo'):
            antigo_num = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            if antigo_num > atual_num:
                porcentagem = int((1 - (atual_num / antigo_num)) * 100)
                linha_preco_antigo = f"💰 De: ~~R$ {p['preco_antigo']}~~\n"
                linha_desconto = f"📉 ({porcentagem}% de desconto no Pix)\n"

        # 2. Extração de Categoria para Hashtag
        hashtag_cat = extrair_categoria_hashtag(p['titulo'])

        # 3. Construção do Template conforme sugestão
        copy = f"**{p['titulo']}**\n"
        copy += f"⭐ {p['nota']} ({p['avaliacoes']} opiniões)\n"
        copy += linha_preco_antigo  # Só aparece se houver preço antigo válido
        copy += f"✅ **POR: R$ {p['preco']}**\n"
        copy += linha_desconto      # Só aparece se houver cálculo de desconto
        copy += f"📦 Entrega: {p['frete']}\n"  # Espaço corrigido aqui
        copy += f"🔥 Estoque: {p['estoque']}\n\n"
        copy += f"🔗 **LINK DA OFERTA:**\n"
        copy += f"{p['link']}\n\n"
        copy += f"➡️ #Ofertas #MercadoLivre{hashtag_cat}"
        
        return copy
    except Exception as e:
        print(f"Erro na formatação: {e}")
        return f"**{p['titulo']}**\n\n✅ **POR: R$ {p['preco']}**\n\n🔗 {p['link']}"

async def loop_bot():
    """Ciclo de busca e postagem no Telegram."""
    await client.start()
    print("Robô de Ofertas Iniciado!")
    
    while True:
        # Busca produtos (mercado_livre.py já deve filtrar 'ja_enviado')
        produtos = buscar_mercado_livre()
        
        for p in produtos:
            try:
                caption = formatar_copy_otimizada(p)
                
                if p.get("imagem"):
                    # Download seguro da imagem
                    r = requests.get(p["imagem"], timeout=15)
                    r.raise_for_status()
                    
                    foto = io.BytesIO(r.content)
                    foto.name = 'oferta.jpg'
                    
                    # Envio para o canal
                    await client.send_file(
                        MEU_CANAL, 
                        foto, 
                        caption=caption, 
                        parse_mode='md'
                    )
                    
                    # Marca no Redis para evitar repetição
                    marcar_enviado(p["id"])
                    
                    # Delay entre posts para evitar detecção de spam
                    await asyncio.sleep(30)
                    
            except Exception as e:
                print(f"Erro ao processar item {p.get('id')}: {e}")
                continue
        
        print("Ciclo finalizado. Aguardando 1 hora...")
        await asyncio.sleep(3600)

# Configuração de Health Check (para Render/Heroku)
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot Online", 200

async def main():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port), 
        daemon=True
    ).start()
    await loop_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot encerrado manualmente.")