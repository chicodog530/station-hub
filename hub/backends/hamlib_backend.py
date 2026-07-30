from __future__ import annotations

import re
import socket
import threading

from hub.backends.backend import RigBackend, RigError
from hub.backends.state import AdvancedRigCapabilities, AdvancedRigState, RigCapabilities, RigState


# These are safe/useful controls to read when Hamlib advertises them.  The
# actual capability sets still come from the connected radio backend; this list
# only keeps an Advanced-window refresh from issuing dozens of obscure CAT
# queries on every radio.
_ADV_LEVEL_ORDER = (
    "RFPOWER", "RFPOWER_METER_WATTS", "RFPOWER_METER", "SWR", "ALC",
    "STRENGTH", "RAWSTR", "RF", "AF", "SQL", "MICGAIN", "COMP", "NR",
    "VOXGAIN", "AGC", "PREAMP", "ATT", "NOTCHF", "IF", "CWPITCH",
    "TEMP_METER", "VD_METER", "ID_METER", "USB_AF", "USB_AF_INPUT",
)


class HamlibRigctldBackend(RigBackend):
    """Persistent TCP client for Hamlib rigctld Extended Response Protocol."""

    name = "Hamlib rigctld"

    def __init__(self, host: str = "127.0.0.1", port: int = 4532, timeout: float = 5.0) -> None:
        self.host = str(host or "127.0.0.1")
        self.port = int(port)
        self.timeout = float(timeout)
        self._sock: socket.socket | None = None
        self._file = None
        self._lock = threading.RLock()

    def connect(self) -> None:
        self.close()
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            sock.settimeout(self.timeout)
            self._sock = sock
            self._file = sock.makefile("rwb", buffering=0)
        except OSError as exc:
            self.close()
            raise RigError(f"rigctld connection failed: {exc}") from exc

    def close(self) -> None:
        with self._lock:
            f, s = self._file, self._sock
            self._file = None; self._sock = None
            try:
                if f is not None: f.close()
            except Exception: pass
            try:
                if s is not None: s.close()
            except Exception: pass

    def _command_rows(self, long_command: str, override_timeout: float | None = None) -> list[str]:
        with self._lock:
            if self._file is None:
                raise RigError("rigctld is not connected")
            if override_timeout is not None:
                self._sock.settimeout(override_timeout)
            wire = ("+" + long_command.strip() + "\n").encode("ascii", "strict")
            try:
                self._file.write(wire)
                rows: list[str] = []
                while True:
                    raw = self._file.readline()
                    if not raw:
                        raise RigError("rigctld closed the connection")
                    line = raw.decode("utf-8", "replace").strip()
                    if line.startswith("RPRT "):
                        code = int(line.split(None, 1)[1])
                        if code != 0:
                            raise RigError(f"rigctld returned error {code} for {long_command}")
                        break
                    rows.append(line)
                return rows
            except (OSError, ValueError) as exc:
                raise RigError(f"rigctld command failed: {exc}") from exc
            finally:
                if override_timeout is not None:
                    self._sock.settimeout(self.timeout)

    def _command(self, long_command: str, override_timeout: float | None = None) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in self._command_rows(long_command, override_timeout=override_timeout):
            if ":" in line:
                key, value = line.split(":", 1)
                values[key.strip().lower().replace(" ", "_")] = value.strip()
        return values

    @staticmethod
    def _split_response_rows(rows: list[str]) -> tuple[dict[str, str], list[str]]:
        """Split rigctld response rows into labeled fields and bare values.

        Hamlib's Extended Response Protocol is not completely uniform across
        versions/backends.  Some advanced getters return e.g. ``Value: 0.5``
        while others return only ``0.5`` on a line by itself.  Preserve both
        forms so callers do not accidentally discard the actual meter/control
        value.
        """
        values: dict[str, str] = {}
        bare: list[str] = []
        for line in rows:
            text = str(line).strip()
            if not text:
                continue
            if ":" in text:
                key, value = text.split(":", 1)
                values[key.strip().lower().replace(" ", "_")] = value.strip()
            else:
                bare.append(text)
        return values, bare

    def _query_value(self, long_command: str, *keys: str, token: str = "") -> str:
        """Read a scalar from either labeled or bare rigctld output."""
        values, bare = self._split_response_rows(self._command_rows(long_command))

        for key in keys:
            value = values.get(key, "")
            if value:
                return value

        # Ignore common bare command/token echoes.  Prefer the last remaining
        # bare row because a few Hamlib versions/backends emit an echo before
        # the actual scalar value.
        ignored = {str(token).strip().upper()}
        command_name = str(long_command).strip().split(None, 1)[0].lstrip("\\+").upper()
        if command_name:
            ignored.add(command_name)
        for value in reversed(bare):
            if value.strip().upper() not in ignored and value.strip() != "?":
                return value.strip()

        # Last-resort labeled fallback, but never mistake the echoed capability
        # name itself (for example ``Level: RFPOWER``) for its numeric value.
        for value in reversed(tuple(values.values())):
            text = str(value).strip()
            if text and text.upper() not in ignored and text != "?":
                return text
        return ""

    @staticmethod
    def _pick(values: dict[str, str], *keys: str, default: str = "") -> str:
        for key in keys:
            if key in values: return values[key]
        return default

    @staticmethod
    def _number(value: str):
        text = str(value).strip()
        try:
            number = float(text)
            return int(number) if number.is_integer() else number
        except Exception:
            return text

    def _query_tokens(self, command: str) -> tuple[str, ...]:
        """Return capability tokens from rigctld's documented '?' queries."""
        try:
            rows = self._command_rows(command)
        except RigError:
            return ()
        tokens: list[str] = []
        for row in rows:
            text = row.split(":", 1)[1].strip() if ":" in row else row.strip()
            if not text or text == "?":
                continue
            for token in re.split(r"[\s,]+", text):
                token = token.strip().upper()
                if not token or token == "?" or token.endswith(":"):
                    continue
                # Capability names are symbolic Hamlib tokens.  This filter also
                # ignores echoed command labels such as "get_level".
                if re.fullmatch(r"[A-Z][A-Z0-9_/-]*", token) and not token.startswith("GET_") and not token.startswith("SET_"):
                    if token not in tokens:
                        tokens.append(token)
        return tuple(tokens)

    def _get_level(self, token: str):
        text = self._query_value(
            rf"\get_level {token}",
            "level_value", "value", token.lower(),
            token=token,
        )
        if text == "":
            raise RigError(f"No value returned for level {token}")
        return self._number(text)

    def _get_func(self, token: str) -> bool:
        text = self._query_value(
            rf"\get_func {token}",
            "func_status", "function_status", "status", "value",
            token=token,
        ) or "0"
        return str(text).strip().upper() not in {"0", "OFF", "FALSE", "NO"}

    def _get_parm(self, token: str):
        text = self._query_value(
            rf"\get_parm {token}",
            "parm_value", "parameter_value", "value",
            token=token,
        )
        if text == "": raise RigError(f"No value returned for parameter {token}")
        return self._number(text)

    def get_state(self) -> RigState:
        f = self._command(r"\get_freq")
        m = self._command(r"\get_mode")
        try: p = self._command(r"\get_ptt")
        except RigError: p = {}
        try: v = self._command(r"\get_vfo")
        except RigError: v = {}
        try: s = self._command(r"\get_split_vfo")
        except RigError: s = {}
        freq = int(float(self._pick(f, "frequency", "freq", default="0") or 0))
        mode = self._pick(m, "mode")
        bw = int(float(self._pick(m, "passband", default="0") or 0))
        ptt_text = self._pick(p, "ptt", default="")
        ptt = None if not ptt_text else ptt_text not in {"0", "OFF", "off"}
        vfo = self._pick(v, "vfo")
        split_text = self._pick(s, "split", default="")
        split = None if not split_text else split_text not in {"0", "OFF", "off"}
        return RigState(
            connected=True, backend="hamlib", frequency_hz=freq, mode=mode,
            bandwidth_hz=bw, vfo=vfo, split=split, ptt=ptt,
        ).touched()

    def set_frequency(self, frequency_hz: int) -> int:
        frequency_hz = int(frequency_hz)
        if frequency_hz <= 0: raise RigError("Frequency must be greater than zero")
        self._command(rf"\set_freq {frequency_hz}")
        return int(float(self._pick(self._command(r"\get_freq"), "frequency", "freq", default=str(frequency_hz))))

    def set_mode(self, mode: str) -> str:
        mode = str(mode).strip().upper()
        self._command(rf"\set_mode {mode} 0")
        return self._pick(self._command(r"\get_mode"), "mode", default=mode)

    def set_ptt(self, enabled: bool) -> None:
        self._command(rf"\set_ptt {1 if enabled else 0}")

    def get_advanced_state(self) -> AdvancedRigState:
        if not hasattr(self, "_cached_caps"):
            get_levels = self._query_tokens(r"\get_level ?")
            set_levels = self._query_tokens(r"\set_level ?")
            get_funcs = self._query_tokens(r"\get_func ?")
            set_funcs = self._query_tokens(r"\set_func ?")
            get_parms = self._query_tokens(r"\get_parm ?")
            set_parms = self._query_tokens(r"\set_parm ?")
            self._cached_caps = AdvancedRigCapabilities(
                get_levels=tuple(get_levels), set_levels=tuple(set_levels),
                get_functions=tuple(get_funcs), set_functions=tuple(set_funcs),
                get_parameters=tuple(get_parms), set_parameters=tuple(set_parms),
            )
            self._ordered_levels = [x for x in _ADV_LEVEL_ORDER if x in get_levels]

        levels: dict[str, float | int | str] = {}
        for token in self._ordered_levels:
            try: levels[token] = self._get_level(token)
            except RigError: pass

        functions: dict[str, bool] = {}
        for token in self._cached_caps.get_functions:
            try: functions[token] = self._get_func(token)
            except RigError: pass

        parameters: dict[str, float | int | str] = {}
        for token in self._cached_caps.get_parameters:
            try: parameters[token] = self._get_parm(token)
            except RigError: pass

        return AdvancedRigState(
            connected=True, backend="hamlib", capabilities=self._cached_caps,
            levels=levels, functions=functions, parameters=parameters,
        ).touched()

    def set_level(self, name: str, value: float | int | str) -> None:
        token = str(name).strip().upper()
        self._command(rf"\set_level {token} {value}")

    def set_function(self, name: str, enabled: bool) -> None:
        token = str(name).strip().upper()
        self._command(rf"\set_func {token} {1 if enabled else 0}")

    def set_parameter(self, name: str, value: float | int | str) -> None:
        token = str(name).strip().upper()
        self._command(rf"\set_parm {token} {value}")

    def capabilities(self) -> RigCapabilities:
        return RigCapabilities(
            frequency_read=True, frequency_write=True, mode_read=True, mode_write=True,
            ptt_read=True, ptt_write=True, vfo_read=True, split_read=True,
            bandwidth_read=True,
        )
