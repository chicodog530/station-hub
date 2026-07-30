from __future__ import annotations

from dataclasses import dataclass, field, replace
import time


@dataclass(frozen=True)
class RigCapabilities:
    frequency_read: bool = True
    frequency_write: bool = True
    mode_read: bool = True
    mode_write: bool = True
    ptt_read: bool = False
    ptt_write: bool = False
    vfo_read: bool = False
    split_read: bool = False
    bandwidth_read: bool = False


@dataclass(frozen=True)
class AdvancedRigCapabilities:
    """Runtime-discovered advanced controls exposed by the selected backend.

    Hamlib fills these sets from rigctld's own capability queries, so the UI can
    expose only controls that the active radio backend says it implements.
    flrig/YWD-Rig fills them by probing the documented XML-RPC methods.
    """

    get_levels: tuple[str, ...] = ()
    set_levels: tuple[str, ...] = ()
    get_functions: tuple[str, ...] = ()
    set_functions: tuple[str, ...] = ()
    get_parameters: tuple[str, ...] = ()
    set_parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdvancedRigState:
    connected: bool = False
    backend: str = "disabled"
    model: str = ""
    capabilities: AdvancedRigCapabilities = field(default_factory=AdvancedRigCapabilities)
    levels: dict[str, float | int | str] = field(default_factory=dict)
    functions: dict[str, bool] = field(default_factory=dict)
    parameters: dict[str, float | int | str] = field(default_factory=dict)
    error: str = ""
    updated_at: float = 0.0

    def touched(self, **changes) -> "AdvancedRigState":
        return replace(self, updated_at=time.time(), **changes)


@dataclass(frozen=True)
class RigState:
    connected: bool = False
    backend: str = "disabled"
    model: str = ""
    frequency_hz: int = 0
    mode: str = ""
    bandwidth_hz: int = 0
    vfo: str = ""
    split: bool | None = None
    ptt: bool | None = None
    error: str = ""
    updated_at: float = 0.0

    def touched(self, **changes) -> "RigState":
        return replace(self, updated_at=time.time(), **changes)
