"""
First-order thermal process model — simulation only.

Replaces random.uniform with a physically plausible closed-loop response.
Removed when connecting to the real S7-1500.

Process model (discrete-time, Euler integration):
  T[k+1] = T[k] + (dt / tau) * (K_proc * u[k] - (T[k] - T_ambient)) + w_T

  where u[k] is the normalised heater output (0.0 – 1.0),
  computed by an internal P-controller driving T toward the setpoint.

Flow model (first-order lag toward setpoint):
  F[k+1] = F[k] + (dt / tau_f) * (SP_F - F[k]) + w_F
"""

import random
import threading


class ThermalProcessModel:
    """
    Discrete-time simulation of a thermal process with flow loop.

    Parameters
    ----------
    dt        : float  Sampling period (s).  Should match Flask polling interval.
    tau_T     : float  Thermal time constant (s).
    K_proc    : float  Process gain (deg C per unit heater output at steady state).
    T_ambient : float  Ambient / initial temperature (deg C).
    T_init    : float  Initial process temperature (deg C).
    tau_F     : float  Flow loop time constant (s).
    F_init    : float  Initial flow rate (m3/h).
    noise_T   : float  Standard deviation of temperature measurement noise (deg C).
    noise_F   : float  Standard deviation of flow measurement noise (m3/h).
    Kp_sim    : float  Proportional gain of the internal simulation controller.
    """

    def __init__(
        self,
        dt: float        = 3.0,
        tau_T: float     = 45.0,
        K_proc: float    = 220.0,
        T_ambient: float = 20.0,
        T_init: float    = 20.0,
        tau_F: float     = 8.0,
        F_init: float    = 2.0,
        noise_T: float   = 0.25,
        noise_F: float   = 0.02,
        Kp_sim: float    = 0.012,
    ):
        self.dt        = dt
        self.tau_T     = tau_T
        self.K_proc    = K_proc
        self.T_ambient = T_ambient
        self.noise_T   = noise_T
        self.noise_F   = noise_F
        self.Kp_sim    = Kp_sim
        self.tau_F     = tau_F

        # State variables
        self._T = T_init
        self._F = F_init
        self._u = 0.0          # last heater output (0–1)
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def temperature(self) -> float:
        return round(self._T, 2)

    @property
    def flow_rate(self) -> float:
        return round(self._F, 3)

    def step(self, sp_temp: float, sp_flow: float) -> dict:
        """
        Advance the model by one time step.

        Parameters
        ----------
        sp_temp : temperature setpoint (deg C)
        sp_flow : flow rate setpoint   (m3/h)

        Returns
        -------
        dict with keys: temperature, flow_rate, u_percent
        """
        with self._lock:
            # ── Internal P-controller for heater output ──────────────────
            error = sp_temp - self._T
            self._u = max(0.0, min(1.0, self.Kp_sim * error))

            # ── Temperature dynamics ─────────────────────────────────────
            # Euler: T[k+1] = T[k] + (dt/tau) * (K*u - (T - T_amb))
            dT = (self.dt / self.tau_T) * (
                self.K_proc * self._u - (self._T - self.T_ambient)
            )
            self._T += dT + random.gauss(0, self.noise_T)
            self._T  = max(0.0, min(600.0, self._T))   # physical hard limits

            # ── Flow dynamics ─────────────────────────────────────────────
            dF = (self.dt / self.tau_F) * (sp_flow - self._F)
            self._F += dF + random.gauss(0, self.noise_F)
            self._F  = max(0.0, min(20.0, self._F))

            return {
                "temperature": round(self._T, 2),
                "flow_rate":   round(self._F, 3),
                "u_percent":   round(self._u * 100, 1),
            }

    def reset(self, T_init: float = None, F_init: float = None):
        """Reset state (e.g. after a large setpoint change in tests)."""
        with self._lock:
            if T_init is not None:
                self._T = float(T_init)
            if F_init is not None:
                self._F = float(F_init)
            self._u = 0.0
