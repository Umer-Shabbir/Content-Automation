import asyncio
import inspect
from typing import Any, Callable, Dict, List, Awaitable
from collections import defaultdict
import threading

class EventBus:
    def __init__(self):
        # We need a lock for thread safety on subscribers dict
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Subscribe a callback (sync or async) to an event type."""
        with self._lock:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Unsubscribe a callback from an event type."""
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    async def publish(self, event_type: str, *args: Any, **kwargs: Any) -> None:
        """Publish an event to all subscribers of event_type.
        Calls each subscriber. Async callbacks are awaited.
        """
        with self._lock:
            # Copy the list to avoid modifying during iteration
            subscribers = list(self._subscribers.get(event_type, []))

        # We can run these concurrently or sequentially.
        # For simplicity and predictability, let's run them sequentially.
        for callback in subscribers:
            if inspect.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                # If the bus is called from an async context, running sync calls directly could block the event loop if they are long.
                # But for a simple event bus, we just call them directly inline.
                callback(*args, **kwargs)

    def publish_sync(self, event_type: str, *args: Any, **kwargs: Any) -> None:
        """Publish an event synchronously.
        Only sync subscribers are immediately executed.
        Async subscribers are scheduled as background tasks on the current event loop.
        """
        with self._lock:
            subscribers = list(self._subscribers.get(event_type, []))

        for callback in subscribers:
            if inspect.iscoroutinefunction(callback):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(callback(*args, **kwargs))
                except RuntimeError:
                    # No running loop, cannot schedule async tasks effectively without asyncio.run
                    asyncio.run(callback(*args, **kwargs))
            else:
                callback(*args, **kwargs)

# A global instance for easy use
default_bus = EventBus()
