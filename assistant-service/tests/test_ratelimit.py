from redis.exceptions import ConnectionError as RedisConnectionError

from app.ratelimit import RateLimiter


class FakeRedis:
    def __init__(self, fail=False):
        self.counts = {}
        self.expiries = {}
        self.fail = fail

    async def incr(self, key):
        if self.fail:
            raise RedisConnectionError("down")
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, seconds):
        self.expiries[key] = seconds


async def test_allows_up_to_the_per_client_limit():
    limiter = RateLimiter(FakeRedis(), per_client=2, per_kitchen=100, clock=lambda: 120.0)
    assert await limiter.allow("1.2.3.4", "k") is True
    assert await limiter.allow("1.2.3.4", "k") is True
    assert await limiter.allow("1.2.3.4", "k") is False
    assert await limiter.allow("5.6.7.8", "k") is True


async def test_kitchen_limit_applies_across_clients():
    limiter = RateLimiter(FakeRedis(), per_client=100, per_kitchen=2, clock=lambda: 0.0)
    assert await limiter.allow("a", "k") is True
    assert await limiter.allow("b", "k") is True
    assert await limiter.allow("c", "k") is False
    assert await limiter.allow("c", "other") is True


async def test_window_resets_each_minute():
    now = [0.0]
    limiter = RateLimiter(FakeRedis(), per_client=1, per_kitchen=100, clock=lambda: now[0])
    assert await limiter.allow("a", "k") is True
    assert await limiter.allow("a", "k") is False
    now[0] = 61.0
    assert await limiter.allow("a", "k") is True


async def test_keys_expire():
    redis = FakeRedis()
    await RateLimiter(redis, per_client=1, per_kitchen=1, clock=lambda: 0.0).allow("a", "k")
    assert set(redis.expiries.values()) == {60}


async def test_fails_open_when_redis_is_down():
    limiter = RateLimiter(FakeRedis(fail=True), per_client=1, per_kitchen=1)
    assert await limiter.allow("a", "k") is True
