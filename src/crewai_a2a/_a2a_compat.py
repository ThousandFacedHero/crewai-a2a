"""Patch a2a-sdk 1.0.x so CrewAI 1.14.4's a2a integration can import successfully.

CrewAI 1.14.4 was authored against a2a-sdk ~0.3.x. The 1.0.x SDK moved to
protobuf-backed types (TASK_STATE_COMPLETED) and reorganized its module
layout. The 1.0.x SDK ships a2a.compat.v0_3.types with Pydantic models that
match the old API (TaskState.completed, Role.user, TextPart, etc.).

This module overlays those compat types onto a2a.types so CrewAI's imports
resolve correctly, then patches two remaining module-level gaps.

Import this module before any crewai.a2a import.
"""

import sys
import types as _types_mod

import a2a.compat.v0_3.types as _compat_types
import a2a.types as _a2a_types

# 1. Overlay every public name from the 0.3.x compat layer onto a2a.types.
#    This replaces protobuf enums (TaskState, Role) and adds missing types
#    (TextPart, TaskQueryParams, etc.) while keeping a2a.types as a real
#    package so a2a.types.a2a_pb2 still resolves.
for _name in dir(_compat_types):
    if not _name.startswith("_"):
        setattr(_a2a_types, _name, getattr(_compat_types, _name))

# 2. A2AClientHTTPError → alias to A2AClientError.
import a2a.client.errors as _a2a_errors

if not hasattr(_a2a_errors, "A2AClientHTTPError"):
    _a2a_errors.A2AClientHTTPError = _a2a_errors.A2AClientError  # type: ignore[attr-defined]

# 3. a2a.client.middleware → synthesize from a2a.client + a2a.client.interceptors.
if "a2a.client.middleware" not in sys.modules:
    import a2a.client as _a2a_client
    import a2a.client.interceptors as _interceptors

    _middleware_mod = _types_mod.ModuleType("a2a.client.middleware")
    _middleware_mod.ClientCallContext = _a2a_client.ClientCallContext  # type: ignore[attr-defined]
    _middleware_mod.ClientCallInterceptor = _interceptors.ClientCallInterceptor  # type: ignore[attr-defined]
    sys.modules["a2a.client.middleware"] = _middleware_mod
