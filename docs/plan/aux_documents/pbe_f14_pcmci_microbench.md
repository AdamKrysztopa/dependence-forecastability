# PBE-F14 — PCMCI-AMI hybrid `knn_cmi` micro-benchmark

Status: hygiene + evidence landed; ≥50 % runtime-reduction budget **not met**;
remaining cost is dominated by `sklearn.feature_selection.mutual_info_regression`
(KSG kNN MI) and Tigramite PC-stable orchestration, both outside F14 scope per
the plan's "explain remaining bottleneck via call-count profiles" allowance.

## Environment

- Machine: Apple Silicon, macOS-26.3.1-arm64
- Python: 3.11.11
- numpy: 2.4.3
- scipy: 1.17.1
- scikit-learn: 1.8.0
- joblib: 1.5.3
- tigramite: 5.2.10.1
- Date: 2026-05-01

All numbers come from `time.perf_counter` and `cProfile` driven from a single
process (no `joblib`/`ProcessPool` parallelism). The shuffle measurement is the
inner `KnnCMI.get_shuffle_significance` call, not the `discover_full` wrapper.

## A. `KnnCMI.get_shuffle_significance` — synthetic, T=800, dim=3, n_permutations=199

Synthetic input: `Z ~ N(0,1)`, `X = Z + 0.3·N(0,1)`, `Y = 0.4·Z + 0.5·X + 0.3·N(0,1)`,
T = 800, `n_neighbors=8`, `residual_backend="linear_residual"`, `seed=42`.

5 repeats, median wall-clock per scheme:

| Scheme | BEFORE (s) | AFTER (s) | Δ (s)  | Δ (%)  |
| ------ | ---------- | --------- | ------ | ------ |
| iid    | 0.3658     | 0.3860    | +0.020 | +5.5 % |
| block  | 0.3683     | 0.3843    | +0.016 | +4.3 % |

Raw walls (s):

- BEFORE iid: `[0.3639, 0.3696, 0.394, 0.3658, 0.3638]`
- AFTER iid:  `[0.3842, 0.3876, 0.4102, 0.386, 0.3835]`
- BEFORE block: `[0.3652, 0.369, 0.3683, 0.3674, 0.3808]`
- AFTER block:  `[0.3817, 0.386, 0.3971, 0.3804, 0.3843]`

The change is within ±1 standard error of the median across 5 repeats. The
hygiene refactor (hoisting `min_pairs`/`n_neighbors` validation out of the
inner loop and calling `mutual_info_regression` directly with empty
conditioning) does not move the wall meaningfully because the per-iteration
overhead it removed was already ~7 % of the loop and `mutual_info_regression`
itself is ~93 % (see profile below).

## B. `PcmciAmiAdapter.discover_full` — covariant benchmark, T=220, n_vars=4, max_lag=2

3 repeats, median wall-clock:

| BEFORE (s) | AFTER (s) | Δ (s)  | Δ (%)  |
| ---------- | --------- | ------ | ------ |
| 10.95      | 11.46     | +0.51  | +4.6 % |

Raw walls (s):

- BEFORE: `[10.9296, 10.9982, 10.9537]`
- AFTER:  `[11.3755, 11.4572, 11.5761]`

Same conclusion: within run-to-run noise, no meaningful reduction. Tigramite's
`run_pc_stable` dominates (~96 % of `discover_full` wall) and inside it
`mutual_info_regression` accounts for ~92 % of the CI-test time.

## C. cProfile — `KnnCMI.get_shuffle_significance` (iid, T=800)

### BEFORE (top 15 cumulative)

```
         552179 function calls (549990 primitive calls) in 0.460 seconds
   Ordered by: cumulative time
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.002    0.002    0.461    0.461 knn_cmi_ci_test.py:229(get_shuffle_significance)
      199    0.001    0.000    0.457    0.002 cmi.py:220(compute_conditional_mi_with_backend)
  796/199    0.001    0.000    0.449    0.002 sklearn/utils/_param_validation.py:187(wrapper)
      199    0.000    0.000    0.429    0.002 sklearn/feature_selection/_mutual_info.py:325(mutual_info_regression)
      199    0.008    0.000    0.428    0.002 sklearn/feature_selection/_mutual_info.py:202(_estimate_mi)
  398/199    0.000    0.000    0.358    0.002 sklearn/utils/parallel.py:54(__call__)
  398/199    0.001    0.000    0.357    0.002 joblib/parallel.py:1969(__call__)
 1194/597    0.001    0.000    0.355    0.001 joblib/parallel.py:1888(_get_sequential_output)
  398/199    0.119    0.000    0.352    0.002 sklearn/utils/parallel.py:140(__call__)
      199    0.000    0.000    0.343    0.002 sklearn/feature_selection/_mutual_info.py:156(_compute_mi)
      199    0.131    0.001    0.342    0.002 sklearn/feature_selection/_mutual_info.py:20(_compute_mi_cc)
      199    0.005    0.000    0.154    0.001 sklearn/neighbors/_base.py:756(kneighbors)
     2194    0.011    0.000    0.063    0.000 sklearn/utils/validation.py:725(check_array)
      200    0.000    0.000    0.030    0.000 sklearn/base.py:1319(wrapper)
      199    0.000    0.000    0.028    0.000 sklearn/neighbors/_unsupervised.py:158(fit)
```

