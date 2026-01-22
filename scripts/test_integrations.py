#!/usr/bin/env python3
"""
Integration Test Script for Slack and Email Services

Tests:
1. Slack webhook connectivity
2. Resend email API connectivity
3. Both send test messages to verify end-to-end

Usage:
    python scripts/test_integrations.py

Environment Variables Required:
    SLACK_WEBHOOK_URL - Slack incoming webhook URL
    RESEND_API_KEY - Resend API key
"""

import os
import sys
import json
import time
from datetime import datetime

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(60)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_success(text: str):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text: str):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text: str):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text: str):
    print(f"{BLUE}ℹ️  {text}{RESET}")

# ============================================================================
# Slack Tests
# ============================================================================

def test_slack_webhook():
    """Test Slack webhook connectivity and send a test message."""
    print_header("Testing Slack Integration")
    
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        print_warning("SLACK_WEBHOOK_URL not set in environment")
        print_info("Checking if it exists in GCP Secret Manager...")
        return "skipped", "No webhook URL configured"
    
    # Validate URL format
    if not webhook_url.startswith("https://hooks.slack.com/"):
        print_error(f"Invalid webhook URL format: {webhook_url[:50]}...")
        return "failed", "Invalid webhook URL format"
    
    print_info(f"Webhook URL: {webhook_url[:50]}...")
    
    try:
        import urllib.request
        
        test_message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🧪 LLMHive Integration Test",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Test Time:*\n{datetime.now().isoformat()}"},
                        {"type": "mrkdwn", "text": "*Status:*\n✅ Slack is working!"}
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "This is an automated test from `scripts/test_integrations.py`"}
                    ]
                }
            ]
        }
        
        data = json.dumps(test_message).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print_info("Sending test message to Slack...")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            body = response.read().decode('utf-8')
            
            if status == 200 and body == "ok":
                print_success("Slack webhook is working!")
                print_success("Test message sent successfully")
                return "passed", "Message sent"
            else:
                print_error(f"Unexpected response: {status} - {body}")
                return "failed", f"Status: {status}, Body: {body}"
                
    except urllib.error.HTTPError as e:
        print_error(f"HTTP Error: {e.code} - {e.reason}")
        return "failed", f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        print_error(f"URL Error: {e.reason}")
        return "failed", f"URL Error: {e.reason}"
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return "failed", str(e)

# ============================================================================
# Resend Email Tests
# ============================================================================

def test_resend_api():
    """Test Resend API connectivity."""
    print_header("Testing Resend Email Integration")
    
    api_key = os.environ.get("RESEND_API_KEY")
    
    if not api_key:
        print_warning("RESEND_API_KEY not set in environment")
        print_info("Checking if it exists in GCP Secret Manager...")
        return "skipped", "No API key configured"
    
    # Validate API key format
    if not api_key.startswith("re_"):
        print_error(f"Invalid API key format (should start with 're_')")
        return "failed", "Invalid API key format"
    
    print_info(f"API Key: {api_key[:10]}...")
    
    try:
        import urllib.request
        
        # First, test API connectivity by listing domains (doesn't send email)
        req = urllib.request.Request(
            "https://api.resend.com/domains",
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        print_info("Testing API connectivity...")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            body = json.loads(response.read().decode('utf-8'))
            
            if status == 200:
                print_success("Resend API is accessible!")
                domains = body.get('data', [])
                if domains:
                    print_success(f"Found {len(domains)} configured domain(s)")
                    for domain in domains:
                        status_emoji = "✅" if domain.get('status') == 'verified' else "⚠️"
                        print_info(f"  {status_emoji} {domain.get('name')} ({domain.get('status')})")
                else:
                    print_warning("No domains configured - emails will use Resend's default domain")
                
                return "passed", f"{len(domains)} domain(s) found"
            else:
                print_error(f"Unexpected response: {status}")
                return "failed", f"Status: {status}"
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e.reason)
        print_error(f"HTTP Error: {e.code} - {error_body}")
        return "failed", f"HTTP {e.code}: {error_body}"
    except urllib.error.URLError as e:
        print_error(f"URL Error: {e.reason}")
        return "failed", f"URL Error: {e.reason}"
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return "failed", str(e)

