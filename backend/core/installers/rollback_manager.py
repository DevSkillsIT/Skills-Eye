"""
Rollback Manager for automatic cleanup on installation failure
Implements LIFO (Last In, First Out) rollback stack
"""
import asyncio
import logging
from typing import Callable, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RollbackAction:
    """Represents a single rollback action"""

    name: str
    action: Callable[..., Any]  # Can be sync or async
    args: tuple = ()
    kwargs: dict = None
    description: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class RollbackManager:
    """
    Manages rollback actions in LIFO order
    Automatically cleans up on installation failure
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], Any]] = None):
        """
        Initialize rollback manager

        Args:
            log_callback: Optional async callback(message, level) for logging
        """
        self.actions: List[RollbackAction] = []
        self.log_callback = log_callback
        self.enabled = True

    async def log(self, message: str, level: str = "info"):
        """Log message via callback or logger"""
        if self.log_callback:
            if asyncio.iscoroutinefunction(self.log_callback):
                await self.log_callback(message, level)
            else:
                self.log_callback(message, level)
        else:
            getattr(logger, level, logger.info)(message)

    def add_action(
        self,
        name: str,
        action: Callable,
        *args,
        description: str = "",
        **kwargs
    ):
        """
        Add rollback action to stack

        Actions are executed in reverse order (LIFO) during rollback

        Args:
            name: Action identifier
            action: Callable to execute (sync or async)
            *args: Positional arguments for action
            description: Human-readable description
            **kwargs: Keyword arguments for action

        Example:
            rollback.add_action(
                "remove_file",
                os.remove,
                "/tmp/installer.sh",
                description="Remove downloaded installer"
            )
        """
        if not self.enabled:
            return

        rollback_action = RollbackAction(
            name=name,
            action=action,
            args=args,
            kwargs=kwargs,
            description=description or name,
        )

        self.actions.append(rollback_action)
        logger.debug(f"[Rollback] Added action: {name} ({len(self.actions)} total)")

    async def execute(self) -> bool:
        """
        Execute all rollback actions in LIFO order

        Returns:
            True if all actions succeeded, False if any failed
        """
        if not self.actions:
            await self.log("Nenhuma ação de rollback necessária", "info")
            return True

        await self.log("", "warning")
        await self.log("=" * 60, "warning")
        await self.log("🔄 INICIANDO ROLLBACK AUTOMÁTICO", "warning")
        await self.log("=" * 60, "warning")
        await self.log(f"Total de ações a reverter: {len(self.actions)}", "warning")
        await self.log("", "warning")

        success = True
        failed_actions = []

        # Execute in reverse order (LIFO)
        for i, action in enumerate(reversed(self.actions), 1):
            try:
                await self.log(
                    f"[{i}/{len(self.actions)}] Revertendo: {action.description}",
                    "info"
                )

                # Execute action (handle both sync and async)
                if asyncio.iscoroutinefunction(action.action):
                    await action.action(*action.args, **action.kwargs)
                else:
                    # Run sync function in thread pool
                    await asyncio.to_thread(action.action, *action.args, **action.kwargs)

                await self.log(f"✅ Sucesso: {action.name}", "success")

            except Exception as e:
                error_msg = f"❌ Falha ao reverter '{action.name}': {str(e)}"
                await self.log(error_msg, "error")
                logger.error(f"[Rollback] {error_msg}", exc_info=True)
                failed_actions.append(action.name)
                success = False

                # Continue with other rollback actions even if one fails
                continue

        # Summary
        await self.log("", "warning")
        await self.log("=" * 60, "warning")

        if success:
            await self.log("✅ ROLLBACK CONCLUÍDO COM SUCESSO", "success")
        else:
            await self.log(
                f"⚠️  ROLLBACK CONCLUÍDO COM FALHAS ({len(failed_actions)} ações falharam)",
                "warning"
            )
            await self.log(f"Ações que falharam: {', '.join(failed_actions)}", "warning")

        await self.log("=" * 60, "warning")

        return success

    def disable(self):
        """Disable rollback (useful when installation succeeds)"""
        self.enabled = False
        logger.debug("[Rollback] Disabled - installation succeeded")

    def clear(self):
        """Clear all rollback actions"""
        self.actions.clear()
        logger.debug("[Rollback] Cleared all actions")

    def __len__(self) -> int:
        """Return number of rollback actions"""
        return len(self.actions)

    def __bool__(self) -> bool:
        """Return True if there are rollback actions"""
        return bool(self.actions)


# Context manager for automatic rollback
class RollbackContext:
    """
    Context manager for automatic rollback on exception

    Usage:
        async with RollbackContext(log_callback) as rollback:
            rollback.add_action("cleanup", cleanup_func)
            # ... installation code
            # If exception occurs, rollback executes automatically
            rollback.disable()  # Call this on success to skip rollback
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], Any]] = None):
        self.manager = RollbackManager(log_callback)

    async def __aenter__(self) -> RollbackManager:
        return self.manager

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Execute rollback only if exception occurred and manager is enabled
        if exc_type is not None and self.manager.enabled:
            await self.manager.log(
                f"Exceção detectada: {exc_type.__name__}: {exc_val}",
                "error"
            )
            await self.manager.execute()

        # Don't suppress exception
        return False


__all__ = [
    'RollbackAction',
    'RollbackManager',
    'RollbackContext',
]
