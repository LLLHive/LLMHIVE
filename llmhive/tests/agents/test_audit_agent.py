"""Tests for AuditAgent."""
import pytest
from datetime import datetime
from llmhive.app.agents.audit_agent import (
    AuditAgent,
    AuditEvent,
    AuditEventType,
    AuditTrail,
    ComplianceStatus,
    CompliancePolicy,
    DEFAULT_POLICIES,
)
from llmhive.app.agents.base import AgentTask


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""
    
    def test_to_dict(self):
        """Test serialization."""
        event = AuditEvent(
            id="evt-123",
            event_type=AuditEventType.QUERY_RECEIVED,
            timestamp=datetime.now(),
            session_id="sess-1",
            description="Query received",
            component="orchestrator",
            compliance_status=ComplianceStatus.COMPLIANT,
        )
        data = event.to_dict()
        
        assert data["id"] == "evt-123"
        assert data["event_type"] == "query_received"
        assert data["session_id"] == "sess-1"
        assert data["compliance_status"] == "compliant"


class TestAuditTrail:
    """Tests for AuditTrail dataclass."""
    
    def test_add_event(self):
        """Test adding events to trail."""
        trail = AuditTrail(
            trail_id="trail-1",
            session_id="sess-1",
            started_at=datetime.now(),
        )
        
        event = AuditEvent(
            id="evt-1",
            event_type=AuditEventType.QUERY_RECEIVED,
            timestamp=datetime.now(),
            latency_ms=100,
        )
        trail.add_event(event)
        
        assert trail.total_events == 1
        assert trail.total_latency_ms == 100
    
    def test_counts_violations(self):
        """Test violation counting."""
        trail = AuditTrail(
            trail_id="trail-1",
            session_id="sess-1",
            started_at=datetime.now(),
        )
        
        violation_event = AuditEvent(
            id="evt-1",
            event_type=AuditEventType.POLICY_VIOLATION,
            timestamp=datetime.now(),
            compliance_status=ComplianceStatus.VIOLATION,
        )
        warning_event = AuditEvent(
            id="evt-2",
            event_type=AuditEventType.FILTER_APPLIED,
            timestamp=datetime.now(),
            compliance_status=ComplianceStatus.WARNING,
        )
        
        trail.add_event(violation_event)
        trail.add_event(warning_event)
        
        assert trail.compliance_violations == 1
        assert trail.warnings == 1


class TestCompliancePolicy:
    """Tests for CompliancePolicy dataclass."""
    
    def test_to_dict(self):
        """Test serialization."""
        policy = CompliancePolicy(
            id="test-policy",
            name="Test Policy",
            description="A test policy",
            category="testing",
            enabled=True,
            severity="warning",
        )
        data = policy.to_dict()
        
        assert data["id"] == "test-policy"
        assert data["name"] == "Test Policy"
        assert data["enabled"] is True


class TestDefaultPolicies:
    """Tests for default policies."""
    
    def test_has_required_policies(self):
        """Test that required policies exist."""
        policy_ids = [p.id for p in DEFAULT_POLICIES]
        
        assert "pii_detection" in policy_ids
        assert "content_safety" in policy_ids
        assert "rate_limit_compliance" in policy_ids
    
    def test_all_policies_have_categories(self):
        """Test that all policies have categories."""
        for policy in DEFAULT_POLICIES:
            assert policy.category, f"Policy {policy.id} missing category"


