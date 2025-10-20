from redis import Redis
import rq

from jobs.logging import logger
from jobs.settings import get_settings



_SETTINGS = get_settings()



worker = rq.SimpleWorker(
    ['default'],
    connection=Redis.from_url(
        str(_SETTINGS.REDIS_URL),
        # decode_responses=True, # RQ 不支援
        # protocol=3,
    ),
)



if __name__ == '__main__':
    logger.info(f'Job queue worker {worker.name} starting')
    worker.work()
