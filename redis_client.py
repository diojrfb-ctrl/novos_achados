import redis
from config import UPSTASH_URL, UPSTASH_TOKEN

redis_client = redis.Redis(
    host=UPSTASH_URL.replace("https://", "").replace("http://", ""),
    password=UPSTASH_TOKEN,
    port=6379,
    ssl=True
)

def ja_enviado(prod_id):
    return redis_client.sismember("produtos_enviados", prod_id)

def marcar_enviado(prod_id):
    redis_client.sadd("produtos_enviados", prod_id)
