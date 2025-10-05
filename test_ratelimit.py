"""
Tests for Rate Limiting Module
"""
import pytest
import time
from ratelimit import (
    RateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    RateLimitError,
    TokenBucket,
    FixedWindow,
    SlidingWindow
)


class TestTokenBucket:
    """Test token bucket rate limiter"""

    def test_token_bucket_init(self):
        """Test token bucket initialization"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10.0

    def test_token_bucket_consume_success(self):
        """Test successful token consumption"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.consume(5) is True
        assert bucket.tokens == 5.0

    def test_token_bucket_consume_failure(self):
        """Test token consumption when not enough tokens"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        bucket.consume(8)
        assert bucket.consume(5) is False
        assert bucket.tokens >= 2.0  # May have small refill from elapsed time

    def test_token_bucket_refill(self):
        """Test token bucket refills over time"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        bucket.consume(10)
        assert bucket.tokens == 0.0

        time.sleep(0.5)
        bucket._refill()
        assert bucket.tokens >= 4.0  # Should have refilled ~5 tokens

    def test_token_bucket_get_wait_time(self):
        """Test wait time calculation"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        bucket.consume(10)
        wait_time = bucket.get_wait_time(5)
        assert wait_time > 0
        assert wait_time <= 0.5

    def test_token_bucket_max_capacity(self):
        """Test bucket doesn't exceed capacity"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        time.sleep(2.0)
        bucket._refill()
        assert bucket.tokens <= 10.0


class TestFixedWindow:
    """Test fixed window rate limiter"""

    def test_fixed_window_init(self):
        """Test fixed window initialization"""
        window = FixedWindow(limit=10, window_seconds=60)
        assert window.limit == 10
        assert window.window_seconds == 60
        assert window.count == 0

    def test_fixed_window_consume_success(self):
        """Test successful consumption"""
        window = FixedWindow(limit=10, window_seconds=60)
        assert window.consume(5) is True
        assert window.count == 5

    def test_fixed_window_consume_failure(self):
        """Test consumption when limit exceeded"""
        window = FixedWindow(limit=10, window_seconds=60)
        window.consume(8)
        assert window.consume(5) is False
        assert window.count == 8

    def test_fixed_window_reset(self):
        """Test window resets after expiration"""
        window = FixedWindow(limit=10, window_seconds=1)
        window.consume(10)
        assert window.count == 10

        time.sleep(1.1)
        assert window.consume(5) is True
        assert window.count == 5

    def test_fixed_window_get_wait_time(self):
        """Test wait time calculation"""
        window = FixedWindow(limit=10, window_seconds=60)
        window.consume(10)
        wait_time = window.get_wait_time()
        assert wait_time > 0
        assert wait_time <= 60


class TestSlidingWindow:
    """Test sliding window rate limiter"""

    def test_sliding_window_init(self):
        """Test sliding window initialization"""
        window = SlidingWindow(limit=10, window_seconds=60)
        assert window.limit == 10
        assert window.window_seconds == 60
        assert len(window.timestamps) == 0

    def test_sliding_window_consume_success(self):
        """Test successful consumption"""
        window = SlidingWindow(limit=10, window_seconds=60)
        assert window.consume(5) is True
        assert len(window.timestamps) == 5

    def test_sliding_window_consume_failure(self):
        """Test consumption when limit exceeded"""
        window = SlidingWindow(limit=10, window_seconds=60)
        window.consume(10)
        assert window.consume(1) is False

    def test_sliding_window_expiration(self):
        """Test old requests expire"""
        window = SlidingWindow(limit=10, window_seconds=1)
        window.consume(10)
        assert len(window.timestamps) == 10

        time.sleep(1.1)
        assert window.consume(5) is True
        assert len(window.timestamps) == 5

    def test_sliding_window_get_wait_time(self):
        """Test wait time calculation"""
        window = SlidingWindow(limit=10, window_seconds=60)
        window.consume(10)
        wait_time = window.get_wait_time(1)
        assert wait_time > 0
        assert wait_time <= 60


