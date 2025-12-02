"""Agent Scheduler - Cron-like scheduling for background agents.

Provides time-based scheduling for agent execution.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled task."""
    name: str
    interval_seconds: int  # Time between runs
    agent_name: str
    enabled: bool = True
    run_immediately: bool = False  # Run once at startup
    max_runtime_seconds: int = 300
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    def update_next_run(self) -> None:
        """Calculate the next run time."""
        self.next_run = datetime.now() + timedelta(seconds=self.interval_seconds)


class AgentScheduler:
    """Manages scheduled execution of agents.
    
    Features:
    - Interval-based scheduling
    - One-time scheduled tasks
    - Priority queuing
    - Execution history
    """
    
    def __init__(self):
        """Initialize the scheduler."""
        self._schedules: Dict[str, ScheduleConfig] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._execution_history: List[Dict[str, Any]] = []
        self._trigger_callbacks: Dict[str, Callable] = {}
        
        logger.info("AgentScheduler initialized")
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("AgentScheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("AgentScheduler stopped")
    
    def add_schedule(
        self,
        name: str,
        agent_name: str,
        interval_seconds: int,
        enabled: bool = True,
        run_immediately: bool = False,
    ) -> ScheduleConfig:
        """Add a new schedule.
        
        Args:
            name: Unique name for this schedule
            agent_name: Agent to trigger
            interval_seconds: Time between runs
            enabled: Whether schedule is active
            run_immediately: Run once at startup
            
        Returns:
            The created ScheduleConfig
        """
        config = ScheduleConfig(
            name=name,
            agent_name=agent_name,
            interval_seconds=interval_seconds,
            enabled=enabled,
            run_immediately=run_immediately,
        )
        config.update_next_run()
        
        self._schedules[name] = config
        logger.info(f"Added schedule '{name}' for agent '{agent_name}' every {interval_seconds}s")
        
        return config
    
    def remove_schedule(self, name: str) -> bool:
        """Remove a schedule.
        
        Args:
            name: Schedule name
            
        Returns:
            True if removed
        """
        if name in self._schedules:
            del self._schedules[name]
            logger.info(f"Removed schedule '{name}'")
            return True
        return False
    
    def enable_schedule(self, name: str) -> bool:
        """Enable a schedule."""
        if name in self._schedules:
            self._schedules[name].enabled = True
            return True
        return False
    
    def disable_schedule(self, name: str) -> bool:
        """Disable a schedule."""
        if name in self._schedules:
            self._schedules[name].enabled = False
            return True
        return False
    
    def register_trigger_callback(
        self,
        agent_name: str,
        callback: Callable
    ) -> None:
        """Register callback to be called when agent should run.
        
        Args:
            agent_name: Agent name
            callback: Async function to call
        """
        self._trigger_callbacks[agent_name] = callback
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        # Handle run_immediately schedules
        for config in self._schedules.values():
            if config.run_immediately and config.enabled:
                await self._trigger_agent(config)
        
        while self._running:
            try:
                now = datetime.now()
                
                for config in self._schedules.values():
                    if not config.enabled:
                        continue
                    
                    if config.next_run and now >= config.next_run:
                        await self._trigger_agent(config)
                        config.last_run = now
                        config.update_next_run()
                
                # Check every 10 seconds
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _trigger_agent(self, config: ScheduleConfig) -> None:
        """Trigger an agent based on schedule.
        
        Args:
            config: Schedule configuration
        """
        logger.info(f"Schedule '{config.name}' triggering agent '{config.agent_name}'")
        
        callback = self._trigger_callbacks.get(config.agent_name)
        if callback:
            try:
                await callback(config.agent_name)
                
                self._execution_history.append({
                    "schedule": config.name,
                    "agent": config.agent_name,
                    "time": datetime.now().isoformat(),
                    "success": True,
                })
            except Exception as e:
                logger.error(f"Failed to trigger agent '{config.agent_name}': {e}")
                self._execution_history.append({
                    "schedule": config.name,
                    "agent": config.agent_name,
                    "time": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e),
                })
        else:
            logger.warning(f"No callback registered for agent '{config.agent_name}'")
        
        # Trim history
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-1000:]
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules."""
        return [
            {
                "name": c.name,
                "agent_name": c.agent_name,
                "interval_seconds": c.interval_seconds,
                "enabled": c.enabled,
                "last_run": c.last_run.isoformat() if c.last_run else None,
                "next_run": c.next_run.isoformat() if c.next_run else None,
            }
            for c in self._schedules.values()
        ]
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return self._execution_history[-limit:]


# Global scheduler
_global_scheduler: Optional[AgentScheduler] = None


def get_agent_scheduler() -> AgentScheduler:
    """Get or create global scheduler."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = AgentScheduler()
    return _global_scheduler

