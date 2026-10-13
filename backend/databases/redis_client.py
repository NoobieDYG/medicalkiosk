import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

# Fail fast when a local Redis service is absent. The triage session layer
# provides a development fallback instead of letting a patient request hang.
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
    retry=Retry(NoBackoff(), 0),
    retry_on_error=[],
)

