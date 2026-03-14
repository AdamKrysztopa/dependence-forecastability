# 11. Include This Base Implementation From the User as the Starting Point

- [x] Preserve this prototype as the baseline implementation.
- [x] Refactor it into package modules while retaining baseline behavior.
- [x] Treat this as a hard requirement.

```python
import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from scipy.fftpack import fft, ifft

class ForecastabilityAnalyzer:
    """Unified AMI + pAMI package with surrogate-based interpretability.
    Exact implementation of the analysis plan we designed."""
    
    def __init__(self, n_surrogates: int = 99, random_state: int = 42):
        self.n_surrogates = n_surrogates
        self.rng = np.random.default_rng(random_state)
        self._ami = None
        self._pami = None
        self._ami_bands = None
        self._pami_bands = None
        self.ts = None

    def compute_ami(self, ts: np.ndarray, max_lag: int = 100):
        self.ts = np.asarray(ts).flatten()
        ts_scaled = StandardScaler().fit_transform(self.ts.reshape(-1,1)).ravel()
        ami = np.zeros(max_lag)
        for h in range(1, max_lag + 1):
            if len(ts_scaled) - h < 30: break
            X = ts_scaled[:-h].reshape(-1, 1)
            y = ts_scaled[h:]
            ami[h-1] = mutual_info_regression(X, y, n_neighbors=8, random_state=self.rng)[0]
        self._ami = ami
        return ami

    def compute_pami(self, ts: np.ndarray, max_lag: int = 50):
        self.ts = np.asarray(ts).flatten()
        ts_scaled = StandardScaler().fit_transform(self.ts.reshape(-1,1)).ravel()
        pami = np.zeros(max_lag)
        for h in range(1, max_lag + 1):
            if len(ts_scaled) - h < 50: break
            # Conditioning lags 1..(h-1)
            Z = np.column_stack([np.roll(ts_scaled, k)[h:] for k in range(1, h)]) if h > 1 else np.empty((len(ts_scaled)-h, 0))
            past = ts_scaled[:-h]
            future = ts_scaled[h:]
            if h == 1 or Z.shape[1] == 0:
                res_past = past
                res_future = future
            else:
                model = LinearRegression()
                model.fit(Z, past)
                res_past = past - model.predict(Z)
                model.fit(Z, future)
                res_future = future - model.predict(Z)
            pami[h-1] = mutual_info_regression(res_past.reshape(-1,1), res_future,
                                               n_neighbors=8, random_state=self.rng)[0]
        self._pami = pami
        return pami

    def _phase_surrogates(self, ts: np.ndarray, n: int):
        surrogates = np.empty((n, len(ts)))
        fft_ts = fft(ts)
        for i in range(n):
            phases = np.exp(1j * self.rng.uniform(0, 2*np.pi, len(ts)//2))
            phases = np.concatenate(([1.], phases, np.conj(phases[::-1 if len(ts)%2 else -1:0:-1])))
            surrogates[i] = np.real(ifft(fft_ts * phases))
        return surrogates

    def compute_significance(self, which: str = 'ami', max_lag: int = None):
        max_lag = max_lag or len(self._ami if which=='ami' else self._pami)
        surrogates = self._phase_surrogates(self.ts, self.n_surrogates)
        if which == 'ami':
            vals = np.array([self.compute_ami(s, max_lag) for s in surrogates])
            self._ami_bands = np.percentile(vals, [2.5, 97.5], axis=0)
            return self._ami_bands
        else:
            vals = np.array([self.compute_pami(s, max_lag) for s in surrogates])
            self._pami_bands = np.percentile(vals, [2.5, 97.5], axis=0)
            return self._pami_bands

    def analyze(self, ts: np.ndarray, max_lag: int = 100, target_horizon: int = None):
        ts = np.asarray(ts).flatten()
        print("=== Forecastability Analysis (AMI + pAMI) ===")
        
        self.compute_ami(ts, max_lag)
        self.compute_significance('ami', max_lag)
        print(f"Raw AMI triage (mean first 20 lags): {self._ami[:20].mean():.4f}")
        sig_ami = np.where(self._ami > self._ami_bands[1])[0] + 1
        print(f"Significant AMI lags: {sig_ami.tolist()}")

        self.compute_pami(ts, max_lag//2)
        self.compute_significance('pami', max_lag//2)
        sig_pami = np.where(self._pami > self._pami_bands[1])[0] + 1
        print(f"Significant direct pAMI lags (use for AR order): {sig_pami.tolist()}")

        mean_ami = self._ami[:20].mean()
        if mean_ami > 0.8:
            rec = "HIGH → Complex global models (Transformers, N-BEATS)"
        elif mean_ami > 0.3:
            rec = "MEDIUM → Seasonal ARIMA / Prophet / LightGBM"
        else:
            rec = "LOW → Naïve or seasonal naïve only"
        print(f"Recommendation: {rec}")
        
        self.plot()
        return {"ami": self._ami, "pami": self._pami, "sig_ami_lags": sig_ami, "sig_pami_lags": sig_pami}

    def plot(self):
        fig, axs = plt.subplots(2, 1, figsize=(11, 8))
        lags_ami = np.arange(1, len(self._ami)+1)
        axs[0].plot(lags_ami, self._ami, 'b-', lw=2, label='AMI(h)')
        if self._ami_bands is not None:
            axs[0].fill_between(lags_ami, self._ami_bands[0], self._ami_bands[1], color='b', alpha=0.15, label='95% surrogate band')
        axs[0].axhline(0, color='k', lw=0.5); axs[0].set_title('Raw AMI — nonlinear ACF + significance')
        axs[0].set_xlabel('Lag'); axs[0].legend(); axs[0].grid(alpha=0.3)

        lags_pami = np.arange(1, len(self._pami)+1)
        axs[1].plot(lags_pami, self._pami, 'r-', lw=2, label='pAMI(h)')
        if self._pami_bands is not None:
            axs[1].fill_between(lags_pami, self._pami_bands[0], self._pami_bands[1], color='r', alpha=0.15)
        axs[1].axhline(0, color='k', lw=0.5); axs[1].set_title('Partial AMI — nonlinear PACF + significance')
        axs[1].set_xlabel('Lag'); axs[1].legend(); axs[1].grid(alpha=0.3)
        plt.tight_layout()
        plt.show()
```
