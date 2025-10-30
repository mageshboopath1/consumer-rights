"""
DDoS Protection Layer
Detects and mitigates distributed denial of service attacks
"""

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta


class DDoSProtection:
    def __init__(self):
        """
        DDoS protection with pattern detection
        """
        # Thresholds
        self.BURST_THRESHOLD = 5  # requests in 10 seconds
        self.BURST_WINDOW = timedelta(seconds=10)

        self.DISTRIBUTED_THRESHOLD = 20  # unique IPs in 1 minute
        self.DISTRIBUTED_WINDOW = timedelta(minutes=1)

        # Tracking
        self.burst_requests = defaultdict(list)
        self.distributed_requests = []

        # Attack detection
        self.under_attack = False
        self.attack_start_time = None
        self.attack_count = 0

    def check_burst_attack(self, ip_address: str) -> tuple[bool, str]:
        """
        Detect burst attacks from single IP

        Returns:
            (is_attack: bool, reason: str)
        """
        identifier = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
        now = datetime.now()

        # Clean old requests
        self.burst_requests[identifier] = [
            req_time
            for req_time in self.burst_requests[identifier]
            if now - req_time < self.BURST_WINDOW
        ]

        # Check burst
        if len(self.burst_requests[identifier]) >= self.BURST_THRESHOLD:
            return (
                True,
                f"BURST_ATTACK: {len(self.burst_requests[identifier])} requests in {self.BURST_WINDOW.seconds}s",
            )

        # Record request
        self.burst_requests[identifier].append(now)
        return False, "OK"

    def check_distributed_attack(self, ip_address: str) -> tuple[bool, str]:
        """
        Detect distributed attacks from multiple IPs

        Returns:
            (is_attack: bool, reason: str)
        """
        identifier = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
        now = datetime.now()

        # Clean old requests
        self.distributed_requests = [
            (req_time, ip_hash)
            for req_time, ip_hash in self.distributed_requests
            if now - req_time < self.DISTRIBUTED_WINDOW
        ]

        # Add current request
        self.distributed_requests.append((now, identifier))

        # Count unique IPs
        unique_ips = len(set(ip_hash for _, ip_hash in self.distributed_requests))

        if unique_ips >= self.DISTRIBUTED_THRESHOLD:
            if not self.under_attack:
                self.under_attack = True
                self.attack_start_time = now
                self.attack_count += 1
                return (
                    True,
                    f"DDOS_ATTACK: {unique_ips} unique IPs in {self.DISTRIBUTED_WINDOW.seconds}s",
                )
        else:
            if self.under_attack:
                # Attack ended
                self.under_attack = False

        return False, "OK"

    def is_under_attack(self) -> bool:
        """Check if system is currently under attack"""
        return self.under_attack

    def get_attack_stats(self) -> dict:
        """Get attack statistics"""
        return {
            "under_attack": self.under_attack,
            "total_attacks": self.attack_count,
            "attack_start_time": (
                self.attack_start_time.isoformat() if self.attack_start_time else None
            ),
            "current_unique_ips": len(
                set(ip_hash for _, ip_hash in self.distributed_requests)
            ),
        }


# Global DDoS protection instance
ddos_protection = DDoSProtection()
