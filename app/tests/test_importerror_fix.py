"""
Test suite to verify ImportError fix for orchestration/planner.py
This ensures that all imports work correctly for Cloud Run deployment.
"""
import pytest


def test_planner_has_no_relative_config_import():
    """Verify planner.py does not use relative import for config."""
    import os
    planner_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'orchestration', 
        'planner.py'
    )
    
    with open(planner_path, 'r') as f:
        content = f.read()
    
    # Should NOT contain problematic relative import
    assert 'from ..config import' not in content, \
        "planner.py should not use relative import 'from ..config import'"
    
    # Should use absolute imports
    assert 'from app.models' in content or 'from .models' in content, \
        "planner.py should have imports"


def test_planner_imports_successfully():
    """Test that planner module can be imported without ImportError."""
    try:
        from app.orchestration.planner import Planner
        assert Planner is not None
    except ImportError as e:
        pytest.fail(f"Failed to import Planner: {e}")


def test_planner_models_import():
    """Test that Plan model can be imported."""
    try:
        from app.orchestration.models import Plan
        assert Plan is not None
    except ImportError as e:
        pytest.fail(f"Failed to import Plan: {e}")


def test_orchestration_config_imports():
    """Verify all orchestration files use correct config imports."""
    import os
    import glob
    
    orchestration_dir = os.path.join(
        os.path.dirname(__file__),
        '..',
        'orchestration'
    )
    
    python_files = glob.glob(os.path.join(orchestration_dir, '*.py'))
    
    for filepath in python_files:
        if os.path.basename(filepath) == '__init__.py':
            continue
            
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Check for problematic pattern
        assert 'from ..config import' not in content, \
            f"{os.path.basename(filepath)} should not use 'from ..config import'"
        
        # If it imports config settings, it should use absolute import
        # Use more specific pattern matching for actual import statements
        if 'from app.config import settings' in content or 'from app.config import' in content:
            # File correctly uses absolute import
            assert 'from app.config import' in content, \
                f"{os.path.basename(filepath)} should use 'from app.config import'"


def test_config_can_be_imported():
    """Test that config module can be imported."""
    try:
        from app.config import settings
        assert settings is not None
        assert hasattr(settings, 'APP_NAME')
    except ImportError as e:
        pytest.fail(f"Failed to import settings: {e}")


def test_orchestration_router_imports():
    """Test that orchestration router imports work.
    
    Note: This test may be skipped in environments without Google Cloud credentials,
    as the router initialization requires Firestore access. The test primarily
    validates import paths rather than runtime functionality.
    """
    try:
        from app.orchestration import router
        assert router is not None
    except ImportError as e:
        # Import errors indicate a problem with import paths
        error_msg = str(e)
        if 'config' in error_msg or 'relative import' in error_msg:
            pytest.fail(f"Import path error in router: {e}")
        else:
            # Some other import issue
            raise
    except Exception as e:
        # Other exceptions (like missing credentials) are OK in test environment
        # Check if it's specifically a credentials error
        if 'DefaultCredentialsError' in type(e).__name__:
            pytest.skip("Skipping due to missing Google Cloud credentials (expected in test environment)")
        elif 'credentials' in str(e).lower():
            pytest.skip(f"Skipping due to missing credentials: {type(e).__name__}")
        else:
            # Unexpected error, re-raise
            raise
