import os
from dotenv import load_dotenv

# Carrega o .env apenas para desenvolvimento local
load_dotenv()

# --- CONFIGURAÇÕES DO TELEGRAM ---
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")
MEU_CANAL = os.getenv("MEU_CANAL", "")
CANAL_TESTE = os.getenv("CANAL_TESTE", "@canaltesteachados")
LOG_CANAL = os.getenv("LOG_CANAL", "")

# --- CONFIGURAÇÕES SHOPEE (API OFICIAL) ---
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_SECRET = os.getenv("SHOPEE_SECRET")
SHOPEE_URL = "https://open-api.affiliate.shopee.com.br/graphql"

# --- CONFIGURAÇÕES AMAZON ---
AMAZON_TAG = os.getenv("AMAZON_TAG", "suatag-20")

# --- BANCO DE DADOS (REDIS/UPSTASH) ---
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

# Headers genéricos para scrapers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}