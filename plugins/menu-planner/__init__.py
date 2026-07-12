"""Menu Planner Hermes plugin package.

The plugin is an adapter layer. It must call the Application HTTP API and must
not import Domain Core, repositories, migrations, or database infrastructure.
"""

from __future__ import annotations

try:
    from .handlers import register_tools
    from .policy import pre_gateway_dispatch, pre_tool_call
    from .runtime_skills import register_runtime_skills
except ImportError:  # pragma: no cover - supports direct Hermes file loading.
    from handlers import register_tools  # type: ignore[no-redef]
    from policy import pre_gateway_dispatch, pre_tool_call  # type: ignore[no-redef]
    from runtime_skills import register_runtime_skills  # type: ignore[no-redef]


def register(ctx) -> None:
    """Register plugin capabilities.

    Tool handlers repeat critical checks before calling the Application HTTP
    API. Hooks are defense in depth.
    """

    register_tools(ctx)
    ctx.register_hook("pre_gateway_dispatch", pre_gateway_dispatch)
    ctx.register_hook("pre_tool_call", pre_tool_call)
    register_runtime_skills(ctx)