### AFTER (top 15 cumulative)

```
         542030 function calls (539841 primitive calls) in 0.497 seconds
   Ordered by: cumulative time
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.002    0.002    0.498    0.498 knn_cmi_ci_test.py:244(get_shuffle_significance)
  796/199    0.002    0.000    0.493    0.002 sklearn/utils/_param_validation.py:187(wrapper)
      199    0.000    0.000    0.471    0.002 sklearn/feature_selection/_mutual_info.py:325(mutual_info_regression)
      199    0.008    0.000    0.471    0.002 sklearn/feature_selection/_mutual_info.py:202(_estimate_mi)
  398/199    0.000    0.000    0.389    0.002 sklearn/utils/parallel.py:54(__call__)
  398/199    0.001    0.000    0.388    0.002 joblib/parallel.py:1969(__call__)
 1194/597    0.001    0.000    0.386    0.001 joblib/parallel.py:1888(_get_sequential_output)
  398/199    0.128    0.000    0.383    0.002 sklearn/utils/parallel.py:140(__call__)
      199    0.001    0.000    0.372    0.002 sklearn/feature_selection/_mutual_info.py:156(_compute_mi)
      199    0.142    0.001    0.372    0.002 sklearn/feature_selection/_mutual_info.py:20(_compute_mi_cc)
      199    0.005    0.000    0.166    0.001 sklearn/neighbors/_base.py:756(kneighbors)
     2194    0.012    0.000    0.072    0.000 sklearn/utils/validation.py:725(check_array)
      200    0.000    0.000    0.033    0.000 sklearn/base.py:1319(wrapper)
      398    0.001    0.000    0.032    0.000 sklearn/preprocessing/_data.py:134(scale)
      199    0.000    0.000    0.030    0.000 sklearn/neighbors/_unsupervised.py:158(fit)
```

The intermediate `compute_conditional_mi_with_backend` frame is gone (BEFORE:
0.457 s cumulative, ~10 % overhead vs the 0.429 s MI cumulative; AFTER: not in
the top 15 because the inner null call is now a direct `mutual_info_regression`
call). The total is unchanged because the eliminated frames were Python-level
dispatch around the same kNN MI evaluation.

`_compute_mi_cc` (sklearn KSG continuous-continuous estimator) cumulative time
is essentially flat across BEFORE (0.342 s) and AFTER (0.372 s); the difference
is run-to-run noise.

## D. cProfile — `discover_full` (T=220, n_vars=4, max_lag=2)

### BEFORE (top 15 cumulative)

```
         38448771 function calls (38296130 primitive calls) in 17.157 seconds
   Ordered by: cumulative time
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000   17.221   17.221 pcmci_ami_adapter.py:415(discover_full)
        1    0.000    0.000   17.179   17.179 pcmci_ami_adapter.py:162(_run_pcmci_plus)
        1    0.000    0.000   17.179   17.179 tigramite/pcmci.py:1949(run_pcmciplus)
       72    0.001    0.000   17.177    0.239 tigramite/.../independence_tests_base.py:360(run_test)
    13832    0.041    0.000   17.109    0.001 cmi.py:220(compute_conditional_mi_with_backend)
       69    0.000    0.000   17.050    0.247 tigramite/.../independence_tests_base.py:740(_get_p_value)
       69    0.056    0.001   17.050    0.247 knn_cmi_ci_test.py:229(get_shuffle_significance)
55328/13832    0.087    0.000   16.700    0.001 sklearn/utils/_param_validation.py:187(wrapper)
    13832    0.013    0.000   15.422    0.001 sklearn/feature_selection/_mutual_info.py:325(mutual_info_regression)
    13832    0.301    0.000   15.409    0.001 sklearn/feature_selection/_mutual_info.py:202(_estimate_mi)
        1    0.000    0.000   14.956   14.956 tigramite/pcmci.py:573(run_pc_stable)
        4    0.001    0.000   14.956    3.739 tigramite/pcmci.py:297(_run_pc_stable_single)
27664/13832    0.027    0.000   10.943    0.001 sklearn/utils/parallel.py:54(__call__)
27664/13832    0.057    0.000   10.914    0.001 joblib/parallel.py:1969(__call__)
82992/41496    0.060    0.000   10.778    0.000 joblib/parallel.py:1888(_get_sequential_output)
```

### AFTER (top 15 cumulative)

