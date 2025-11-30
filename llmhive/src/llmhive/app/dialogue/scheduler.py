"""Task Scheduler for LLMHive.

Enables scheduled tasks and reminders:
- Parse schedule requests from queries
- Schedule reminders and notifications
- Execute scheduled tasks at the right time

Usage:
    scheduler = get_task_scheduler()
    
    # Schedule a reminder
    task = await scheduler.schedule_reminder(
        user_id="user123",
        message="Check the oven",
        delay_seconds=3600,  # 1 hour
    )
    
    # Schedule at specific time
    task = await scheduler.schedule_at(
        user_id="user123",
        message="Meeting reminder",
        run_at=datetime(2025, 1, 15, 14, 0),
    )
"""
from __future__ import annotations

import asyncio
import heapq
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class TaskStatus(str, Enum):
    """Status of a scheduled task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of scheduled tasks."""
    REMINDER = "reminder"
    NOTIFICATION = "notification"
    RECURRING = "recurring"
    DELAYED_ACTION = "delayed_action"


@dataclass
class ScheduledTask:
    """A scheduled task."""
    id: str
    user_id: str
    task_type: TaskType
    message: str
    run_at: datetime
    status: TaskStatus = TaskStatus.PENDING
    
    # Optional fields
    session_id: Optional[str] = None
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Execution info
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Recurring task config
    recurrence_interval: Optional[timedelta] = None
    recurrence_count: int = 0
    max_recurrences: int = 0
    
    def __lt__(self, other):
        """For heap ordering."""
        return self.run_at < other.run_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_type": self.task_type.value,
            "message": self.message,
            "run_at": self.run_at.isoformat(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


# ==============================================================================
# Time Parsing
# ==============================================================================

# Patterns for parsing time expressions
TIME_PATTERNS = [
    # "in X minutes/hours/days"
    (r"in\s+(\d+)\s*(minute|minutes|min|mins)", lambda m: timedelta(minutes=int(m.group(1)))),
    (r"in\s+(\d+)\s*(hour|hours|hr|hrs)", lambda m: timedelta(hours=int(m.group(1)))),
    (r"in\s+(\d+)\s*(day|days)", lambda m: timedelta(days=int(m.group(1)))),
    (r"in\s+(\d+)\s*(second|seconds|sec|secs)", lambda m: timedelta(seconds=int(m.group(1)))),
    (r"in\s+(\d+)\s*(week|weeks)", lambda m: timedelta(weeks=int(m.group(1)))),
    
    # "X minutes/hours from now"
    (r"(\d+)\s*(minute|minutes|min)\s+from\s+now", lambda m: timedelta(minutes=int(m.group(1)))),
    (r"(\d+)\s*(hour|hours|hr)\s+from\s+now", lambda m: timedelta(hours=int(m.group(1)))),
    
    # "tomorrow"
    (r"\btomorrow\b", lambda m: timedelta(days=1)),
    
    # "in half an hour"
    (r"in\s+half\s+an?\s+hour", lambda m: timedelta(minutes=30)),
    
    # "in an hour"
    (r"in\s+an?\s+hour", lambda m: timedelta(hours=1)),
]

# Pattern for schedule tool format
SCHEDULE_TOOL_PATTERN = re.compile(
    r'\[TOOL:schedule\]\s*(?P<when>.+?)\s*\|\s*(?P<task>.+)',
    re.IGNORECASE
)

# Pattern for reminder requests
REMINDER_PATTERNS = [
    re.compile(r"remind\s+me\s+(?P<when>in\s+\d+\s+\w+)\s+(?:to\s+)?(?P<task>.+)", re.IGNORECASE),
    re.compile(r"set\s+(?:a\s+)?reminder\s+(?P<when>in\s+\d+\s+\w+)\s+(?:to\s+)?(?P<task>.+)", re.IGNORECASE),
    re.compile(r"(?:in\s+)?(?P<when>\d+\s+\w+)\s+remind\s+me\s+(?:to\s+)?(?P<task>.+)", re.IGNORECASE),
]


def parse_time_expression(text: str) -> Optional[timedelta]:
    """Parse a time expression into a timedelta."""
    text_lower = text.lower().strip()
    
    for pattern, converter in TIME_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            try:
                return converter(match)
            except Exception:
                continue
    
    return None


def parse_reminder_request(text: str) -> Optional[Tuple[timedelta, str]]:
    """
    Parse a reminder request from user text.
    
    Args:
        text: User's message
        
    Returns:
        (delay, task_description) or None
    """
    for pattern in REMINDER_PATTERNS:
        match = pattern.search(text)
        if match:
            when = match.group("when")
            task = match.group("task")
            
            delay = parse_time_expression(when)
            if delay:
                return delay, task.strip()
    
    return None


# ==============================================================================
# Task Scheduler
# ==============================================================================

class TaskScheduler:
    """Scheduler for delayed tasks and reminders.
    
    Features:
    - Schedule reminders with natural language time parsing
    - Execute callbacks when tasks are due
    - Support for recurring tasks
    - Persistent task storage (optional)
    
    Usage:
        scheduler = TaskScheduler()
        await scheduler.start()
        
        # Schedule a reminder
        task = await scheduler.schedule_reminder(
            user_id="user123",
            message="Check the oven",
            delay_seconds=3600,
        )
        
        # Register callback for notifications
        scheduler.on_task_due(my_callback)
    """
    
    def __init__(
        self,
        check_interval: float = 1.0,
        max_tasks_per_user: int = 10,
    ):
        self.check_interval = check_interval
        self.max_tasks_per_user = max_tasks_per_user
        
        # Task storage
        self._tasks: Dict[str, ScheduledTask] = {}
        self._task_heap: List[ScheduledTask] = []
        self._user_tasks: Dict[str, List[str]] = {}
        
        # Callbacks
        self._callbacks: List[Callable[[ScheduledTask], Coroutine]] = []
        
        # State
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return
        
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("Task scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Task scheduler stopped")
    
    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_due_tasks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler loop error: %s", e)
    
    async def _check_due_tasks(self) -> None:
        """Check and execute due tasks."""
        now = datetime.now(timezone.utc)
        
        while self._task_heap:
            # Peek at next task
            task = self._task_heap[0]
            
            if task.status != TaskStatus.PENDING:
                # Remove completed/cancelled tasks
                heapq.heappop(self._task_heap)
                continue
            
            if task.run_at > now:
                # Not due yet
                break
            
            # Task is due
            heapq.heappop(self._task_heap)
            await self._execute_task(task)
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a due task."""
        logger.info("Executing task %s for user %s", task.id, task.user_id)
        
        task.status = TaskStatus.RUNNING
        task.executed_at = datetime.now(timezone.utc)
        
        try:
            # Call all registered callbacks
            for callback in self._callbacks:
                try:
                    await callback(task)
                except Exception as e:
                    logger.error("Task callback error: %s", e)
            
            task.status = TaskStatus.COMPLETED
            
            # Handle recurring tasks
            if task.recurrence_interval and task.recurrence_count < task.max_recurrences:
                await self._schedule_recurrence(task)
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error("Task execution failed: %s", e)
    
    async def _schedule_recurrence(self, task: ScheduledTask) -> None:
        """Schedule next occurrence of a recurring task."""
        next_run = task.run_at + task.recurrence_interval
        
        new_task = ScheduledTask(
            id=f"{task.id}_r{task.recurrence_count + 1}",
            user_id=task.user_id,
            task_type=task.task_type,
            message=task.message,
            run_at=next_run,
            session_id=task.session_id,
            callback_url=task.callback_url,
            metadata=task.metadata,
            recurrence_interval=task.recurrence_interval,
            recurrence_count=task.recurrence_count + 1,
            max_recurrences=task.max_recurrences,
        )
        
        self._add_task(new_task)
    
    def on_task_due(
        self,
        callback: Callable[[ScheduledTask], Coroutine],
    ) -> None:
        """Register callback for when tasks are due."""
        self._callbacks.append(callback)
    
    def _add_task(self, task: ScheduledTask) -> None:
        """Add task to scheduler."""
        self._tasks[task.id] = task
        heapq.heappush(self._task_heap, task)
        
        # Track per-user
        if task.user_id not in self._user_tasks:
            self._user_tasks[task.user_id] = []
        self._user_tasks[task.user_id].append(task.id)
    
    async def schedule_reminder(
        self,
        user_id: str,
        message: str,
        delay_seconds: int,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """
        Schedule a reminder.
        
        Args:
            user_id: User ID to notify
            message: Reminder message
            delay_seconds: Seconds until reminder
            session_id: Optional session ID
            metadata: Optional metadata
            
        Returns:
            ScheduledTask object
        """
        # Check user limit
        user_task_count = len(self._user_tasks.get(user_id, []))
        if user_task_count >= self.max_tasks_per_user:
            raise ValueError(f"User {user_id} has reached maximum scheduled tasks")
        
        run_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        task = ScheduledTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            task_type=TaskType.REMINDER,
            message=message,
            run_at=run_at,
            session_id=session_id,
            metadata=metadata or {},
        )
        
        self._add_task(task)
        
        logger.info(
            "Scheduled reminder for user %s in %d seconds: %s",
            user_id, delay_seconds, message[:50],
        )
        
        return task
    
    async def schedule_at(
        self,
        user_id: str,
        message: str,
        run_at: datetime,
        task_type: TaskType = TaskType.REMINDER,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """
        Schedule task at a specific time.
        
        Args:
            user_id: User ID
            message: Task message
            run_at: When to execute
            task_type: Type of task
            session_id: Optional session ID
            metadata: Optional metadata
            
        Returns:
            ScheduledTask object
        """
        # Ensure timezone-aware
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=timezone.utc)
        
        task = ScheduledTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            task_type=task_type,
            message=message,
            run_at=run_at,
            session_id=session_id,
            metadata=metadata or {},
        )
        
        self._add_task(task)
        return task
    
    async def schedule_recurring(
        self,
        user_id: str,
        message: str,
        interval: timedelta,
        max_occurrences: int = 10,
        session_id: Optional[str] = None,
    ) -> ScheduledTask:
        """
        Schedule a recurring task.
        
        Args:
            user_id: User ID
            message: Task message
            interval: Time between occurrences
            max_occurrences: Maximum times to repeat
            session_id: Optional session ID
            
        Returns:
            ScheduledTask object
        """
        run_at = datetime.now(timezone.utc) + interval
        
        task = ScheduledTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            task_type=TaskType.RECURRING,
            message=message,
            run_at=run_at,
            session_id=session_id,
            recurrence_interval=interval,
            recurrence_count=0,
            max_recurrences=max_occurrences,
        )
        
        self._add_task(task)
        return task
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            logger.info("Cancelled task %s", task_id)
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def get_user_tasks(
        self,
        user_id: str,
        include_completed: bool = False,
    ) -> List[ScheduledTask]:
        """Get all tasks for a user."""
        task_ids = self._user_tasks.get(user_id, [])
        tasks = [self._tasks[tid] for tid in task_ids if tid in self._tasks]
        
        if not include_completed:
            tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
        
        return sorted(tasks, key=lambda t: t.run_at)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
        completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
        
        return {
            "total_tasks": len(self._tasks),
            "pending_tasks": pending,
            "completed_tasks": completed,
            "users_with_tasks": len(self._user_tasks),
            "scheduler_running": self._running,
        }


# ==============================================================================
# Tool Handler
# ==============================================================================

async def schedule_tool_handler(
    when: str,
    task: str,
    user_id: str,
    session_id: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Handle [TOOL:schedule] requests.
    
    Args:
        when: Time expression (e.g., "in 1 hour")
        task: Task description
        user_id: User ID
        session_id: Session ID
        
    Returns:
        Result dict
    """
    scheduler = get_task_scheduler()
    
    # Parse time expression
    delay = parse_time_expression(when)
    if not delay:
        return {
            "success": False,
            "error": f"Could not understand time expression: {when}",
        }
    
    # Schedule the task
    scheduled_task = await scheduler.schedule_reminder(
        user_id=user_id,
        message=task,
        delay_seconds=int(delay.total_seconds()),
        session_id=session_id,
    )
    
    return {
        "success": True,
        "task_id": scheduled_task.id,
        "message": f"I'll remind you to '{task}' {when}.",
        "run_at": scheduled_task.run_at.isoformat(),
    }


# ==============================================================================
# Global Instance
# ==============================================================================

_scheduler: Optional[TaskScheduler] = None


def get_task_scheduler() -> TaskScheduler:
    """Get or create global task scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


async def start_scheduler() -> TaskScheduler:
    """Start the global scheduler."""
    scheduler = get_task_scheduler()
    await scheduler.start()
    return scheduler

