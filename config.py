import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")
MEU_CANAL = os.getenv("MEU_CANAL")

AMAZON_TAG = os.getenv("StoreID")
MATT_TOOL = "74449748"

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