class TestAuditAgent:
    """Tests for AuditAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return AuditAgent()
    
    def test_initialization(self, agent):
        """Test agent initialization."""
        assert agent.config.name == "audit_agent"
        assert len(agent._policies) > 0
        assert agent._total_events == 0
    
    def test_get_capabilities(self, agent):
        """Test capabilities reporting."""
        caps = agent.get_capabilities()
        
        assert caps["name"] == "Audit & Compliance Agent"
        assert "log_event" in caps["task_types"]
        assert "check_compliance" in caps["task_types"]
    
    @pytest.mark.asyncio
    async def test_default_execution(self, agent):
        """Test default execution returns summary."""
        result = await agent.execute(None)
        
        assert result.success
        assert "total_events" in result.output
        assert "compliance_rate" in result.output
    
    @pytest.mark.asyncio
    async def test_log_event(self, agent):
        """Test logging an event."""
        task = AgentTask(
            task_id="test-1",
            task_type="log_event",
            payload={
                "event_type": "query_received",
                "session_id": "sess-123",
                "description": "Test query",
                "component": "test",
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "event_id" in result.output
        assert agent._total_events == 1
    
    @pytest.mark.asyncio
    async def test_log_event_creates_trail(self, agent):
        """Test that logging creates audit trail."""
        task = AgentTask(
            task_id="test-2",
            task_type="log_event",
            payload={
                "event_type": "query_received",
                "session_id": "sess-456",
                "component": "test",
            },
        )
        await agent.execute(task)
        
        assert "sess-456" in agent._trails
    
    @pytest.mark.asyncio
    async def test_get_trail(self, agent):
        """Test getting audit trail."""
        # First log an event
        await agent.execute(AgentTask(
            task_id="t1",
            task_type="log_event",
            payload={"session_id": "sess-789", "component": "test"},
        ))
        
        # Get trail
        task = AgentTask(
            task_id="test-3",
            task_type="get_trail",
            payload={"session_id": "sess-789"},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert result.output["session_id"] == "sess-789"
    
    @pytest.mark.asyncio
    async def test_get_trail_not_found(self, agent):
        """Test getting non-existent trail."""
        task = AgentTask(
            task_id="test-4",
            task_type="get_trail",
            payload={"session_id": "nonexistent"},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "No audit trail found" in result.output["message"]
    
    @pytest.mark.asyncio
    async def test_check_compliance_clean(self, agent):
        """Test compliance check with clean content."""
        task = AgentTask(
            task_id="test-5",
            task_type="check_compliance",
            payload={
                "content": "Hello, how can I help you today",  # No special characters
                "models_used": ["gpt-4o"],  # Include model attribution
            },
        )
        result = await agent.execute(task)
        
        assert result.success
        assert result.output["status"] == "compliant"
        assert len(result.output["violations"]) == 0
    
    @pytest.mark.asyncio
    async def test_check_compliance_pii(self, agent):
        """Test compliance check detects PII."""
        task = AgentTask(
            task_id="test-6",
            task_type="check_compliance",
            payload={"content": "My social security number is 123-45-6789"},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert result.output["status"] in ["violation", "warning"]
        assert len(result.output["violations"]) > 0 or len(result.output["warnings"]) > 0
    
    @pytest.mark.asyncio
    async def test_generate_report(self, agent):
        """Test report generation."""
        # Log some events first
        for i in range(3):
            await agent.execute(AgentTask(
                task_id=f"t{i}",
                task_type="log_event",
                payload={"session_id": f"sess-{i}", "component": "test"},
            ))
        
        task = AgentTask(
            task_id="test-7",
            task_type="generate_report",
            payload={"time_range": "24h", "include_details": True},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "summary" in result.output
        assert result.output["summary"]["total_events"] >= 3
    
    @pytest.mark.asyncio
    async def test_get_policies(self, agent):
        """Test getting policies."""
        task = AgentTask(
            task_id="test-8",
            task_type="get_policies",
            payload={},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert result.output["total"] > 0
        assert len(result.output["policies"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_policies_by_category(self, agent):
        """Test getting policies by category."""
        task = AgentTask(
            task_id="test-9",
            task_type="get_policies",
            payload={"category": "data_privacy"},
        )
        result = await agent.execute(task)
        
        assert result.success
        for policy in result.output["policies"]:
            assert policy["category"] == "data_privacy"
    
    @pytest.mark.asyncio
    async def test_explain_decision(self, agent):
        """Test decision explanation."""
        # Log some events for a session
        session_id = "sess-explain"
        await agent.execute(AgentTask(
            task_id="t1",
            task_type="log_event",
            payload={
                "session_id": session_id,
                "event_type": "query_received",
                "action": "receive_query",
                "component": "orchestrator",
            },
        ))
        await agent.execute(AgentTask(
            task_id="t2",
            task_type="log_event",
            payload={
                "session_id": session_id,
                "event_type": "model_selected",
                "action": "select_model",
                "component": "model_router",
                "outputs": {"model": "gpt-4o"},
            },
        ))
        
        task = AgentTask(
            task_id="test-10",
            task_type="explain_decision",
            payload={"session_id": session_id},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "steps" in result.output
        assert len(result.output["steps"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, agent):
        """Test getting statistics."""
        task = AgentTask(
            task_id="test-11",
            task_type="get_statistics",
            payload={},
        )
        result = await agent.execute(task)
        
        assert result.success
        assert "total_events" in result.output
        assert "compliance_rate" in result.output
    
    @pytest.mark.asyncio
    async def test_unknown_task_type(self, agent):
        """Test with unknown task type."""
        task = AgentTask(
            task_id="test-12",
            task_type="unknown_type",
            payload={},
        )
        result = await agent.execute(task)
        
        assert not result.success
        assert "Unknown task type" in result.error
    
    def test_log_query_method(self, agent):
        """Test the log_query convenience method."""
        event_id = agent.log_query(
            query="Test query",
            session_id="sess-test",
            user_id="user-1",
        )
        
        assert event_id.startswith("evt-")
        assert len(agent._audit_log) == 1
    
    def test_log_model_selection_method(self, agent):
        """Test the log_model_selection convenience method."""
        agent.log_model_selection(
            model="gpt-4o",
            session_id="sess-test",
            reason="Best for coding",
        )
        
        assert len(agent._audit_log) == 1
        assert agent._audit_log[0].event_type == AuditEventType.MODEL_SELECTED
    
    def test_log_tool_invocation_method(self, agent):
        """Test the log_tool_invocation convenience method."""
        agent.log_tool_invocation(
            tool_name="calculator",
            session_id="sess-test",
            inputs={"expression": "2+2"},
            outputs={"result": 4},
            latency_ms=50.0,
        )
        
        assert len(agent._audit_log) == 1
        assert agent._audit_log[0].event_type == AuditEventType.TOOL_INVOKED
