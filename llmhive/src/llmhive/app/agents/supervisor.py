"""Agent Supervisor - Manages lifecycle of all autonomous agents.

The supervisor is responsible for:
- Starting and stopping agents
- Monitoring agent health
- Managing resource allocation
- Coordinating agent activities
- Handling agent failures
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from collections import defaultdict

from .base import (
    BaseAgent,
    AgentConfig,
    AgentStatus,
    AgentResult,
    AgentType,
    AgentPriority,
)
from .blackboard import AgentBlackboard, get_global_blackboard

logger = logging.getLogger(__name__)


class AgentSupervisor:
    """Manages the lifecycle and coordination of all autonomous agents.
    
    Responsibilities:
    - Agent registration and initialization
    - Lifecycle management (start, stop, pause, resume)
    - Health monitoring and automatic recovery
    - Resource allocation and throttling
    - Inter-agent coordination via blackboard
    """
    
    def __init__(
        self,
        max_concurrent_agents: int = 10,
        health_check_interval: int = 60,
        auto_restart_failed: bool = True,
    ):
        """Initialize the supervisor.
        
        Args:
            max_concurrent_agents: Max agents running simultaneously
            health_check_interval: Seconds between health checks
            auto_restart_failed: Whether to auto-restart failed agents
        """
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._max_concurrent = max_concurrent_agents
        self._health_check_interval = health_check_interval
        self._auto_restart = auto_restart_failed
        
        # Resource tracking
        self._total_tokens_used = 0
        self._total_runs = 0
        self._errors_by_agent: Dict[str, int] = defaultdict(int)
        
        # Background tasks
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # Blackboard reference
        self._blackboard: Optional[AgentBlackboard] = None
        
        logger.info(f"AgentSupervisor initialized (max_concurrent={max_concurrent_agents})")
    
    async def start(self) -> None:
        """Start the supervisor and all registered agents."""
        if self._running:
            logger.warning("Supervisor already running")
            return
        
        self._running = True
        
        # Initialize blackboard
        self._blackboard = get_global_blackboard()
        await self._blackboard.start()
        
        # Start health monitor
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        
        # Start all registered agents
        for agent in self._agents.values():
            await self._start_agent(agent)
        
        logger.info(f"AgentSupervisor started with {len(self._agents)} agents")
    
    async def stop(self) -> None:
        """Stop the supervisor and all agents gracefully."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel health monitor
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all agents
        for name in list(self._agent_tasks.keys()):
            await self._stop_agent(name)
        
        # Stop blackboard
        if self._blackboard:
            await self._blackboard.stop()
        
        logger.info("AgentSupervisor stopped")
    
    def register_agent(
        self,
        agent_class: Type[BaseAgent],
        config: AgentConfig,
    ) -> BaseAgent:
        """Register a new agent with the supervisor.
        
        Args:
            agent_class: The agent class to instantiate
            config: Configuration for the agent
            
        Returns:
            The created agent instance
        """
        if config.name in self._agents:
            raise ValueError(f"Agent '{config.name}' already registered")
        
        # Create agent instance
        agent = agent_class(config)
        
        # Wire up blackboard
        if self._blackboard:
            agent.set_blackboard(self._blackboard)
        
        # Register error callback
        agent.register_callback("error", self._on_agent_error)
        agent.register_callback("complete", self._on_agent_complete)
        
        self._agents[config.name] = agent
        logger.info(f"Registered agent: {config.name} ({config.agent_type.value})")
        
        # If supervisor is running, start the agent
        if self._running:
            asyncio.create_task(self._start_agent(agent))
        
        return agent
    
    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent.
        
        Args:
            name: Name of agent to remove
            
        Returns:
            True if agent was removed
        """
        if name not in self._agents:
            return False
        
        # Stop the agent first
        if name in self._agent_tasks:
            asyncio.create_task(self._stop_agent(name))
        
        del self._agents[name]
        logger.info(f"Unregistered agent: {name}")
        return True
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent instance or None
        """
        return self._agents.get(name)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their status.
        
        Returns:
            List of agent info dictionaries
        """
        return [
            {
                "name": agent.name,
                "type": agent.config.agent_type.value,
                "status": agent.status.name,
                "priority": agent.config.priority.name,
            }
            for agent in self._agents.values()
        ]
    
    async def trigger_agent(
        self,
        name: str,
        task: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentResult]:
        """Manually trigger an agent execution.
        
        Args:
            name: Agent name
            task: Optional task payload
            
        Returns:
            AgentResult from execution
        """
        agent = self._agents.get(name)
        if not agent:
            logger.warning(f"Agent '{name}' not found")
            return None
        
        if agent.status == AgentStatus.RUNNING:
            logger.warning(f"Agent '{name}' is already running")
            return None
        
        return await agent.run()
    
    async def pause_agent(self, name: str) -> bool:
        """Pause an agent.
        
        Args:
            name: Agent name
            
        Returns:
            True if paused
        """
        agent = self._agents.get(name)
        if not agent:
            return False
        
        agent.status = AgentStatus.PAUSED
        
        # Cancel running task
        if name in self._agent_tasks:
            self._agent_tasks[name].cancel()
            try:
                await self._agent_tasks[name]
            except asyncio.CancelledError:
                pass
            del self._agent_tasks[name]
        
        logger.info(f"Paused agent: {name}")
        return True
    
    async def resume_agent(self, name: str) -> bool:
        """Resume a paused agent.
        
        Args:
            name: Agent name
            
        Returns:
            True if resumed
        """
        agent = self._agents.get(name)
        if not agent:
            return False
        
        if agent.status != AgentStatus.PAUSED:
            return False
        
        await self._start_agent(agent)
        logger.info(f"Resumed agent: {name}")
        return True
    
    async def _start_agent(self, agent: BaseAgent) -> bool:
        """Start an individual agent.
        
        Args:
            agent: Agent to start
            
        Returns:
            True if started successfully
        """
        try:
            # Setup
            if not await agent.setup():
                logger.error(f"Agent '{agent.name}' setup failed")
                agent.status = AgentStatus.ERROR
                return False
            
            # Start based on type
            if agent.config.agent_type == AgentType.PERSISTENT:
                # Run continuously
                task = asyncio.create_task(self._run_persistent_agent(agent))
                self._agent_tasks[agent.name] = task
                
            elif agent.config.agent_type == AgentType.SCHEDULED:
                # Run on schedule
                task = asyncio.create_task(self._run_scheduled_agent(agent))
                self._agent_tasks[agent.name] = task
            
            # ON_DEMAND and REACTIVE agents don't need background tasks
            
            logger.debug(f"Started agent: {agent.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agent '{agent.name}': {e}")
            agent.status = AgentStatus.ERROR
            return False
    
    async def _stop_agent(self, name: str) -> None:
        """Stop an individual agent.
        
        Args:
            name: Agent name
        """
        agent = self._agents.get(name)
        if not agent:
            return
        
        agent.status = AgentStatus.STOPPED
        
        # Cancel task
        if name in self._agent_tasks:
            self._agent_tasks[name].cancel()
            try:
                await self._agent_tasks[name]
            except asyncio.CancelledError:
                pass
            del self._agent_tasks[name]
        
        # Teardown
        await agent.teardown()
        logger.debug(f"Stopped agent: {name}")
    
    async def _run_persistent_agent(self, agent: BaseAgent) -> None:
        """Run a persistent agent in a loop.
        
        Args:
            agent: Agent to run
        """
        while self._running and agent.status not in (AgentStatus.STOPPED, AgentStatus.ERROR):
            try:
                if agent.status == AgentStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                await agent.run()
                
                # Brief pause between runs
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Persistent agent '{agent.name}' error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _run_scheduled_agent(self, agent: BaseAgent) -> None:
        """Run a scheduled agent based on its schedule config.
        
        Args:
            agent: Agent to run
        """
        interval = agent.config.schedule_interval_seconds or 3600  # Default 1 hour
        
        while self._running and agent.status not in (AgentStatus.STOPPED, AgentStatus.ERROR):
            try:
                if agent.status == AgentStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                await agent.run()
                
                # Wait for next scheduled run
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled agent '{agent.name}' error: {e}")
                await asyncio.sleep(300)  # 5 min back off on error
    
    async def _health_monitor_loop(self) -> None:
        """Background task to monitor agent health."""
        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    async def _check_all_health(self) -> None:
        """Check health of all agents and restart failed ones."""
        for name, agent in self._agents.items():
            try:
                health = await agent.health_check()
                
                # Check for stuck agents
                if agent.status == AgentStatus.RUNNING:
                    # Agent has been running for too long
                    if agent._last_run:
                        runtime = (datetime.now() - agent._last_run).total_seconds()
                        if runtime > agent.config.max_runtime_seconds * 2:
                            logger.warning(f"Agent '{name}' appears stuck, restarting")
                            await self._stop_agent(name)
                            if self._auto_restart:
                                await self._start_agent(agent)
                
                # Check for error state
                if agent.status == AgentStatus.ERROR and self._auto_restart:
                    error_count = self._errors_by_agent[name]
                    if error_count < 5:  # Max 5 restart attempts
                        logger.info(f"Auto-restarting failed agent '{name}'")
                        agent.status = AgentStatus.IDLE
                        await self._start_agent(agent)
                    else:
                        logger.error(f"Agent '{name}' exceeded max restart attempts")
                
            except Exception as e:
                logger.error(f"Health check failed for '{name}': {e}")
    
    async def _on_agent_error(self, agent: BaseAgent, error: Exception) -> None:
        """Callback when an agent encounters an error.
        
        Args:
            agent: The agent that errored
            error: The exception
        """
        self._errors_by_agent[agent.name] += 1
        
        # Post to blackboard for other agents to see
        if self._blackboard:
            await self._blackboard.write(
                key=f"supervisor:error:{agent.name}:{datetime.now().timestamp()}",
                value={
                    "agent": agent.name,
                    "error": str(error),
                    "error_type": type(error).__name__,
                },
                source_agent="supervisor",
                tags=["error", "agent_failure"],
                ttl_seconds=86400,  # Keep for 24 hours
            )
    
    async def _on_agent_complete(self, agent: BaseAgent, result: AgentResult) -> None:
        """Callback when an agent completes execution.
        
        Args:
            agent: The agent that completed
            result: The execution result
        """
        self._total_runs += 1
        self._total_tokens_used += result.tokens_used
        
        # Post findings to blackboard
        if result.findings and self._blackboard:
            for finding in result.findings:
                await self._blackboard.write(
                    key=f"{agent.name}:finding:{datetime.now().timestamp()}",
                    value=finding,
                    source_agent=agent.name,
                    tags=["finding", agent.config.agent_type.value],
                )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics.
        
        Returns:
            Statistics dictionary
        """
        status_counts = defaultdict(int)
        for agent in self._agents.values():
            status_counts[agent.status.name] += 1
        
        return {
            "total_agents": len(self._agents),
            "running_agents": len(self._agent_tasks),
            "status_counts": dict(status_counts),
            "total_runs": self._total_runs,
            "total_tokens_used": self._total_tokens_used,
            "errors_by_agent": dict(self._errors_by_agent),
            "blackboard_stats": self._blackboard.get_stats() if self._blackboard else {},
        }


# Global supervisor instance
_global_supervisor: Optional[AgentSupervisor] = None


def get_agent_supervisor() -> AgentSupervisor:
    """Get or create the global supervisor instance.
    
    Returns:
        The global AgentSupervisor
    """
    global _global_supervisor
    if _global_supervisor is None:
        _global_supervisor = AgentSupervisor()
    return _global_supervisor

