"""Load Testing Configuration for LLMHive.

This file defines Locust load tests for LLMHive API:
- Chat endpoint performance
- Concurrent user simulation
- Token usage tracking
- Latency measurement

Usage:
    locust -f locustfile.py --host=http://localhost:8080
    
    # Headless mode for CI/CD:
    locust -f locustfile.py --host=http://localhost:8080 \
        --headless -u 100 -r 10 --run-time 5m
"""
from __future__ import annotations

import json
import os
import random
import time
from typing import Dict, List, Optional

from locust import HttpUser, TaskSet, task, between, events
from locust.runners import MasterRunner


# ==============================================================================
# Test Configuration
# ==============================================================================

# API configuration
API_KEY = os.getenv("LLMHIVE_API_KEY", "test-key")
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

# Sample prompts for testing
SAMPLE_PROMPTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms.",
    "Write a Python function to calculate Fibonacci numbers.",
    "What are the benefits of renewable energy?",
    "How does machine learning work?",
    "Summarize the theory of relativity.",
    "What are best practices for API design?",
    "Explain the difference between SQL and NoSQL databases.",
    "What is the history of artificial intelligence?",
    "How do neural networks learn?",
]

# Complex prompts for stress testing
COMPLEX_PROMPTS = [
    "Analyze the economic impact of climate change on global agriculture, including specific statistics and projections.",
    "Compare and contrast the philosophical approaches of Plato, Aristotle, and Kant regarding ethics and morality.",
    "Provide a detailed technical explanation of transformer architecture in deep learning.",
]

# Models to test
MODELS_TO_TEST = ["gpt-4o-mini", "gpt-4o", "claude-3-haiku"]


# ==============================================================================
# Statistics Tracking
# ==============================================================================

# Custom stats
token_usage = {"total_tokens": 0, "requests": 0}
model_latencies: Dict[str, List[float]] = {}


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, **kwargs):
    """Track custom metrics on each request."""
    global token_usage
    
    response = kwargs.get("response")
    if response and response.ok:
        try:
            data = response.json()
            if "usage" in data:
                token_usage["total_tokens"] += data["usage"].get("total_tokens", 0)
            token_usage["requests"] += 1
        except Exception:
            pass


@events.test_stop.add_listener
def on_test_stop(**kwargs):
    """Print final statistics."""
    if token_usage["requests"] > 0:
        avg_tokens = token_usage["total_tokens"] / token_usage["requests"]
        print(f"\n=== Token Usage Statistics ===")
        print(f"Total Tokens: {token_usage['total_tokens']:,}")
        print(f"Total Requests: {token_usage['requests']:,}")
        print(f"Avg Tokens/Request: {avg_tokens:.1f}")


# ==============================================================================
# Task Sets
# ==============================================================================

class ChatTasks(TaskSet):
    """Tasks for chat endpoint testing."""
    
    @task(5)
    def simple_chat(self):
        """Test simple chat completion."""
        prompt = random.choice(SAMPLE_PROMPTS)
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "gpt-4o-mini",
            "max_tokens": 100,
        }
        
        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=BASE_HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def chat_with_context(self):
        """Test chat with conversation history."""
        messages = [
            {"role": "user", "content": "Hello, I have a question."},
            {"role": "assistant", "content": "Of course! How can I help you?"},
            {"role": "user", "content": random.choice(SAMPLE_PROMPTS)},
        ]
        
        payload = {
            "messages": messages,
            "model": "gpt-4o-mini",
            "max_tokens": 150,
        }
        
        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=BASE_HEADERS,
            name="/v1/chat/completions [with context]",
        )
    
    @task(1)
    def complex_chat(self):
        """Test complex prompts."""
        prompt = random.choice(COMPLEX_PROMPTS)
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "gpt-4o",
            "max_tokens": 500,
        }
        
        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=BASE_HEADERS,
            name="/v1/chat/completions [complex]",
        )


class HealthTasks(TaskSet):
    """Tasks for health check endpoints."""
    
    @task(10)
    def health_check(self):
        """Test health endpoint."""
        self.client.get("/healthz", name="/healthz")
    
    @task(1)
    def full_health(self):
        """Test full health endpoint."""
        self.client.get("/health", name="/health")
    
    @task(5)
    def readiness(self):
        """Test readiness endpoint."""
        self.client.get("/readyz", name="/readyz")


class ToolTasks(TaskSet):
    """Tasks for tool execution testing."""
    
    @task(3)
    def calculator(self):
        """Test calculator tool."""
        expressions = [
            "2 + 2",
            "100 * 5",
            "sqrt(144)",
            "sin(3.14159 / 2)",
        ]
        
        payload = {
            "messages": [
                {"role": "user", "content": f"Calculate: {random.choice(expressions)}"}
            ],
            "model": "gpt-4o-mini",
            "tools": [{"name": "calculator"}],
        }
        
        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=BASE_HEADERS,
            name="/v1/chat/completions [tool:calculator]",
        )


# ==============================================================================
# User Classes
# ==============================================================================

class NormalUser(HttpUser):
    """Simulates a normal user making occasional requests."""
    tasks = [ChatTasks, HealthTasks]
    weight = 8
    wait_time = between(1, 5)


class PowerUser(HttpUser):
    """Simulates a power user making frequent requests."""
    tasks = [ChatTasks, ToolTasks]
    weight = 2
    wait_time = between(0.5, 2)


class HealthMonitor(HttpUser):
    """Simulates health monitoring (e.g., Kubernetes)."""
    tasks = [HealthTasks]
    weight = 1
    wait_time = between(5, 10)


# ==============================================================================
# Stress Test User
# ==============================================================================

class StressTestUser(HttpUser):
    """User for stress testing - minimal wait time."""
    
    wait_time = between(0.1, 0.5)
    weight = 1
    
    @task
    def rapid_requests(self):
        """Make rapid requests to stress test."""
        self.client.get("/healthz")
    
    @task(2)
    def stress_chat(self):
        """Stress test chat endpoint."""
        payload = {
            "messages": [{"role": "user", "content": "Quick test"}],
            "model": "gpt-4o-mini",
            "max_tokens": 10,
        }
        
        self.client.post(
            "/v1/chat/completions",
            json=payload,
            headers=BASE_HEADERS,
            name="/v1/chat/completions [stress]",
        )


# ==============================================================================
# CLI Entry Point
# ==============================================================================

if __name__ == "__main__":
    import sys
    from locust.main import main
    
    sys.exit(main())

