"""
Locust Load Testing for Corgi Recommender Service

This file defines user behaviors and load patterns for stress testing
the recommendation API endpoints using the Locust framework.

Usage:
    # Web UI mode
    locust -f tests/locustfile_recommendations.py --host http://localhost:5002
    
    # Headless mode
    locust -f tests/locustfile_recommendations.py --headless --users 100 --spawn-rate 10 --run-time 30m --host http://localhost:5002
"""

from locust import HttpUser, task, between, events, TaskSet
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import random
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os

# Setup logging
setup_logging("INFO", None)
logger = logging.getLogger(__name__)

# Test data pools
TEST_USER_POOL_SIZE = 10000
TEST_POST_POOL_SIZE = 50000
INTERACTION_TYPES = ["like", "share", "comment", "click", "view", "bookmark"]
TIMELINE_TYPES = ["home", "local", "public"]

class CorgiTaskSet(TaskSet):
    """Task set defining user behavior patterns"""
    
    def on_start(self):
        """Initialize user session"""
        self.user_id = f"stress_user_{random.randint(1, TEST_USER_POOL_SIZE)}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer test_token_{self.user_id}",
            "User-Agent": "Locust/CorgiStressTest"
        }
        self.followed_users = [
            f"stress_user_{random.randint(1, TEST_USER_POOL_SIZE)}" 
            for _ in range(random.randint(50, 200))
        ]
        logger.info(f"User {self.user_id} started session")
        
    @task(40)
    def get_recommendations(self):
        """Get personalized recommendations - highest frequency task"""
        params = {
            "user_id": self.user_id,
            "limit": random.choice([10, 20, 50]),
            "offset": random.randint(0, 100),
            "include_metadata": random.choice(["true", "false"])
        }
        
        # 20% chance to request async processing
        if random.random() < 0.2:
            params["async"] = "true"
        
        with self.client.get(
            "/api/v1/recommendations",
            params=params,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/recommendations"
        ) as response:
            self._validate_recommendation_response(response)
    
    @task(30)
    def get_timeline(self):
        """Get home timeline with injected recommendations"""
        timeline_type = random.choice(TIMELINE_TYPES)
        params = {
            "user_id": self.user_id,
            "limit": random.choice([20, 50]),
            "max_id": random.randint(1000, 5000) if random.random() < 0.3 else None,
            "since_id": random.randint(1, 1000) if random.random() < 0.2 else None
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        with self.client.get(
            f"/api/v1/timelines/{timeline_type}",
            params=params,
            headers=self.headers,
            catch_response=True,
            name=f"/api/v1/timelines/{timeline_type}"
        ) as response:
            self._validate_timeline_response(response)
    
    @task(20)
    def log_interaction(self):
        """Log user interaction with content"""
        interaction_data = {
            "user_id": self.user_id,
            "post_id": f"post_{random.randint(1, TEST_POST_POOL_SIZE)}",
            "interaction_type": random.choice(INTERACTION_TYPES),
            "timestamp": int(time.time()),
            "metadata": {
                "source": "timeline" if random.random() < 0.7 else "recommendation",
                "position": random.randint(1, 20),
                "time_spent": random.randint(1, 60)
            }
        }
        
        with self.client.post(
            "/api/v1/interactions",
            json=interaction_data,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/interactions"
        ) as response:
            if response.status_code in [200, 201, 204]:
                response.success()
            else:
                response.failure(f"Interaction logging failed: {response.status_code}")
    
    @task(10)
    def discover_content(self):
        """Discover new content through various endpoints"""
        endpoint = random.choice([
            "/api/v1/posts/trending",
            "/api/v1/posts/recommended",
            "/api/v1/posts"
        ])
        
        params = {
            "limit": random.choice([10, 20]),
            "offset": random.randint(0, 200)
        }
        
        with self.client.get(
            endpoint,
            params=params,
            headers=self.headers,
            catch_response=True,
            name=endpoint
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "posts" in data:
                        response.success()
                    elif isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(5)
    def check_async_task_status(self):
        """Check status of async recommendation tasks"""
        # Simulate checking a previously submitted task
        task_id = f"task_{random.randint(1000, 9999)}"
        
        with self.client.get(
            f"/api/v1/recommendations/status/{task_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/recommendations/status/[task_id]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Task status check failed: {response.status_code}")
    
    @task(3)
    def update_preferences(self):
        """Update user preferences"""
        preferences = {
            "diversity_weight": round(random.uniform(0.1, 0.9), 2),
            "recency_weight": round(random.uniform(0.1, 0.9), 2),
            "language_preferences": random.sample(["en", "es", "fr", "de", "ja"], k=2),
            "content_filters": random.sample(["politics", "sports", "tech", "art"], k=2)
        }
        
        with self.client.put(
            f"/api/v1/users/{self.user_id}/preferences",
            json=preferences,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/users/[user_id]/preferences"
        ) as response:
            if response.status_code in [200, 204]:
                response.success()
            else:
                response.failure(f"Preference update failed: {response.status_code}")
    
    @task(2)
    def get_metrics(self):
        """Get recommendation quality metrics"""
        with self.client.get(
            f"/api/v1/metrics/recommendations/{self.user_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/metrics/recommendations/[user_id]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # User might not have metrics yet
                response.success()
            else:
                response.failure(f"Metrics fetch failed: {response.status_code}")
    
    def _validate_recommendation_response(self, response):
        """Validate recommendation API response"""
        if response.status_code == 202:
            # Async processing
            try:
                data = response.json()
                if "task_id" in data:
                    response.success()
                else:
                    response.failure("Async response missing task_id")
            except json.JSONDecodeError:
                response.failure("Invalid JSON in async response")
        elif response.status_code == 200:
            try:
                data = response.json()
                if "recommendations" in data and isinstance(data["recommendations"], list):
                    response.success()
                else:
                    response.failure("Invalid recommendation response format")
            except json.JSONDecodeError:
                response.failure("Invalid JSON response")
        else:
            response.failure(f"Unexpected status code: {response.status_code}")
    
    def _validate_timeline_response(self, response):
        """Validate timeline API response"""
        if response.status_code == 200:
            try:
                data = response.json()
                if "timeline" in data and isinstance(data["timeline"], list):
                    # Check if recommendations are injected
                    has_recommendations = any(
                        post.get("is_recommendation", False) 
                        for post in data["timeline"]
                    )
                    if has_recommendations or len(data["timeline"]) == 0:
                        response.success()
                    else:
                        # Timeline should have some recommendations
                        logger.warning("Timeline has no injected recommendations")
                        response.success()  # Still success, but log warning
                else:
                    response.failure("Invalid timeline response format")
            except json.JSONDecodeError:
                response.failure("Invalid JSON response")
        else:
            response.failure(f"Timeline fetch failed: {response.status_code}")


class CorgiUser(HttpUser):
    """Simulated user for Corgi Recommender Service"""
    
    tasks = [CorgiTaskSet]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts"""
        logger.info(f"New user spawned: {self.environment.runner.user_count} total users")
    
    def on_stop(self):
        """Called when a simulated user stops"""
        logger.info("User stopped")


# Event handlers for custom metrics and reporting
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics collection"""
    logger.info("=" * 80)
    logger.info("Corgi Recommender Service - Load Test Initialized")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Test started at: {datetime.now()}")
    logger.info("=" * 80)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("Load test starting...")
    # Initialize custom metrics collection
    environment.stats.clear_all()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("Load test completed")
    logger.info("=" * 80)
    logger.info("Test Summary:")
    logger.info(f"Total requests: {environment.stats.total.num_requests}")
    logger.info(f"Failed requests: {environment.stats.total.num_failures}")
    logger.info(f"Median response time: {environment.stats.total.median_response_time}ms")
    logger.info(f"95th percentile: {environment.stats.total.get_response_time_percentile(0.95)}ms")
    logger.info("=" * 80)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Collect detailed request metrics"""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
    elif response and response.status_code >= 500:
        logger.error(f"Server error: {name} - Status {response.status_code}")
    elif response and response.status_code == 429:
        logger.warning(f"Rate limited: {name}")
    
    # Log slow requests
    if response_time > 1000:  # Log requests slower than 1 second
        logger.warning(f"Slow request: {name} took {response_time}ms")


@events.report_to_master.add_listener
def on_report_to_master(client_id, data):
    """Handle reporting in distributed mode"""
    logger.debug(f"Worker {client_id} reporting to master")


@events.worker_report.add_listener
def on_worker_report(client_id, data):
    """Handle worker reports in distributed mode"""
    logger.debug(f"Master received report from worker {client_id}")


# Custom LoadTestShape for specific scenarios (optional)
from locust import LoadTestShape

class StressTestShape(LoadTestShape):
    """
    Custom load shape for stress testing scenarios
    Can be activated by running: locust -f locustfile_recommendations.py --class-picker
    """
    
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 1},      # Warm-up
        {"duration": 300, "users": 100, "spawn_rate": 5},    # Ramp to normal load
        {"duration": 600, "users": 200, "spawn_rate": 10},   # Sustained normal load
        {"duration": 900, "users": 500, "spawn_rate": 20},   # Increase to high load
        {"duration": 1200, "users": 1000, "spawn_rate": 50}, # Peak load
        {"duration": 1500, "users": 200, "spawn_rate": 20},  # Ramp down
        {"duration": 1800, "users": 10, "spawn_rate": 5},    # Cool down
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        
        # Test complete
        return None


# Utility functions for test data generation
def generate_test_user_id() -> str:
    """Generate a test user ID"""
    return f"stress_user_{random.randint(1, TEST_USER_POOL_SIZE)}"


def generate_test_post_id() -> str:
    """Generate a test post ID"""
    return f"post_{random.randint(1, TEST_POST_POOL_SIZE)}"


def generate_interaction_type() -> str:
    """Generate a random interaction type"""
    return random.choice(INTERACTION_TYPES)


# Environment setup for programmatic execution
def create_environment(host: str = "http://localhost:5002") -> Environment:
    """Create a Locust environment for programmatic execution"""
    env = Environment(user_classes=[CorgiUser], host=host)
    env.create_local_runner()
    return env


# Main execution for standalone testing
if __name__ == "__main__":
    import sys
    
    # Check if running in standalone mode
    if len(sys.argv) > 1 and sys.argv[1] == "standalone":
        print("Running standalone stress test...")
        env = create_environment()
        
        # Start a greenlet that periodically outputs stats
        import gevent
        gevent.spawn(stats_printer(env.stats))
        
        # Start test
        env.runner.start(100, spawn_rate=10)
        
        # Run for 60 seconds
        gevent.spawn_later(60, lambda: env.runner.quit())
        
        # Wait for completion
        env.runner.greenlet.join()
        
        # Print final stats
        print(f"Total requests: {env.stats.total.num_requests}")
        print(f"Failed requests: {env.stats.total.num_failures}")
        print(f"Average response time: {env.stats.total.avg_response_time}ms")
    else:
        print("Use 'locust -f locustfile_recommendations.py' to run with web UI")
        print("Or 'locust -f locustfile_recommendations.py --headless --users 100 --spawn-rate 10' for headless mode") 