"""
Step-response identification for the thermal process.

Procedure:
  1. Record ~15 s of baseline (5 samples at 3 s/sample)
  2. Apply step on HeaterLarge_PWM
  3. Record response for `duration_s` seconds
  4. Identify K, tau, theta using 63.2% method for Tin1_HE1 and T_hout (smallOutlet)
  5. Compute IMC-tuned PI gains (krPI, TiPI) from Tin1 channel at 3 aggressiveness levels
"""
import time
import threading
from typing import Optional

_PRE_SAMPLES = 5   # baseline samples before applying step


class StepIdentifier:
    IDLE     = 'idle'
    PRE_STEP = 'pre_step'
    STEP     = 'step'
    DONE     = 'done'

    def __init__(self):
        self._lock         = threading.Lock()
        self.state: str    = self.IDLE
        self.record: list  = []
        self.result: dict  = {}

        self._base_F1: float       = 0.0
        self._step_F1: float       = 0.0
        self._base_Tin1: float     = 0.0
        self._base_T_hout: float   = 0.0
        self._step_t: Optional[float] = None
        self._start_t: Optional[float] = None
        self.duration_s: float     = 120.0

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, base_F1_SP: float, amplitude: float, duration_s: float):
        with self._lock:
            self.state         = self.PRE_STEP
            self.record        = []
            self.result        = {}
            self._base_F1      = base_F1_SP
            self._step_F1      = base_F1_SP + amplitude
            self._base_Tin1    = 0.0
            self._base_T_hout  = 0.0
            self._step_t       = None
            self._start_t      = time.time()
            self.duration_s    = duration_s

    def cancel(self):
        with self._lock:
            was_step = self.state == self.STEP
            self.state  = self.IDLE
            self.record = []
            self.result = {}
            return self._base_F1 if was_step else None

    def feed(self, Tin1: float, Tout2: float, F1_SP: float,
             T_hout: float = 0.0) -> Optional[float]:
        """
        Call once per poll cycle. Returns F1_SP value to write during the step,
        the base F1_SP to restore on final step cycle, or None otherwise.
        T_hout is the small-furnace outlet temperature (smallOutlet).
        """
        with self._lock:
            if self.state not in (self.PRE_STEP, self.STEP):
                return None

            now = time.time()
            self.record.append({
                't': now, 'Tin1': Tin1, 'Tout2': Tout2,
                'F1_SP': F1_SP, 'T_hout': T_hout,
            })

            if self.state == self.PRE_STEP:
                if len(self.record) >= _PRE_SAMPLES:
                    self._base_Tin1 = (
                        sum(s['Tin1'] for s in self.record[-_PRE_SAMPLES:]) / _PRE_SAMPLES
                    )
                    self._base_T_hout = (
                        sum(s['T_hout'] for s in self.record[-_PRE_SAMPLES:]) / _PRE_SAMPLES
                    )
                    self.state   = self.STEP
                    self._step_t = now
                return None   # keep current F1_SP during pre-step

            # STEP phase
            if now - self._step_t >= self.duration_s:
                self._analyze()
                self.state = self.DONE
                return self._base_F1   # restore baseline on the cycle step ends
            return self._step_F1

    def get_status(self) -> dict:
        with self._lock:
            elapsed = (time.time() - self._step_t) if self._step_t else 0.0
            return {
                'state':      self.state,
                'n_samples':  len(self.record),
                'elapsed_s':  round(elapsed, 1) if self.state == self.STEP else 0.0,
                'duration_s': self.duration_s,
                'base_F1':    self._base_F1,
                'step_F1':    self._step_F1,
                'result':     dict(self.result),
            }

    def get_chart_data(self) -> list:
        with self._lock:
            t0 = self._start_t or (self.record[0]['t'] if self.record else time.time())
            return [
                {
                    't':      round(s['t'] - t0, 1),
                    'Tin1':   s['Tin1'],
                    'Tout2':  s['Tout2'],
                    'F1_SP':  s['F1_SP'],
                    'T_hout': s.get('T_hout', 0.0),
                    'step':   self._step_t is not None and s['t'] >= self._step_t,
                }
                for s in self.record
            ]

    # ── Identification ─────────────────────────────────────────────────────────

    def _identify_channel(self, step_data: list, key: str,
                          base_val: float, d_input: float) -> dict:
        """
        FOPTD identification for one output channel using the 63.2% method.
        Returns K, tau, theta and IMC tuning (aggressive / normal / conservative).
        """
        if abs(d_input) < 0.01:
            return {'error': 'Input step too small'}

        values   = [s[key] for s in step_data]
        final    = sum(values[-3:]) / 3
        delta_y  = final - base_val
        K        = delta_y / d_input

        # 63.2% crossing → tau (linear interpolation between samples)
        target = base_val + 0.632 * delta_y
        tau    = self.duration_s
        for i in range(1, len(step_data)):
            prev, curr = step_data[i - 1], step_data[i]
            crossed = ((delta_y > 0 and curr[key] >= target) or
                       (delta_y < 0 and curr[key] <= target))
            if crossed:
                span = curr['t'] - prev['t']
                frac = (target - prev[key]) / (curr[key] - prev[key] + 1e-9)
                tau  = (prev['t'] + frac * span) - self._step_t
                break

        # Dead time: first sample where response exceeds 2% of total step
        theta  = 0.0
        thresh = abs(0.02 * delta_y)
        for s in step_data:
            if abs(s[key] - base_val) >= thresh:
                theta = s['t'] - self._step_t
                break

        def imc(factor: float) -> dict:
            tau_c = max(factor * tau, theta)
            Kp    = round(tau / (K * (tau_c + theta)), 4) if K != 0 else 0.0
            return {'Kp': Kp, 'Ti': round(tau, 1)}

        return {
            'K':       round(K, 4),
            'tau':     round(tau, 1),
            'theta':   round(theta, 1),
            'd_input': round(d_input, 2),
            'delta_y': round(delta_y, 2),
            'tuning': {
                'aggressive':   imc(0.5),
                'normal':       imc(1.0),
                'conservative': imc(2.0),
            },
        }

    def _analyze(self):
        step_data = [s for s in self.record if self._step_t and s['t'] >= self._step_t]
        if len(step_data) < 3:
            self.result = {'error': 'Not enough data after step'}
            return

        d_input = self._step_F1 - self._base_F1

        tin1_res   = self._identify_channel(step_data, 'Tin1',   self._base_Tin1,   d_input)
        t_hout_res = self._identify_channel(step_data, 'T_hout', self._base_T_hout, d_input)

        if 'error' in tin1_res:
            self.result = {'error': tin1_res['error']}
            return

        normal = tin1_res.get('tuning', {}).get('normal', {})
        self.result = {
            # Backward-compatible top-level fields (from Tin1 channel)
            'K':     tin1_res['K'],
            'tau':   tin1_res['tau'],
            'theta': tin1_res['theta'],
            'dF1':   round(d_input, 2),
            'dTin1': tin1_res['delta_y'],
            'tuning': tin1_res['tuning'],
            # Per-channel breakdown
            'Tin1':        tin1_res,
            'smallOutlet': t_hout_res,
            # PI controller parameters (IMC Normal, Tin1 channel)
            'krPI': normal.get('Kp', 0.0),
            'TiPI': normal.get('Ti', 0.0),
        }
