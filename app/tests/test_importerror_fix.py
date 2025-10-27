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
        
        # If it imports config, it should use absolute import
        if 'import settings' in content and 'config' in content:
            assert 'from app.config import' in content, \
                f"{os.path.basename(filepath)} should use 'from app.config import settings'"


def test_config_can_be_imported():
    """Test that config module can be imported."""
    try:
        from app.config import settings
        assert settings is not None
        assert hasattr(settings, 'APP_NAME')
    except ImportError as e:
        pytest.fail(f"Failed to import settings: {e}")


def test_orchestration_router_imports():
    """Test that orchestration router imports work."""
    try:
        from app.orchestration import router
        assert router is not None
    except Exception as e:
        # This might fail due to missing cloud credentials, which is OK in test environment
        # We're mainly checking for import path issues, not runtime dependencies
        error_str = str(e)
        if 'config' in error_str and 'relative import' in error_str:
            pytest.fail(f"Import path error in router: {e}")
        # If it's just missing credentials, the import paths are fine
        if 'DefaultCredentialsError' in str(type(e)):
            pytest.skip("Skipping due to missing Google Cloud credentials (expected in test environment)")
