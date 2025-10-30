"""
IP-based Rate Limiter with DDoS Protection
Prevents abuse and cost explosion
"""

from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import json
import os


class RateLimiter:
    def __init__(
        self,
        max_requests=10,
        window_minutes=60,
        block_threshold=50,
        block_duration_hours=24,
    ):
        """
        Rate limiter with automatic IP blocking

        Args:
            max_requests: Max requests per window (default: 10/hour)
            window_minutes: Time window in minutes (default: 60)
            block_threshold: Requests before permanent block (default: 50)
            block_duration_hours: How long to block IPs (default: 24)
        """
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.block_threshold = block_threshold
        self.block_duration = timedelta(hours=block_duration_hours)

        # Storage
        self.requests = defaultdict(list)
        self.blocked_ips = {}  # {ip_hash: block_time}
        self.violation_count = defaultdict(int)

        # Stats
        self.total_requests = 0
        self.blocked_requests = 0
        self.unique_ips = set()

        # Load blocked IPs from file
        self._load_blocked_ips()

    def _get_identifier(self, ip_address: str) -> str:
        """Hash IP for privacy"""
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]

    def _load_blocked_ips(self):
        """Load permanently blocked IPs from file"""
        blocked_file = "/var/log/app/blocked_ips.json"
        if not os.path.exists("/var/log/app"):
            blocked_file = "/tmp/blocked_ips.json"
        if os.path.exists(blocked_file):
            try:
                with open(blocked_file, "r") as f:
                    data = json.load(f)
                    self.blocked_ips = {
                        k: datetime.fromisoformat(v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"[!] Error loading blocked IPs: {e}")

    def _save_blocked_ips(self):
        """Save blocked IPs to file"""
        blocked_file = "/var/log/app/blocked_ips.json"
        try:
            os.makedirs(os.path.dirname(blocked_file), exist_ok=True)
        except PermissionError:
            blocked_file = "/tmp/blocked_ips.json"
        try:
            data = {k: v.isoformat() for k, v in self.blocked_ips.items()}
            with open(blocked_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[!] Error saving blocked IPs: {e}")

    def is_allowed(self, ip_address: str) -> tuple[bool, int, str]:
        """
        Check if request is allowed

        Returns:
            (allowed: bool, retry_after: int, reason: str)
        """
        identifier = self._get_identifier(ip_address)
        now = datetime.now()

        self.total_requests += 1
        self.unique_ips.add(identifier)

        # Check if IP is permanently blocked
        if identifier in self.blocked_ips:
            block_time = self.blocked_ips[identifier]
            time_since_block = now - block_time

            if time_since_block < self.block_duration:
                self.blocked_requests += 1
                remaining = int(
                    (self.block_duration - time_since_block).total_seconds()
                )
                return False, remaining, "IP_BLOCKED"
            else:
                # Unblock after duration
                del self.blocked_ips[identifier]
                self.violation_count[identifier] = 0
                self._save_blocked_ips()

        # Clean old requests
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
            if now - req_time < self.window
        ]

        # Check rate limit
        current_count = len(self.requests[identifier])

        if current_count >= self.max_requests:
            self.violation_count[identifier] += 1

            # Permanent block if excessive violations
            if self.violation_count[identifier] >= self.block_threshold:
                self.blocked_ips[identifier] = now
                self._save_blocked_ips()
                self._log_security_event(
                    "IP_BLOCKED",
                    identifier,
                    f"Excessive violations: {self.violation_count[identifier]}",
                )
                return (
                    False,
                    int(self.block_duration.total_seconds()),
                    "IP_BLOCKED_PERMANENT",
                )

            # Calculate retry time
            oldest = min(self.requests[identifier])
            retry_after = int((oldest + self.window - now).total_seconds())

            self.blocked_requests += 1
            self._log_security_event(
                "RATE_LIMIT_EXCEEDED",
                identifier,
                f"Requests: {current_count}/{self.max_requests}",
            )

            return False, retry_after, "RATE_LIMIT"

        # Allow request
        self.requests[identifier].append(now)
        return True, 0, "OK"

    def _log_security_event(self, event_type: str, identifier: str, details: str):
        """Log security events"""
        log_file = "/var/log/app/security.log"
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        except PermissionError:
            log_file = "/tmp/security.log"  # Fallback to /tmp

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "ip_hash": identifier,
            "details": details,
        }

        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"[!] Error logging security event: {e}")

    def unblock_ip(self, ip_address: str) -> bool:
        """Manually unblock an IP"""
        identifier = self._get_identifier(ip_address)
        if identifier in self.blocked_ips:
            del self.blocked_ips[identifier]
            self.violation_count[identifier] = 0
            self._save_blocked_ips()
            self._log_security_event("IP_UNBLOCKED", identifier, "Manual unblock")
            return True
        return False

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        return {
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "unique_ips": len(self.unique_ips),
            "blocked_ips": len(self.blocked_ips),
            "block_rate": f"{(self.blocked_requests / max(self.total_requests, 1) * 100):.2f}%",
        }

    def get_ip_status(self, ip_address: str) -> dict:
        """Get status for specific IP"""
        identifier = self._get_identifier(ip_address)
        now = datetime.now()

        # Clean old requests
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
            if now - req_time < self.window
        ]

        status = {
            "ip_hash": identifier,
            "is_blocked": identifier in self.blocked_ips,
            "requests_in_window": len(self.requests[identifier]),
            "max_requests": self.max_requests,
            "violations": self.violation_count[identifier],
        }

        if identifier in self.blocked_ips:
            block_time = self.blocked_ips[identifier]
            time_remaining = self.block_duration - (now - block_time)
            status["block_expires_in"] = int(time_remaining.total_seconds())

        return status


# Global rate limiter instance
# 10 requests per hour, block after 50 violations for 24 hours
rate_limiter = RateLimiter(
    max_requests=10, window_minutes=60, block_threshold=50, block_duration_hours=24
)
