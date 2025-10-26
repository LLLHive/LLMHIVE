"""
Test that the planner module imports correctly with absolute imports.
This test validates the fix for the Google Cloud deployment import error.
"""
import pytest


def test_planner_imports_successfully():
    """Test that planner module can be imported without ImportError."""
    try:
        from app.orchestration.planner import Planner, Plan
        assert Planner is not None
        assert Plan is not None
    except ImportError as e:
        pytest.fail(f"Failed to import planner module: {e}")


def test_planner_instantiation():
    """Test that Planner class can be instantiated."""
    from app.orchestration.planner import Planner
    
    # Test instantiation without arguments
    planner1 = Planner()
    assert planner1 is not None
    assert planner1.preferred_protocol is None
    
    # Test instantiation with preferred protocol
    planner2 = Planner(preferred_protocol="simple")
    assert planner2 is not None
    assert planner2.preferred_protocol == "simple"


@pytest.mark.asyncio
async def test_planner_create_plan_with_preferred_protocol():
    """Test that planner creates a plan when preferred protocol is set."""
    from app.orchestration.planner import Planner
    
    planner = Planner(preferred_protocol="simple")
    plan = await planner.create_plan("Test prompt")
    
    assert plan is not None
    assert plan.protocol == "simple"
    assert "simple" in plan.reasoning.lower()
    assert "task" in plan.params
