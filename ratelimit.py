"""
Rate Limiting Module for GIF Distributor
Provides rate limiting and abuse protection
Issue: #22
"""
import time
from typing import Dict, Optional, Tuple
from enum import Enum
from collections import deque
from dataclasses import dataclass, field


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    TOKEN_BUCKET = "token_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_window: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens are available

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait (0 if tokens available now)
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


@dataclass
class FixedWindow:
    """Fixed window rate limiter"""
    limit: int
    window_seconds: int
    count: int = 0
    window_start: float = field(default_factory=time.time)

    def consume(self, count: int = 1) -> bool:
        """
        Try to consume from the window

        Args:
            count: Number of requests to consume

        Returns:
            True if request allowed, False if limit exceeded
        """
        now = time.time()

        # Reset window if expired
        if now - self.window_start >= self.window_seconds:
            self.count = 0
            self.window_start = now

        if self.count + count <= self.limit:
            self.count += count
            return True
        return False

    def get_wait_time(self, count: int = 1) -> float:
        """
        Get time to wait until next window

        Returns:
            Seconds to wait (0 if requests available now)
        """
        now = time.time()

        # Check if window expired
        if now - self.window_start >= self.window_seconds:
            return 0.0

        if self.count + count <= self.limit:
            return 0.0

        # Wait until window resets
        return self.window_seconds - (now - self.window_start)


@dataclass
class SlidingWindow:
    """Sliding window rate limiter"""
    limit: int
    window_seconds: int
    timestamps: deque = field(default_factory=deque)

    def consume(self, count: int = 1) -> bool:
        """
        Try to consume from the sliding window

        Args:
            count: Number of requests to consume

        Returns:
            True if request allowed, False if limit exceeded
        """
        now = time.time()

        # Remove expired timestamps
        cutoff = now - self.window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

        if len(self.timestamps) + count <= self.limit:
            for _ in range(count):
                self.timestamps.append(now)
            return True
        return False

    def get_wait_time(self, count: int = 1) -> float:
        """
        Get time to wait until request can be made

        Returns:
            Seconds to wait (0 if requests available now)
        """
        now = time.time()

        # Remove expired timestamps
        cutoff = now - self.window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

        if len(self.timestamps) + count <= self.limit:
            return 0.0

        # Calculate when oldest request will expire
        if self.timestamps:
            return (self.timestamps[0] + self.window_seconds) - now
        return 0.0


class RateLimiter:
    """Main rate limiter with support for multiple strategies"""

    def __init__(
        self,
        config: RateLimitConfig,
        enable_per_ip: bool = True,
        enable_per_user: bool = True
    ):
        """
        Initialize the rate limiter

        Args:
            config: Rate limit configuration
            enable_per_ip: Enable IP-based rate limiting
            enable_per_user: Enable user-based rate limiting
        """
        self.config = config
        self.enable_per_ip = enable_per_ip
        self.enable_per_user = enable_per_user

        # Storage for rate limiters per identifier
        self._ip_limiters: Dict[str, any] = {}
        self._user_limiters: Dict[str, any] = {}

    def _create_limiter(self):
        """Create a new limiter instance based on strategy"""
        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            refill_rate = self.config.requests_per_window / self.config.window_seconds
            return TokenBucket(
                capacity=self.config.requests_per_window,
                refill_rate=refill_rate
            )
        elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return FixedWindow(
                limit=self.config.requests_per_window,
                window_seconds=self.config.window_seconds
            )
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return SlidingWindow(
                limit=self.config.requests_per_window,
                window_seconds=self.config.window_seconds
            )
        else:
            raise ValueError(f"Unknown strategy: {self.config.strategy}")

    def check_rate_limit(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        count: int = 1
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if request is allowed under rate limits

        Args:
            ip_address: IP address of the requester
            user_id: User ID of the requester
            count: Number of requests to consume (default: 1)

        Returns:
            Tuple of (allowed, retry_after_seconds)
            allowed: True if request is allowed
            retry_after_seconds: Seconds to wait if blocked, None if allowed
        """
        max_wait = 0.0

        # Check IP-based rate limit
        if self.enable_per_ip and ip_address:
            if ip_address not in self._ip_limiters:
                self._ip_limiters[ip_address] = self._create_limiter()

            limiter = self._ip_limiters[ip_address]
            if not limiter.consume(count):
                wait_time = limiter.get_wait_time(count)
                return False, wait_time
            max_wait = max(max_wait, limiter.get_wait_time(count))

        # Check user-based rate limit
        if self.enable_per_user and user_id:
            if user_id not in self._user_limiters:
                self._user_limiters[user_id] = self._create_limiter()

            limiter = self._user_limiters[user_id]
            if not limiter.consume(count):
                wait_time = limiter.get_wait_time(count)
                return False, wait_time
            max_wait = max(max_wait, limiter.get_wait_time(count))

        return True, None

    def enforce_rate_limit(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        count: int = 1
    ) -> None:
        """
        Enforce rate limit, raising exception if exceeded

        Args:
            ip_address: IP address of the requester
            user_id: User ID of the requester
            count: Number of requests to consume (default: 1)

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        allowed, retry_after = self.check_rate_limit(ip_address, user_id, count)

        if not allowed:
            raise RateLimitError(
                f"Rate limit exceeded. Retry after {retry_after:.1f} seconds."
            )

    def get_remaining_quota(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get remaining quota for IP and user

        Args:
            ip_address: IP address to check
            user_id: User ID to check

        Returns:
            Dictionary with 'ip' and 'user' remaining quotas
        """
        result = {}

        if self.enable_per_ip and ip_address:
            if ip_address in self._ip_limiters:
                limiter = self._ip_limiters[ip_address]
                if hasattr(limiter, 'tokens'):
                    limiter._refill()
                    result['ip'] = int(limiter.tokens)
                elif hasattr(limiter, 'count'):
                    result['ip'] = max(0, limiter.limit - limiter.count)
                elif hasattr(limiter, 'timestamps'):
                    now = time.time()
                    cutoff = now - limiter.window_seconds
                    valid_count = sum(1 for ts in limiter.timestamps if ts >= cutoff)
                    result['ip'] = max(0, limiter.limit - valid_count)
            else:
                result['ip'] = self.config.requests_per_window

        if self.enable_per_user and user_id:
            if user_id in self._user_limiters:
                limiter = self._user_limiters[user_id]
                if hasattr(limiter, 'tokens'):
                    limiter._refill()
                    result['user'] = int(limiter.tokens)
                elif hasattr(limiter, 'count'):
                    result['user'] = max(0, limiter.limit - limiter.count)
                elif hasattr(limiter, 'timestamps'):
                    now = time.time()
                    cutoff = now - limiter.window_seconds
                    valid_count = sum(1 for ts in limiter.timestamps if ts >= cutoff)
                    result['user'] = max(0, limiter.limit - valid_count)
            else:
                result['user'] = self.config.requests_per_window

        return result

    def reset_limits(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Reset rate limits for IP and/or user

        Args:
            ip_address: IP address to reset (None to keep)
            user_id: User ID to reset (None to keep)
        """
        if ip_address and ip_address in self._ip_limiters:
            del self._ip_limiters[ip_address]

        if user_id and user_id in self._user_limiters:
            del self._user_limiters[user_id]

    def clear_all(self) -> None:
        """Clear all rate limit data"""
        self._ip_limiters.clear()
        self._user_limiters.clear()
