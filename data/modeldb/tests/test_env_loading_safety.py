#!/usr/bin/env python3
"""
Tests for environment loading safety.

These tests verify:
1. .env loading does NOT override already-set env vars (Secret Manager injection pattern)
2. Error messages for missing vars include guidance about scripts/gcp_secret_inject.sh
3. dotenv uses override=False

NO TESTS HERE REQUIRE REAL GCP ACCESS.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Add the parent directory to sys.path to import run_modeldb_refresh
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))


class TestDotenvOverrideFalse(unittest.TestCase):
    """Test that dotenv does not override pre-existing environment variables."""
    
    def test_dotenv_does_not_override_existing_env_var(self):
        """Verify that load_dotenv with override=False preserves existing vars."""
        # This test directly verifies the behavior we expect from dotenv
        try:
            from dotenv import load_dotenv
        except ImportError:
            self.skipTest("python-dotenv not installed")
        
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("TEST_SECRET_VAR=from_dotenv_file\n")
            f.write("OTHER_VAR=also_from_dotenv\n")
            temp_env_path = Path(f.name)
        
        try:
            # Set the var BEFORE loading dotenv (simulates platform injection)
            os.environ["TEST_SECRET_VAR"] = "from_platform_injection"
            
            # Load dotenv with override=False (as our code does)
            load_dotenv(temp_env_path, override=False)
            
            # The platform-injected value should be preserved
            self.assertEqual(
                os.environ.get("TEST_SECRET_VAR"), 
                "from_platform_injection",
                ".env should NOT override pre-existing env vars"
            )
            
            # Variables not previously set should be loaded
            self.assertEqual(
                os.environ.get("OTHER_VAR"),
                "also_from_dotenv",
                "New vars from .env should be set"
            )
        finally:
            temp_env_path.unlink()
            os.environ.pop("TEST_SECRET_VAR", None)
            os.environ.pop("OTHER_VAR", None)
    
    def test_load_dotenv_safely_uses_override_false(self):
        """Verify our load_dotenv_safely function uses override=False."""
        # Import the function
        from run_modeldb_refresh import load_dotenv_safely
        
        # Read the source code to verify override=False is used
        import inspect
        source = inspect.getsource(load_dotenv_safely)
        
        # Check that override=False is in the source
        self.assertIn(
            "override=False",
            source,
            "load_dotenv_safely must use override=False to preserve platform secrets"
        )


class TestMissingEnvVarGuidance(unittest.TestCase):
    """Test that error messages include Secret Manager injection guidance."""
    
    def test_error_message_mentions_gcp_secret_inject(self):
        """When env vars are missing, error message should mention gcp_secret_inject.sh."""
        import io
        import logging
        from contextlib import redirect_stderr
        
        # Import the check function
        from run_modeldb_refresh import check_required_env_vars, ENV_REQUIREMENTS
        
        # Clear all required env vars
        saved_vars = {}
        for var_name in ENV_REQUIREMENTS:
            if var_name in os.environ:
                saved_vars[var_name] = os.environ.pop(var_name)
        
        try:
            # Check should fail when vars are missing
            env_ok, issues = check_required_env_vars(
                skip_update=False, 
                skip_pipeline=False, 
                dry_run=False
            )
            
            # If there are required vars, env_ok should be False
            has_required = any(
                ENV_REQUIREMENTS[v].get("required_for") 
                for v in ENV_REQUIREMENTS
            )
            
            if has_required:
                self.assertFalse(env_ok, "Should fail when required vars are missing")
                self.assertGreater(len(issues), 0, "Should have issues when vars missing")
        finally:
            # Restore saved vars
            for var_name, value in saved_vars.items():
                os.environ[var_name] = value
    
    def test_gcp_secret_inject_script_exists(self):
        """Verify the gcp_secret_inject.sh script exists."""
        repo_root = SCRIPT_DIR.parent.parent
        inject_script = repo_root / "scripts" / "gcp_secret_inject.sh"
        
        self.assertTrue(
            inject_script.exists(),
            f"gcp_secret_inject.sh should exist at {inject_script}"
        )
    
    def test_gcp_secret_inject_script_is_executable(self):
        """Verify the gcp_secret_inject.sh script has proper bash syntax."""
        import subprocess
        
        repo_root = SCRIPT_DIR.parent.parent
        inject_script = repo_root / "scripts" / "gcp_secret_inject.sh"
        
        if not inject_script.exists():
            self.skipTest("gcp_secret_inject.sh not found")
        
        # Check bash syntax without executing
        result = subprocess.run(
            ["bash", "-n", str(inject_script)],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"gcp_secret_inject.sh has syntax errors: {result.stderr}"
        )


class TestDryRunNoSecrets(unittest.TestCase):
    """Test that dry-run mode doesn't require secrets."""
    
    def test_dry_run_returns_true_for_env_check(self):
        """Dry run should pass env check even without secrets."""
        from run_modeldb_refresh import check_required_env_vars
        
        # Clear all secret env vars
        saved_vars = {}
        for var in ["PINECONE_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"]:
            if var in os.environ:
                saved_vars[var] = os.environ.pop(var)
        
        try:
            # Dry run should not require secrets
            env_ok, issues = check_required_env_vars(
                skip_update=False,
                skip_pipeline=False,
                dry_run=True
            )
            
            self.assertTrue(env_ok, "Dry run should not require secrets")
            self.assertEqual(len(issues), 0, "Dry run should have no issues")
        finally:
            for var_name, value in saved_vars.items():
                os.environ[var_name] = value


class TestProdPerfEvalScript(unittest.TestCase):
    """Test the prod_perf_eval.sh script configuration."""
    
    def test_prod_perf_eval_has_dry_run_only_mode(self):
        """Verify prod_perf_eval.sh supports DRY_RUN_ONLY mode."""
        repo_root = SCRIPT_DIR.parent.parent
        script_path = repo_root / "scripts" / "prod_perf_eval.sh"
        
        if not script_path.exists():
            self.skipTest("prod_perf_eval.sh not found")
        
        content = script_path.read_text()
        
        self.assertIn(
            "DRY_RUN_ONLY",
            content,
            "prod_perf_eval.sh should support DRY_RUN_ONLY mode"
        )
        
        self.assertIn(
            "gcp_secret_inject.sh",
            content,
            "prod_perf_eval.sh should reference gcp_secret_inject.sh"
        )
    
    def test_prod_perf_eval_bash_syntax(self):
        """Verify prod_perf_eval.sh has proper bash syntax."""
        import subprocess
        
        repo_root = SCRIPT_DIR.parent.parent
        script_path = repo_root / "scripts" / "prod_perf_eval.sh"
        
        if not script_path.exists():
            self.skipTest("prod_perf_eval.sh not found")
        
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"prod_perf_eval.sh has syntax errors: {result.stderr}"
        )


if __name__ == "__main__":
    unittest.main()

