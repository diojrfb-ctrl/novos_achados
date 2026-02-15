from upstash_redis import Redis
from config import UPSTASH_URL, UPSTASH_TOKEN

redis_client = Redis(
    url=UPSTASH_URL,
    token=UPSTASH_TOKEN
)

def ja_enviado(prod_id):
    return redis_client.sismember("produtos_enviados", prod_id)

def marcar_enviado(prod_id):
    redis_client.sadd("produtos_enviados", prod_id)
