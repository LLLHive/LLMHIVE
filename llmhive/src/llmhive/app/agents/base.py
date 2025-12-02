"""Base Agent class for LLMHive Autonomous Agents.

This module defines the abstract base class and common interfaces
for all agents in the system.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status of an agent."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    STOPPED = auto()
    WAITING = auto()


class AgentPriority(Enum):
    """Priority levels for agent tasks."""
    CRITICAL = 1  # User-facing, immediate
    HIGH = 2      # Important background
    MEDIUM = 3    # Standard background
    LOW = 4       # Can be deferred


class AgentType(Enum):
    """Type of agent based on execution pattern."""
    PERSISTENT = "persistent"    # Runs continuously
    SCHEDULED = "scheduled"      # Runs on schedule
    ON_DEMAND = "on_demand"      # Triggered by requests
    REACTIVE = "reactive"        # Triggered by events


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    agent_type: AgentType
    priority: AgentPriority = AgentPriority.MEDIUM
    
    # Resource limits
    max_tokens_per_run: int = 10000
    max_runtime_seconds: int = 300
    max_memory_mb: int = 512
    
    # Scheduling (for scheduled agents)
    schedule_cron: Optional[str] = None  # e.g., "0 2 * * *" for 2 AM daily
    schedule_interval_seconds: Optional[int] = None
    
    # Permissions
    allowed_tools: List[str] = field(default_factory=list)
    can_modify_prompts: bool = False
    can_modify_routing: bool = False
    can_access_user_data: bool = False
    
    # Memory
    memory_namespace: str = ""
    persist_state: bool = True
    
    # Retry behavior
    max_retries: int = 3
    retry_delay_seconds: int = 60


@dataclass
class AgentResult:
    """Result of an agent's execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    tokens_used: int = 0
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class AgentTask:
    """A task for an agent to execute."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: AgentPriority = AgentPriority.MEDIUM
    deadline: Optional[datetime] = None
    retries: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class BaseAgent(ABC):
    """Abstract base class for all LLMHive agents.
    
    All agents must implement:
    - execute(): Main execution logic
    - get_capabilities(): What the agent can do
    
    Optional overrides:
    - setup(): One-time initialization
    - teardown(): Cleanup
    - on_error(): Error handling
    - health_check(): Status verification
    """
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.name = config.name
        self.status = AgentStatus.IDLE
        self._task_queue: asyncio.Queue[AgentTask] = asyncio.Queue()
        self._results: List[AgentResult] = []
        self._error_count = 0
        self._last_run: Optional[datetime] = None
        self._total_runs = 0
        self._total_tokens = 0
        
        # Hooks for external integration
        self._on_start_callbacks: List[Callable] = []
        self._on_complete_callbacks: List[Callable] = []
        self._on_error_callbacks: List[Callable] = []
        
        # Memory reference (set by supervisor)
        self._blackboard = None
        self._memory_store = None
        
        logger.info(f"Agent '{self.name}' initialized with type {config.agent_type.value}")
    
    @abstractmethod
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute the agent's main logic.
        
        Args:
            task: Optional specific task to execute
            
        Returns:
            AgentResult with execution outcome
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return the agent's capabilities and metadata.
        
        Returns:
            Dictionary describing what this agent can do
        """
        pass
    
    async def setup(self) -> bool:
        """One-time setup called before first execution.
        
        Override to initialize resources, load models, etc.
        
        Returns:
            True if setup successful, False otherwise
        """
        logger.debug(f"Agent '{self.name}' setup complete")
        return True
    
    async def teardown(self) -> None:
        """Cleanup called when agent is stopped.
        
        Override to release resources, save state, etc.
        """
        logger.debug(f"Agent '{self.name}' teardown complete")
    
    async def on_error(self, error: Exception) -> None:
        """Handle errors during execution.
        
        Args:
            error: The exception that occurred
        """
        self._error_count += 1
        logger.error(f"Agent '{self.name}' error: {error}", exc_info=True)
        
        # Call registered error callbacks
        for callback in self._on_error_callbacks:
            try:
                await callback(self, error)
            except Exception as cb_error:
                logger.error(f"Error callback failed: {cb_error}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check agent health status.
        
        Returns:
            Health status dictionary
        """
        return {
            "name": self.name,
            "status": self.status.name,
            "error_count": self._error_count,
            "total_runs": self._total_runs,
            "total_tokens": self._total_tokens,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "queue_size": self._task_queue.qsize(),
        }
    
    async def run(self) -> AgentResult:
        """Execute the agent with full lifecycle management.
        
        This is the main entry point that handles:
        - Status management
        - Timing
        - Error handling
        - Callbacks
        - Resource tracking
        
        Returns:
            AgentResult from execution
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        
        # Call start callbacks
        for callback in self._on_start_callbacks:
            try:
                await callback(self)
            except Exception as e:
                logger.warning(f"Start callback failed: {e}")
        
        try:
            # Get next task if any
            task = None
            if not self._task_queue.empty():
                task = await self._task_queue.get()
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(task),
                timeout=self.config.max_runtime_seconds
            )
            
            # Track metrics
            self._total_runs += 1
            self._total_tokens += result.tokens_used
            self._last_run = datetime.now()
            self._results.append(result)
            
            # Trim result history
            if len(self._results) > 100:
                self._results = self._results[-100:]
            
            result.duration_ms = int((time.time() - start_time) * 1000)
            
        except asyncio.TimeoutError:
            logger.warning(f"Agent '{self.name}' timed out after {self.config.max_runtime_seconds}s")
            result = AgentResult(
                success=False,
                error=f"Execution timeout after {self.config.max_runtime_seconds}s",
                duration_ms=int((time.time() - start_time) * 1000)
            )
            await self.on_error(TimeoutError("Agent execution timeout"))
            
        except Exception as e:
            logger.error(f"Agent '{self.name}' execution failed: {e}")
            result = AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
            await self.on_error(e)
        
        finally:
            self.status = AgentStatus.IDLE
            
            # Call complete callbacks
            for callback in self._on_complete_callbacks:
                try:
                    await callback(self, result)
                except Exception as e:
                    logger.warning(f"Complete callback failed: {e}")
        
        return result
    
    def add_task(self, task: AgentTask) -> None:
        """Add a task to the agent's queue.
        
        Args:
            task: Task to add
        """
        self._task_queue.put_nowait(task)
        logger.debug(f"Agent '{self.name}' received task {task.task_id}")
    
    def register_callback(
        self,
        event: str,
        callback: Callable
    ) -> None:
        """Register a callback for agent events.
        
        Args:
            event: Event type ('start', 'complete', 'error')
            callback: Async function to call
        """
        if event == "start":
            self._on_start_callbacks.append(callback)
        elif event == "complete":
            self._on_complete_callbacks.append(callback)
        elif event == "error":
            self._on_error_callbacks.append(callback)
        else:
            raise ValueError(f"Unknown event type: {event}")
    
    def set_blackboard(self, blackboard) -> None:
        """Set reference to global blackboard for inter-agent communication.
        
        Args:
            blackboard: AgentBlackboard instance
        """
        self._blackboard = blackboard
    
    def set_memory_store(self, memory_store) -> None:
        """Set reference to persistent memory store.
        
        Args:
            memory_store: Memory store instance
        """
        self._memory_store = memory_store
    
    async def write_to_blackboard(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Write data to the shared blackboard.
        
        Args:
            key: Key to store under
            value: Value to store
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        if not self._blackboard:
            logger.warning(f"Agent '{self.name}' has no blackboard reference")
            return False
        
        return await self._blackboard.write(
            key=f"{self.name}:{key}",
            value=value,
            source_agent=self.name,
            ttl_seconds=ttl_seconds
        )
    
    async def read_from_blackboard(self, key: str, source_agent: Optional[str] = None) -> Any:
        """Read data from the shared blackboard.
        
        Args:
            key: Key to read
            source_agent: Optional filter by source agent
            
        Returns:
            Stored value or None
        """
        if not self._blackboard:
            logger.warning(f"Agent '{self.name}' has no blackboard reference")
            return None
        
        full_key = f"{source_agent}:{key}" if source_agent else key
        return await self._blackboard.read(full_key)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' status={self.status.name}>"

