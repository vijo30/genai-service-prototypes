from app import REDIS_DB, REDIS_HOST, REDIS_PORT
import redis
from rq import Worker, Queue

r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False, db=REDIS_DB)


q = Queue(connection=r)

if __name__ == '__main__':
    worker = Worker(list(q))
    worker.work()