class TestRateLimiterTokenBucket:
    """Test RateLimiter with token bucket strategy"""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization"""
        config = RateLimitConfig(
            requests_per_window=100,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)
        assert limiter.config == config

    def test_ip_based_rate_limiting(self):
        """Test IP-based rate limiting"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Should allow 10 requests
        for i in range(10):
            allowed, retry_after = limiter.check_rate_limit(ip_address="192.168.1.1")
            assert allowed is True
            assert retry_after is None

        # 11th request should be blocked
        allowed, retry_after = limiter.check_rate_limit(ip_address="192.168.1.1")
        assert allowed is False
        assert retry_after > 0

    def test_user_based_rate_limiting(self):
        """Test user-based rate limiting"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Should allow 10 requests
        for i in range(10):
            allowed, retry_after = limiter.check_rate_limit(user_id="user123")
            assert allowed is True

        # 11th request should be blocked
        allowed, retry_after = limiter.check_rate_limit(user_id="user123")
        assert allowed is False

    def test_separate_ip_and_user_limits(self):
        """Test IP and user limits are tracked separately"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Use up IP quota
        for i in range(10):
            limiter.check_rate_limit(ip_address="192.168.1.1")

        # User quota should still be available
        allowed, _ = limiter.check_rate_limit(user_id="user123")
        assert allowed is True

    def test_enforce_rate_limit_success(self):
        """Test enforce_rate_limit allows valid requests"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Should not raise exception
        limiter.enforce_rate_limit(ip_address="192.168.1.1")

    def test_enforce_rate_limit_failure(self):
        """Test enforce_rate_limit raises exception when exceeded"""
        config = RateLimitConfig(
            requests_per_window=5,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Use up quota
        for i in range(5):
            limiter.enforce_rate_limit(ip_address="192.168.1.1")

        # Should raise exception
        with pytest.raises(RateLimitError):
            limiter.enforce_rate_limit(ip_address="192.168.1.1")

    def test_get_remaining_quota(self):
        """Test getting remaining quota"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        limiter.check_rate_limit(ip_address="192.168.1.1", count=3)
        quota = limiter.get_remaining_quota(ip_address="192.168.1.1")
        assert quota['ip'] == 7

    def test_reset_limits(self):
        """Test resetting rate limits"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Use up quota
        for i in range(10):
            limiter.check_rate_limit(ip_address="192.168.1.1")

        # Reset
        limiter.reset_limits(ip_address="192.168.1.1")

        # Should be allowed again
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
        assert allowed is True

    def test_clear_all(self):
        """Test clearing all rate limits"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        limiter.check_rate_limit(ip_address="192.168.1.1")
        limiter.check_rate_limit(user_id="user123")

        limiter.clear_all()

        assert len(limiter._ip_limiters) == 0
        assert len(limiter._user_limiters) == 0


class TestRateLimiterFixedWindow:
    """Test RateLimiter with fixed window strategy"""

    def test_fixed_window_strategy(self):
        """Test fixed window strategy"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=1,
            strategy=RateLimitStrategy.FIXED_WINDOW
        )
        limiter = RateLimiter(config)

        # Use up window
        for i in range(10):
            allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
            assert allowed is True

        # Should be blocked
        allowed, retry_after = limiter.check_rate_limit(ip_address="192.168.1.1")
        assert allowed is False

        # Wait for window to reset
        time.sleep(1.1)

        # Should be allowed again
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
        assert allowed is True


class TestRateLimiterSlidingWindow:
    """Test RateLimiter with sliding window strategy"""

    def test_sliding_window_strategy(self):
        """Test sliding window strategy"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=1,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        limiter = RateLimiter(config)

        # Use up window
        for i in range(10):
            allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
            assert allowed is True

        # Should be blocked
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
        assert allowed is False

        # Wait for window to slide
        time.sleep(1.1)

        # Should be allowed again
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
        assert allowed is True


