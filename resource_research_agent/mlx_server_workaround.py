from __future__ import annotations

from collections.abc import Callable
from typing import Any


WORKAROUND_VERSION = "arrays-cache-materialization-v1"


def install_arrays_cache_materialization(
    cache_class: type,
    async_eval: Callable[..., Any],
) -> bool:
    """Materialize Qwen hybrid-cache metadata before its lazy graph can grow."""
    if getattr(cache_class, "_resource_scout_materialization", False):
        return False

    original_advance = cache_class.advance

    def advance(self: Any, count: int) -> None:
        original_advance(self, count)
        pending = [
            value
            for value in (self.lengths, self.left_padding)
            if value is not None
        ]
        if pending:
            async_eval(*pending)

    cache_class.advance = advance
    cache_class._resource_scout_materialization = True
    return True


def main() -> int:
    import mlx.core as mx
    from mlx_lm.models.cache import ArraysCache
    from mlx_lm.server import main as mlx_server_main

    install_arrays_cache_materialization(ArraysCache, mx.async_eval)
    print(
        f"Resource Scout MLX workaround active: {WORKAROUND_VERSION}",
        flush=True,
    )
    result = mlx_server_main()
    return int(result) if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
