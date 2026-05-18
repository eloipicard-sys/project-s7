"""
Cascade PI+P controller for the thermal process.

Inner loop: Tin1 (measured) -> F1_SP (output)   — PI with P on measurement
Outer loop: Tout2 (measured) -> Tin1_SP (output)  — Proportional
"""
import threading
from typing import Optional


class PIplusP:
    """
    Discrete PI — velocity (incremental) form with proportional on measurement.
    Avoids proportional kick on setpoint step changes.
    Call init_output() before switching from manual to auto for bumpless transfer.
    """

    def __init__(self, Kp: float = 1.0, Ti: float = 60.0,
                 out_min: float = 0.0, out_max: float = 10.0, dt: float = 3.0):
        self.Kp = Kp
        self.Ti = Ti
        self.out_min = out_min
        self.out_max = out_max
        self.dt = dt
        self.last_output: float = (out_min + out_max) / 2.0
        self._last_meas: Optional[float] = None

    def update(self, setpoint: float, measurement: float) -> float:
        if self._last_meas is None:
            self._last_meas = measurement
        error = setpoint - measurement
        # Velocity form: du = -Kp*(dy) + (Kp/Ti)*e*dt
        delta_u = (-self.Kp * (measurement - self._last_meas)
                   + (self.Kp / max(self.Ti, 0.01)) * error * self.dt)
        raw = self.last_output + delta_u
        clamped = max(self.out_min, min(self.out_max, raw))
        self.last_output = clamped
        self._last_meas = measurement
        return clamped

    def init_output(self, current_output: float, current_meas: float):
        self.last_output = current_output
        self._last_meas = current_meas


class CascadeController:
    """
    Two-level cascade controller.

    Modes:
        'manual'      — no automatic output
        'auto_inner'  — inner PI+P active (Tin1 -> F1_SP), outer setpoint manual
        'auto_full'   — both loops active (Tout2_SP -> Tin1_SP -> F1_SP)
    """

    MODE_MANUAL     = 'manual'
    MODE_AUTO_INNER = 'auto_inner'
    MODE_AUTO_FULL  = 'auto_full'

    def __init__(self):
        self._lock = threading.Lock()
        self.mode: str = self.MODE_MANUAL

        # Inner PI+P: Tin1 -> F1_SP (m3/h)
        self.inner = PIplusP(Kp=1.0, Ti=60.0, out_min=0.0, out_max=10.0, dt=3.0)

        # Outer proportional: Tout2 -> Tin1_SP (°C)
        self.outer_Kp: float = 2.0
        self.outer_out_min: float = 20.0
        self.outer_out_max: float = 200.0

        # Setpoints (operator input)
        self.Tout2_SP: float = 50.0
        self.Tin1_SP: float  = 60.0

        # Last computed values (for status display)
        self.Tin1_SP_cmd: float = 60.0
        self.F1_SP_out: float   = 0.0
        self.last_Tin1: Optional[float]  = None
        self.last_Tout2: Optional[float] = None

    def update(self, Tin1: float, Tout2: float) -> Optional[float]:
        """
        Run one control cycle. Returns F1_SP to write, or None if manual.
        Called every dt seconds from the poll thread.
        """
        with self._lock:
            self.last_Tin1  = Tin1
            self.last_Tout2 = Tout2

            if self.mode == self.MODE_MANUAL:
                return None

            if self.mode == self.MODE_AUTO_FULL:
                raw = self.Tin1_SP + self.outer_Kp * (self.Tout2_SP - Tout2)
                self.Tin1_SP_cmd = max(self.outer_out_min, min(self.outer_out_max, raw))
            else:
                self.Tin1_SP_cmd = self.Tin1_SP

            F1_SP = self.inner.update(self.Tin1_SP_cmd, Tin1)
            self.F1_SP_out = F1_SP
            return F1_SP

    def set_mode(self, mode: str, current_F1_SP: float = 0.0, current_Tin1: float = 0.0):
        with self._lock:
            if mode not in (self.MODE_MANUAL, self.MODE_AUTO_INNER, self.MODE_AUTO_FULL):
                raise ValueError(f"Unknown mode: {mode}")
            if self.mode == self.MODE_MANUAL and mode != self.MODE_MANUAL:
                self.inner.init_output(current_F1_SP, current_Tin1)
            self.mode = mode

    def set_inner_params(self, Kp: float, Ti: float):
        with self._lock:
            self.inner.Kp = Kp
            self.inner.Ti = max(Ti, 0.1)

    def set_outer_params(self, Kp: float):
        with self._lock:
            self.outer_Kp = Kp

    def set_Tout2_SP(self, value: float):
        with self._lock:
            self.Tout2_SP = value

    def set_Tin1_SP(self, value: float):
        with self._lock:
            self.Tin1_SP = value

    def get_status(self) -> dict:
        with self._lock:
            Tin1  = self.last_Tin1
            Tout2 = self.last_Tout2
            return {
                'mode':        self.mode,
                'Tout2_SP':    self.Tout2_SP,
                'Tin1_SP':     self.Tin1_SP,
                'Tin1_SP_cmd': round(self.Tin1_SP_cmd, 2),
                'F1_SP_out':   round(self.F1_SP_out, 3),
                'Tin1':        round(Tin1, 2) if Tin1 is not None else None,
                'Tout2':       round(Tout2, 2) if Tout2 is not None else None,
                'err_Tin1':    round(self.Tin1_SP_cmd - Tin1, 2) if Tin1 is not None else None,
                'err_Tout2':   round(self.Tout2_SP - Tout2, 2) if Tout2 is not None else None,
                'inner_Kp':    self.inner.Kp,
                'inner_Ti':    self.inner.Ti,
                'outer_Kp':    self.outer_Kp,
            }