def test_resend_send_email():
    """Send a test email via Resend (optional - requires valid domain)."""
    api_key = os.environ.get("RESEND_API_KEY")
    test_email = os.environ.get("TEST_EMAIL")  # Optional: where to send test email
    
    if not api_key or not test_email:
        print_info("Skipping email send test (set TEST_EMAIL env var to enable)")
        return "skipped", "No test email configured"
    
    try:
        import urllib.request
        
        email_data = {
            "from": "LLMHive Test <onboarding@resend.dev>",  # Use Resend's test domain
            "to": test_email,
            "subject": "🧪 LLMHive Integration Test",
            "html": f"""
                <h1>LLMHive Email Test</h1>
                <p>This is an automated test from <code>scripts/test_integrations.py</code></p>
                <p>Test time: {datetime.now().isoformat()}</p>
                <p>If you receive this, email integration is working! ✅</p>
            """
        }
        
        data = json.dumps(email_data).encode('utf-8')
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=data,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        print_info(f"Sending test email to {test_email}...")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            body = json.loads(response.read().decode('utf-8'))
            email_id = body.get('id')
            
            if email_id:
                print_success(f"Test email sent! ID: {email_id}")
                return "passed", f"Email ID: {email_id}"
            else:
                print_error(f"Unexpected response: {body}")
                return "failed", str(body)
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e.reason)
        print_error(f"HTTP Error: {e.code} - {error_body}")
        return "failed", f"HTTP {e.code}"
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return "failed", str(e)

# ============================================================================
# GCP Secret Manager Check
# ============================================================================

def check_gcp_secrets():
    """Check if secrets exist in GCP Secret Manager."""
    print_header("Checking GCP Secret Manager")
    
    try:
        import subprocess
        
        secrets_to_check = [
            "slack-webhook-url",
            "resend-api-key",
        ]
        
        for secret_name in secrets_to_check:
            result = subprocess.run(
                ["gcloud", "secrets", "describe", secret_name, "--format=json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print_success(f"Secret '{secret_name}' exists in GCP")
            else:
                print_warning(f"Secret '{secret_name}' not found in GCP")
                print_info(f"  Create with: gcloud secrets create {secret_name} --data-file=-")
                
    except FileNotFoundError:
        print_warning("gcloud CLI not found - skipping GCP Secret Manager check")
    except Exception as e:
        print_error(f"Error checking GCP secrets: {e}")

# ============================================================================
# Main
# ============================================================================

def main():
    print(f"\n{BOLD}🐝 LLMHive Integration Tests{RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    results = {}
    
    # Check GCP Secrets first
    check_gcp_secrets()
    
    # Run tests
    status, msg = test_slack_webhook()
    results["Slack Webhook"] = (status, msg)
    
    status, msg = test_resend_api()
    results["Resend API"] = (status, msg)
    
    status, msg = test_resend_send_email()
    results["Resend Send Test"] = (status, msg)
    
    # Summary
    print_header("Test Results Summary")
    
    passed = sum(1 for s, _ in results.values() if s == "passed")
    failed = sum(1 for s, _ in results.values() if s == "failed")
    skipped = sum(1 for s, _ in results.values() if s == "skipped")
    
    for test_name, (status, message) in results.items():
        if status == "passed":
            print(f"  {GREEN}✅ {test_name}: PASSED{RESET} - {message}")
        elif status == "failed":
            print(f"  {RED}❌ {test_name}: FAILED{RESET} - {message}")
        else:
            print(f"  {YELLOW}⏭️  {test_name}: SKIPPED{RESET} - {message}")
    
    print(f"\n{BOLD}Total: {passed} passed, {failed} failed, {skipped} skipped{RESET}\n")
    
    # Exit with appropriate code
    if failed > 0:
        sys.exit(1)
    else:
        print_success("All critical integration tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
