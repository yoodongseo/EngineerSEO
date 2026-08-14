from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

def fixture(*args: Any, **kwargs: Any) -> Callable[[_F], _F]: ...

class _MarkProxy:
    asyncio: Any

mark: _MarkProxy
