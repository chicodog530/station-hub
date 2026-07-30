from __future__ import annotations

from abc import ABC, abstractmethod

from hub.backends.state import AdvancedRigState, RigCapabilities, RigState


class RigError(RuntimeError):
    pass


class RigBackend(ABC):
    name = "rig"

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def get_state(self) -> RigState: ...

    @abstractmethod
    def set_frequency(self, frequency_hz: int) -> int: ...

    def set_mode(self, mode: str) -> str:
        raise RigError(f"{self.name} does not support setting mode")

    def set_ptt(self, enabled: bool) -> None:
        raise RigError(f"{self.name} does not support PTT")

    def get_advanced_state(self) -> AdvancedRigState:
        return AdvancedRigState(connected=True, backend=self.name).touched()

    def set_level(self, name: str, value: float | int | str) -> None:
        raise RigError(f"{self.name} does not support advanced level {name}")

    def set_function(self, name: str, enabled: bool) -> None:
        raise RigError(f"{self.name} does not support advanced function {name}")

    def set_parameter(self, name: str, value: float | int | str) -> None:
        raise RigError(f"{self.name} does not support advanced parameter {name}")

    def capabilities(self) -> RigCapabilities:
        return RigCapabilities()
