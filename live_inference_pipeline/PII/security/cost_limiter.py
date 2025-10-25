"""
AWS Bedrock Cost Limiter
Prevents cost explosion by tracking and limiting API usage
"""

from datetime import datetime, timedelta
import json
import os

class CostLimiter:
    def __init__(self, 
                 daily_budget_usd=0.50,
                 monthly_budget_usd=5.00,
                 cost_per_query=0.002):
        """
        Cost limiter for AWS Bedrock
        
        Args:
            daily_budget_usd: Maximum daily spend (default: $0.50)
            monthly_budget_usd: Maximum monthly spend (default: $5.00)
            cost_per_query: Estimated cost per query (default: $0.002)
        """
        self.daily_budget = daily_budget_usd
        self.monthly_budget = monthly_budget_usd
        self.cost_per_query = cost_per_query
        
        # Tracking
        self.daily_queries = []
        self.monthly_queries = []
        
        # Limits
        self.daily_query_limit = int(daily_budget_usd / cost_per_query)
        self.monthly_query_limit = int(monthly_budget_usd / cost_per_query)
        
        # Load saved data
        self._load_usage_data()
        
        print(f"[i] Cost Limiter Initialized:")
        print(f"    Daily Budget: ${daily_budget_usd} ({self.daily_query_limit} queries)")
        print(f"    Monthly Budget: ${monthly_budget_usd} ({self.monthly_query_limit} queries)")
        print(f"    Cost per Query: ${cost_per_query}")
    
    def _load_usage_data(self):
        """Load usage data from file"""
        usage_file = '/var/log/app/cost_usage.json'
        if not os.path.exists('/var/log/app'):
            usage_file = '/tmp/cost_usage.json'
        if os.path.exists(usage_file):
            try:
                with open(usage_file, 'r') as f:
                    data = json.load(f)
                    self.daily_queries = [
                        datetime.fromisoformat(ts) for ts in data.get('daily', [])
                    ]
                    self.monthly_queries = [
                        datetime.fromisoformat(ts) for ts in data.get('monthly', [])
                    ]
            except Exception as e:
                print(f"[!] Error loading usage data: {e}")
    
    def _save_usage_data(self):
        """Save usage data to file"""
        usage_file = '/var/log/app/cost_usage.json'
        try:
            os.makedirs(os.path.dirname(usage_file), exist_ok=True)
        except PermissionError:
            usage_file = '/tmp/cost_usage.json'
        
        try:
            data = {
                'daily': [ts.isoformat() for ts in self.daily_queries],
                'monthly': [ts.isoformat() for ts in self.monthly_queries],
                'last_updated': datetime.now().isoformat()
            }
            with open(usage_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[!] Error saving usage data: {e}")
    
    def can_process_query(self) -> tuple[bool, str, dict]:
        """
        Check if query can be processed within budget
        
        Returns:
            (allowed: bool, reason: str, stats: dict)
        """
        now = datetime.now()
        
        # Clean old data
        self._clean_old_data(now)
        
        # Check daily limit
        daily_count = len(self.daily_queries)
        daily_cost = daily_count * self.cost_per_query
        
        if daily_count >= self.daily_query_limit:
            stats = self._get_stats()
            return False, f"DAILY_BUDGET_EXCEEDED: ${daily_cost:.2f}/${self.daily_budget}", stats
        
        # Check monthly limit
        monthly_count = len(self.monthly_queries)
        monthly_cost = monthly_count * self.cost_per_query
        
        if monthly_count >= self.monthly_query_limit:
            stats = self._get_stats()
            return False, f"MONTHLY_BUDGET_EXCEEDED: ${monthly_cost:.2f}/${self.monthly_budget}", stats
        
        # Check if approaching limits (80% threshold)
        if daily_count >= self.daily_query_limit * 0.8:
            print(f"[⚠️] WARNING: 80% of daily budget used ({daily_count}/{self.daily_query_limit} queries)")
        
        if monthly_count >= self.monthly_query_limit * 0.8:
            print(f"[⚠️] WARNING: 80% of monthly budget used ({monthly_count}/{self.monthly_query_limit} queries)")
        
        stats = self._get_stats()
        return True, "OK", stats
    
    def record_query(self):
        """Record a query for cost tracking"""
        now = datetime.now()
        self.daily_queries.append(now)
        self.monthly_queries.append(now)
        self._save_usage_data()
    
    def _clean_old_data(self, now: datetime):
        """Remove old query records"""
        # Keep last 24 hours for daily
        day_ago = now - timedelta(days=1)
        self.daily_queries = [
            ts for ts in self.daily_queries if ts > day_ago
        ]
        
        # Keep last 30 days for monthly
        month_ago = now - timedelta(days=30)
        self.monthly_queries = [
            ts for ts in self.monthly_queries if ts > month_ago
        ]
    
    def _get_stats(self) -> dict:
        """Get current usage statistics"""
        daily_count = len(self.daily_queries)
        monthly_count = len(self.monthly_queries)
        
        daily_cost = daily_count * self.cost_per_query
        monthly_cost = monthly_count * self.cost_per_query
        
        return {
            'daily': {
                'queries': daily_count,
                'limit': self.daily_query_limit,
                'cost': f"${daily_cost:.3f}",
                'budget': f"${self.daily_budget:.2f}",
                'percentage': f"{(daily_count / self.daily_query_limit * 100):.1f}%"
            },
            'monthly': {
                'queries': monthly_count,
                'limit': self.monthly_query_limit,
                'cost': f"${monthly_cost:.2f}",
                'budget': f"${self.monthly_budget:.2f}",
                'percentage': f"{(monthly_count / self.monthly_query_limit * 100):.1f}%"
            }
        }
    
    def get_stats(self) -> dict:
        """Get current usage statistics"""
        now = datetime.now()
        self._clean_old_data(now)
        return self._get_stats()
    
    def reset_daily(self):
        """Reset daily counter (for testing)"""
        self.daily_queries = []
        self._save_usage_data()
    
    def reset_monthly(self):
        """Reset monthly counter (for testing)"""
        self.monthly_queries = []
        self._save_usage_data()

# Global cost limiter instance
# $0.50/day, $5/month, $0.002 per query
cost_limiter = CostLimiter(
    daily_budget_usd=0.50,
    monthly_budget_usd=5.00,
    cost_per_query=0.002
)