class TestRateLimiterEdgeCases:
    """Test edge cases and error handling"""

    def test_multiple_ips(self):
        """Test multiple IPs are tracked independently"""
        config = RateLimitConfig(
            requests_per_window=5,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Use up quota for IP1
        for i in range(5):
            limiter.check_rate_limit(ip_address="192.168.1.1")

        # IP2 should still have quota
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.2")
        assert allowed is True

    def test_multiple_users(self):
        """Test multiple users are tracked independently"""
        config = RateLimitConfig(
            requests_per_window=5,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Use up quota for user1
        for i in range(5):
            limiter.check_rate_limit(user_id="user1")

        # User2 should still have quota
        allowed, _ = limiter.check_rate_limit(user_id="user2")
        assert allowed is True

    def test_disable_ip_limiting(self):
        """Test disabling IP-based limiting"""
        config = RateLimitConfig(
            requests_per_window=5,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config, enable_per_ip=False)

        # Should not track IP limits
        for i in range(10):
            allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
            assert allowed is True

    def test_disable_user_limiting(self):
        """Test disabling user-based limiting"""
        config = RateLimitConfig(
            requests_per_window=5,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config, enable_per_user=False)

        # Should not track user limits
        for i in range(10):
            allowed, _ = limiter.check_rate_limit(user_id="user123")
            assert allowed is True

    def test_count_parameter(self):
        """Test consuming multiple requests at once"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Consume 5 requests at once
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1", count=5)
        assert allowed is True

        quota = limiter.get_remaining_quota(ip_address="192.168.1.1")
        assert quota['ip'] == 5

    def test_both_ip_and_user_limits(self):
        """Test both IP and user limits enforced"""
        config = RateLimitConfig(
            requests_per_window=5,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Use up IP quota
        for i in range(5):
            limiter.check_rate_limit(ip_address="192.168.1.1", user_id="user123")

        # Both IP and user should be blocked
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1", user_id="user456")
        assert allowed is False


class TestRateLimitConfig:
    """Test rate limit configuration"""

    def test_config_creation(self):
        """Test creating configuration"""
        config = RateLimitConfig(
            requests_per_window=100,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        assert config.requests_per_window == 100
        assert config.window_seconds == 60
        assert config.strategy == RateLimitStrategy.TOKEN_BUCKET

    def test_config_default_strategy(self):
        """Test default strategy is token bucket"""
        config = RateLimitConfig(
            requests_per_window=100,
            window_seconds=60
        )
        assert config.strategy == RateLimitStrategy.TOKEN_BUCKET


class TestIntegration:
    """Integration tests for real-world scenarios"""

    def test_api_rate_limiting_scenario(self):
        """Test realistic API rate limiting"""
        # 100 requests per minute
        config = RateLimitConfig(
            requests_per_window=100,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Simulate 50 API calls
        for i in range(50):
            limiter.enforce_rate_limit(
                ip_address="192.168.1.1",
                user_id="user123"
            )

        # Check remaining quota
        quota = limiter.get_remaining_quota(
            ip_address="192.168.1.1",
            user_id="user123"
        )
        assert quota['ip'] == 50
        assert quota['user'] == 50

    def test_burst_protection(self):
        """Test protection against burst traffic"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Try burst of 20 requests
        allowed_count = 0
        for i in range(20):
            allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
            if allowed:
                allowed_count += 1

        # Only 10 should be allowed
        assert allowed_count == 10

    def test_rate_limit_recovery(self):
        """Test rate limit recovers over time with token bucket"""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=1,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter(config)

        # Use up quota
        for i in range(10):
            limiter.check_rate_limit(ip_address="192.168.1.1")

        # Should be blocked
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1")
        assert allowed is False

        # Wait for partial refill
        time.sleep(0.5)

        # Should have some quota back
        allowed, _ = limiter.check_rate_limit(ip_address="192.168.1.1", count=3)
        assert allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
