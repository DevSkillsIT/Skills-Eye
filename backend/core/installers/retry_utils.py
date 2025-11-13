"""
Retry utilities with exponential backoff
Handles transient failures in remote operations
"""
import asyncio
import logging
from typing import Callable, TypeVar, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Transient error patterns that should trigger retry
TRANSIENT_ERROR_PATTERNS = [
    'timeout',
    'connection refused',
    'connection reset',
    'broken pipe',
    'temporarily unavailable',
    'too many open files',
    'resource temporarily unavailable',
    'network is unreachable',
    'no route to host',
]


def is_transient_error(error: Exception) -> bool:
    """
    Check if error is transient and worth retrying

    Args:
        error: Exception to check

    Returns:
        True if error appears to be transient
    """
    error_msg = str(error).lower()

    # Check against known transient patterns
    for pattern in TRANSIENT_ERROR_PATTERNS:
        if pattern in error_msg:
            return True

    # Check specific exception types
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return True

    return False


async def retry_with_backoff(
    func: Callable[..., T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retry_on_transient: bool = True,
    log_callback: Optional[Callable[[str, str], Any]] = None,
) -> T:
    """
    Retry async function with exponential backoff

    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between attempts (default: 30.0)
        backoff_factor: Exponential backoff multiplier (default: 2.0)
        retry_on_transient: Only retry on transient errors (default: True)
        log_callback: Optional async callback(message, level) for logging

    Returns:
        Result of successful function call

    Raises:
        Exception: Last exception if all attempts fail
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(1, max_attempts + 1):
        try:
            if log_callback and attempt > 1:
                await log_callback(
                    f"Tentativa {attempt}/{max_attempts} após falha...",
                    "info"
                )

            result = await func()
            return result

        except Exception as e:
            last_exception = e
            is_final_attempt = attempt == max_attempts

            # Check if we should retry
            should_retry = not retry_on_transient or is_transient_error(e)

            if is_final_attempt or not should_retry:
                if log_callback:
                    await log_callback(
                        f"Falha definitiva após {attempt} tentativa(s): {str(e)}",
                        "error"
                    )
                raise e

            # Log retry
            if log_callback:
                await log_callback(
                    f"Erro transiente (tentativa {attempt}/{max_attempts}): {str(e)}. "
                    f"Aguardando {delay:.1f}s antes de retry...",
                    "warning"
                )
            else:
                logger.warning(
                    f"Retry {attempt}/{max_attempts} after error: {e}. "
                    f"Waiting {delay:.1f}s..."
                )

            # Wait with exponential backoff
            await asyncio.sleep(delay)

            # Increase delay for next attempt
            delay = min(delay * backoff_factor, max_delay)

    # Should never reach here, but just in case
    raise last_exception


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retry_on_transient: bool = True,
):
    """
    Decorator for async functions to add retry logic

    Usage:
        @with_retry(max_attempts=5, initial_delay=2.0)
        async def my_function():
            # ... code that may fail transiently

    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between attempts
        backoff_factor: Exponential backoff multiplier
        retry_on_transient: Only retry on transient errors
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async def execute():
                return await func(*args, **kwargs)

            return await retry_with_backoff(
                execute,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                retry_on_transient=retry_on_transient,
            )

        return wrapper

    return decorator


async def retry_ssh_command(
    execute_func: Callable[..., tuple[int, str, str]],
    command: str,
    max_attempts: int = 3,
    log_callback: Optional[Callable[[str, str], Any]] = None,
) -> tuple[int, str, str]:
    """
    Retry SSH command execution with backoff

    Args:
        execute_func: Async function that executes SSH command
        command: Command to execute
        max_attempts: Maximum number of attempts
        log_callback: Optional logging callback

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    async def execute():
        return await execute_func(command)

    return await retry_with_backoff(
        execute,
        max_attempts=max_attempts,
        initial_delay=0.5,
        max_delay=5.0,
        backoff_factor=2.0,
        retry_on_transient=True,
        log_callback=log_callback,
    )


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        retry_on_transient: bool = True,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retry_on_transient = retry_on_transient

    # Predefined configs for common scenarios
    @classmethod
    def aggressive(cls) -> 'RetryConfig':
        """Aggressive retry: 5 attempts, quick backoff"""
        return cls(max_attempts=5, initial_delay=0.5, max_delay=10.0, backoff_factor=1.5)

    @classmethod
    def conservative(cls) -> 'RetryConfig':
        """Conservative retry: 3 attempts, slow backoff"""
        return cls(max_attempts=3, initial_delay=2.0, max_delay=60.0, backoff_factor=3.0)

    @classmethod
    def network_operation(cls) -> 'RetryConfig':
        """Network operations: 4 attempts, moderate backoff"""
        return cls(max_attempts=4, initial_delay=1.0, max_delay=20.0, backoff_factor=2.0)

    @classmethod
    def file_operation(cls) -> 'RetryConfig':
        """File operations: 3 attempts, quick backoff"""
        return cls(max_attempts=3, initial_delay=0.5, max_delay=5.0, backoff_factor=2.0)


__all__ = [
    'retry_with_backoff',
    'with_retry',
    'retry_ssh_command',
    'is_transient_error',
    'RetryConfig',
    'TRANSIENT_ERROR_PATTERNS',
]
