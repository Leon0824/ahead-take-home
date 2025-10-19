from redis import Redis
from rq import Queue

from app.settings import get_settings



_SETTINGS = get_settings()



queue = Queue(connection=Redis.from_url(
    str(_SETTINGS.REDIS_URL),
    # decode_responses=True, # RQ 不支援
    protocol=3,
))
