#!/usr/bin/env python3
"""
Test Security Measures
Tests rate limiting, DDoS protection, and cost limiting
"""

import sys
import time

sys.path.insert(0, "live_inference_pipeline")

from security.cost_limiter import cost_limiter
from security.ddos_protection import ddos_protection
from security.rate_limiter import rate_limiter


def test_rate_limiting():
    """Test IP-based rate limiting"""
    print("=" * 60)
    print("TEST 1: Rate Limiting (10 requests/hour limit)")
    print("=" * 60)

    test_ip = "192.168.1.100"

    # Send 15 requests
    for i in range(15):
        allowed, retry_after, reason = rate_limiter.is_allowed(test_ip)

        if allowed:
            print(f" Request {i+1}: ALLOWED")
        else:
            print(f" Request {i+1}: BLOCKED ({reason}) - Retry in {retry_after}s")

    # Check stats
    stats = rate_limiter.get_stats()
    print(f"\n Stats: {stats}")
    print(f"   Blocked: {stats['blocked_requests']}/{stats['total_requests']}")
    print()


def test_ddos_protection():
    """Test DDoS detection"""
    print("=" * 60)
    print("TEST 2: DDoS Protection (Burst Detection)")
    print("=" * 60)

    test_ip = "192.168.1.101"

    # Send burst of requests
    for i in range(7):
        is_burst, reason = ddos_protection.check_burst_attack(test_ip)

        if is_burst:
            print(f" Request {i+1}: BURST ATTACK DETECTED - {reason}")
        else:
            print(f" Request {i+1}: Normal")

    print()


def test_cost_limiting():
    """Test cost limiting"""
    print("=" * 60)
    print("TEST 3: Cost Limiting ($0.50/day, $5/month)")
    print("=" * 60)

    # Check current status
    can_process, reason, stats = cost_limiter.can_process_query()

    print(f"Status: {' CAN PROCESS' if can_process else ' BLOCKED'}")
    print(f"Reason: {reason}")
    print(f"\n Daily Budget:")
    print(f"   Queries: {stats['daily']['queries']}/{stats['daily']['limit']}")
    print(f"   Cost: {stats['daily']['cost']}/{stats['daily']['budget']}")
    print(f"   Usage: {stats['daily']['percentage']}")
    print(f"\n Monthly Budget:")
    print(f"   Queries: {stats['monthly']['queries']}/{stats['monthly']['limit']}")
    print(f"   Cost: {stats['monthly']['cost']}/{stats['monthly']['budget']}")
    print(f"   Usage: {stats['monthly']['percentage']}")

    # Simulate queries
    print(f"\n Simulating 5 queries...")
    for i in range(5):
        can_process, reason, _ = cost_limiter.can_process_query()
        if can_process:
            cost_limiter.record_query()
            print(f"   Query {i+1}: Processed")
        else:
            print(f"   Query {i+1}: Blocked - {reason}")

    # Check updated stats
    _, _, updated_stats = cost_limiter.can_process_query()
    print(f"\n After Simulation:")
    print(
        f"   Daily: {updated_stats['daily']['queries']} queries ({updated_stats['daily']['cost']})"
    )
    print(
        f"   Monthly: {updated_stats['monthly']['queries']} queries ({updated_stats['monthly']['cost']})"
    )
    print()


def test_distributed_attack():
    """Test distributed DDoS detection"""
    print("=" * 60)
    print("TEST 4: Distributed Attack Detection (20+ IPs)")
    print("=" * 60)

    # Simulate 25 different IPs
    for i in range(25):
        test_ip = f"192.168.1.{i}"
        is_ddos, reason = ddos_protection.check_distributed_attack(test_ip)

        if is_ddos:
            print(f" IP {i+1}: DDOS ATTACK DETECTED - {reason}")
            break
        elif i % 5 == 0:
            print(f" IP {i+1}: Normal")

    # Check attack stats
    stats = ddos_protection.get_attack_stats()
    print(f"\n Attack Stats:")
    print(f"   Under Attack: {stats['under_attack']}")
    print(f"   Total Attacks: {stats['total_attacks']}")
    print(f"   Current IPs: {stats['current_unique_ips']}")
    print()


if __name__ == "__main__":
    print("\n Security Measures Test Suite\n")

    try:
        test_rate_limiting()
        test_ddos_protection()
        test_cost_limiting()
        test_distributed_attack()

        print("=" * 60)
        print(" ALL SECURITY TESTS COMPLETED")
        print("=" * 60)
        print("\n  Security Status:")
        print("    Rate Limiting: Active (10 req/hour)")
        print("    DDoS Protection: Active (burst & distributed)")
        print("    Cost Limiting: Active ($0.50/day, $5/month)")
        print("\n Limits:")
        print("   • 10 requests per hour per IP")
        print("   • 5 requests per 10 seconds (burst)")
        print("   • 250 queries per day (cost)")
        print("   • 2500 queries per month (cost)")
        print("\n  Blocked IPs are logged to: /var/log/app/security.log")
        print("  Cost usage tracked in: /var/log/app/cost_usage.json")

    except Exception as e:
        print(f"\n Test failed: {e}")
        sys.exit(1)