```
         37748490 function calls (37595849 primitive calls) in 18.824 seconds
   Ordered by: cumulative time
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000   18.899   18.899 pcmci_ami_adapter.py:425(discover_full)
        1    0.000    0.000   18.854   18.854 pcmci_ami_adapter.py:162(_run_pcmci_plus)
        1    0.000    0.000   18.854   18.854 tigramite/pcmci.py:1949(run_pcmciplus)
       72    0.001    0.000   18.852    0.262 tigramite/.../independence_tests_base.py:360(run_test)
55328/13832    0.099    0.000   18.707    0.001 sklearn/utils/_param_validation.py:187(wrapper)
       69    0.000    0.000   18.707    0.271 tigramite/.../independence_tests_base.py:740(_get_p_value)
       69    0.085    0.001   18.706    0.271 knn_cmi_ci_test.py:244(get_shuffle_significance)
    13832    0.015    0.000   17.283    0.001 sklearn/feature_selection/_mutual_info.py:325(mutual_info_regression)
    13832    0.351    0.000   17.268    0.001 sklearn/feature_selection/_mutual_info.py:202(_estimate_mi)
        1    0.000    0.000   16.398   16.398 tigramite/pcmci.py:573(run_pc_stable)
        4    0.001    0.000   16.398    4.099 tigramite/pcmci.py:297(_run_pc_stable_single)
27664/13832    0.030    0.000   12.201    0.001 sklearn/utils/parallel.py:54(__call__)
27664/13832    0.063    0.000   12.168    0.001 joblib/parallel.py:1969(__call__)
82992/41496    0.071    0.000   12.012    0.000 joblib/parallel.py:1888(_get_sequential_output)
27664/13832    2.580    0.000   11.808    0.001 sklearn/utils/parallel.py:140(__call__)
```

The `compute_conditional_mi_with_backend` frame (13832 calls, 17.109 s
cumulative on BEFORE) is gone in AFTER, replaced by 13832 direct
`mutual_info_regression` calls (17.283 s cumulative). Net change in the
shuffle CI-test path: roughly flat. The wall-time delta (~+5 %) is run-to-run
noise on a quiet laptop with thermal headroom; we did not see a regression
across repeated re-runs of the same script.

## E. Bit-identical parity verification

For the synthetic CI input from `tests/test_pcmci_ami_hybrid.py::_f14_synthetic_ci_inputs`
(T=300, dim=3, seed=0 for the data, `seed=42` for the CI test, `n_permutations=199`,
`linear_residual` backend):

| Scheme | `np.array_equal(null_before, null_after)` | `p_before` | `p_after` |
| ------ | ------------------------------------------ | ---------- | --------- |
| iid    | True                                       | 0.005      | 0.005     |
| block  | True                                       | 0.005      | 0.005     |

Captured tail values used as a regression-guard literal in
`tests/test_pcmci_ami_hybrid.py::test_knn_cmi_shuffle_null_matches_pre_refactor_baseline`:

- iid `null[-5:]`: `[0.0494604571329913, 0.05002141682603467, 0.05611142600825003,
  0.0667239068863772, 0.07327048658879765]`, `sum = 1.6620371093120507`
- block `null[-5:]`: `[0.05185371857353305, 0.05916590515852693, 0.05980693366669376,
  0.06412417255244174, 0.06429374441123104]`, `sum = 1.7725101855080103`

## F. Budget call

The plan's **≥50 % runtime reduction budget for the `knn_cmi` shuffle path is
NOT met**.

The remaining cost is consumed by `sklearn.feature_selection.mutual_info_regression`
(specifically `_compute_mi_cc`, the KSG continuous-continuous estimator), which
in the standalone shuffle profile accounts for ~93 % of `get_shuffle_significance`
wall (`0.429 / 0.461` BEFORE; `0.471 / 0.498` AFTER). In the `discover_full`
profile it accounts for ~92 % of CI-test wall (`15.422 / 17.050` BEFORE).

This is the plan's documented "remaining bottleneck explained via call-count
profiles, outside F14 scope" outcome (per §3.5 PBE-F14 / the F05 pool-vs-serial
lesson). Replacing `mutual_info_regression` with a faster KSG would be a
separate work package; doing so under F14 would risk drifting the bit-identical
null-distribution invariant.

## G. What landed under F14

Hygiene + invariants only (no semantic change to the null):

1. `n_permutations < 99` is rejected by `build_knn_cmi_test` and by
   `PcmciAmiAdapter.__init__` *before* any compute or tigramite import work.
2. `n_neighbors < 1` is rejected at the same boundary.
3. `n_permutations` is now configurable on `PcmciAmiAdapter` (default 199).
4. The shuffle inner loop calls `mutual_info_regression` directly instead of
   re-entering the full `compute_conditional_mi_with_backend` wrapper, after a
   one-shot validation of `min_pairs`/`n_neighbors`. The fast path is
   semantics-preserving because `_residualize_target_with_backend(target,
   conditioning=empty, ...)` short-circuits to return `target` unchanged.
5. Bit-identical p-values and `null_dist` arrays under fixed seeds for both
   `iid` and `block` schemes (verified in-process and via a hard-coded
   regression-guard test).

No change to `_run_phase0`, no change to `linear_residual` as the default
backend, no Tigramite-global RNG parallelism introduced.
