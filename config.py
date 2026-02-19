import os
from dotenv import load_dotenv

# Carrega o arquivo .env se estiver rodando localmente
load_dotenv()

# --- CONFIGURAÇÕES DO TELEGRAM ---
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")

# Canais e Grupos
MEU_CANAL = os.getenv("MEU_CANAL", "")
CANAL_TESTE = "@canaltesteachados"
LOG_CANAL = os.getenv("LOG_CANAL", "")

# --- CONFIGURAÇÕES SHOPEE (API OFICIAL) ---
# Substitua ou configure no painel do Render/Arquivo .env
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID", "18339480979")
SHOPEE_SECRET = os.getenv("SHOPEE_SECRET", "U6L3QKS2WLMAYKK67OCNGSQ65NIROVMV")
SHOPEE_AFFILIATE_ID = "18339480979"
SHOPEE_URL = "https://open-api.affiliate.shopee.com.br/graphql"

# --- CONFIGURAÇÕES AMAZON ---
AMAZON_TAG = os.getenv("StoreID", "") # Sua Tag de Associado

# --- OUTRAS FERRAMENTAS ---
MATT_TOOL = "74449748"

# --- BANCO DE DADOS (REDIS/UPSTASH) ---
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

# --- HEADERS GERAIS (Para outros scrapers se necessário) ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com.br/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1"
}

# --- LOG DE INICIALIZAÇÃO (Opcional) ---
if not SHOPEE_APP_ID or not SHOPEE_SECRET:
    print("⚠️  AVISO: Credenciais da Shopee não encontradas nas variáveis de ambiente.")