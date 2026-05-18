"""
Step-response identification for the thermal process.

Procedure:
  1. Record ~15 s of baseline (5 samples at 3 s/sample)
  2. Apply step on F1_SP
  3. Record response for `duration_s` seconds
  4. Identify K, tau, theta using 63.2% method
  5. Compute IMC-tuned PI gains at 3 aggressiveness levels
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

        self._base_F1: float      = 0.0
        self._step_F1: float      = 0.0
        self._base_Tin1: float    = 0.0
        self._step_t: Optional[float] = None
        self._start_t: Optional[float] = None
        self.duration_s: float    = 120.0

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, base_F1_SP: float, amplitude: float, duration_s: float):
        with self._lock:
            self.state      = self.PRE_STEP
            self.record     = []
            self.result     = {}
            self._base_F1   = base_F1_SP
            self._step_F1   = base_F1_SP + amplitude
            self._base_Tin1 = 0.0
            self._step_t    = None
            self._start_t   = time.time()
            self.duration_s = duration_s

    def cancel(self):
        with self._lock:
            was_step = self.state == self.STEP
            self.state  = self.IDLE
            self.record = []
            self.result = {}
            return self._base_F1 if was_step else None

    def feed(self, Tin1: float, Tout2: float, F1_SP: float) -> Optional[float]:
        """
        Call once per poll cycle. Returns F1_SP value to write during the step,
        the base F1_SP to restore on final step cycle, or None otherwise.
        """
        with self._lock:
            if self.state not in (self.PRE_STEP, self.STEP):
                return None

            now = time.time()
            self.record.append({'t': now, 'Tin1': Tin1, 'Tout2': Tout2, 'F1_SP': F1_SP})

            if self.state == self.PRE_STEP:
                if len(self.record) >= _PRE_SAMPLES:
                    self._base_Tin1 = (
                        sum(s['Tin1'] for s in self.record[-_PRE_SAMPLES:]) / _PRE_SAMPLES
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
                    't':     round(s['t'] - t0, 1),
                    'Tin1':  s['Tin1'],
                    'Tout2': s['Tout2'],
                    'F1_SP': s['F1_SP'],
                    'step':  self._step_t is not None and s['t'] >= self._step_t,
                }
                for s in self.record
            ]

    # ── Identification ─────────────────────────────────────────────────────────

    def _analyze(self):
        step_data = [s for s in self.record if self._step_t and s['t'] >= self._step_t]
        if len(step_data) < 3:
            self.result = {'error': 'Not enough data after step'}
            return

        dF1 = self._step_F1 - self._base_F1
        if abs(dF1) < 0.01:
            self.result = {'error': 'Step amplitude too small'}
            return

        Tin1_final = sum(s['Tin1'] for s in step_data[-3:]) / 3
        dTin1 = Tin1_final - self._base_Tin1
        K = dTin1 / dF1

        # 63.2% crossing -> tau
        target = self._base_Tin1 + 0.632 * dTin1
        tau = self.duration_s
        for i in range(1, len(step_data)):
            prev, curr = step_data[i - 1], step_data[i]
            crossed = ((dTin1 > 0 and curr['Tin1'] >= target) or
                       (dTin1 < 0 and curr['Tin1'] <= target))
            if crossed:
                span = curr['t'] - prev['t']
                frac = (target - prev['Tin1']) / (curr['Tin1'] - prev['Tin1'] + 1e-9)
                tau  = (prev['t'] + frac * span) - self._step_t
                break

        # Dead time: first sample where |dTin1| > 2% of total step
        theta = 0.0
        thresh = abs(0.02 * dTin1)
        for s in step_data:
            if abs(s['Tin1'] - self._base_Tin1) >= thresh:
                theta = s['t'] - self._step_t
                break

        # IMC tuning: Kp = tau / (K*(tau_c+theta)),  Ti = tau
        def imc(factor: float) -> dict:
            tau_c = max(factor * tau, theta)
            Kp = round(tau / (K * (tau_c + theta)), 4) if K != 0 else 0.0
            return {'Kp': Kp, 'Ti': round(tau, 1)}

        self.result = {
            'K':     round(K, 4),
            'tau':   round(tau, 1),
            'theta': round(theta, 1),
            'dF1':   round(dF1, 2),
            'dTin1': round(dTin1, 2),
            'tuning': {
                'aggressive':   imc(0.5),
                'normal':       imc(1.0),
                'conservative': imc(2.0),
            },
        }
