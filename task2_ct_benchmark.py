#!/usr/bin/env python3
"""
Task 2 – Scientific Computing (project-aligned)
CT-like volume processing benchmark: window -> smooth -> threshold -> stats.

- Modes: serial | parallel | both
- Parallel: one process per volume
- Outputs: CSV + Markdown with timings, speedup, and efficiency

Recommended venv setup (once):
  source ~/venvs/ensf619/bin/activate
  pip install -U numpy pandas scipy   # scipy optional but recommended
  deactivate
"""

import argparse, os, time, json, math, csv, statistics as stats
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

# Optional fast smoothing (SciPy). Falls back if missing.
try:
    from scipy.ndimage import gaussian_filter as _scipy_gaussian
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

def _np_gaussian_fallback(vol: np.ndarray, sigma: float) -> np.ndarray:
    """Simple separable 1D Gaussian smoothing using NumPy (no SciPy).
    Not super fast, but fine for modest sizes; set --sigma 0 to skip."""
    if sigma <= 0:
        return vol
    # build 1D kernel
    radius = max(1, int(3 * sigma))
    x = np.arange(-radius, radius + 1, dtype=np.float32)
    k = np.exp(-(x ** 2) / (2 * sigma ** 2)).astype(np.float32)
    k /= k.sum()

    # separable conv over (z, y, x)
    out = vol.astype(np.float32, copy=False)
    for axis in (0, 1, 2):
        out = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, out)
    return out

def smooth3d(vol: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return vol
    if HAVE_SCIPY:
        return _scipy_gaussian(vol, sigma=sigma, mode="nearest")
    return _np_gaussian_fallback(vol, sigma=sigma)

@dataclass
class VolumeResult:
    idx: int
    n_vox: int
    muscle_vox: int
    muscle_vol_mm3: float
    hu_mean: float
    hu_std: float
    elapsed_sec: float

def generate_synthetic_ct(shape, rng: np.random.Generator) -> np.ndarray:
    """Rough CT-ish volume: background + soft tissue + bone-like speckles, in HU."""
    z, y, x = shape
    vol = rng.normal(0, 30, size=shape).astype(np.float32)  # background ~ air-ish
    # soft tissue / muscle band around HU ~ 40 ± 20
    vol += rng.normal(40, 20, size=shape).astype(np.float32)
    # sparse higher HU 'bone' blobs
    mask = rng.random(size=shape) < 0.02
    vol[mask] += rng.normal(600, 150, size=mask.sum()).astype(np.float32)
    return vol

def process_volume(idx: int, shape, sigma: float, hu_window=(-200, 200),
                   muscle_range=(-29, 150), voxel_size_mm=1.0, seed=12345) -> VolumeResult:
    rng = np.random.default_rng(seed + idx)
    t0 = time.perf_counter()

    vol = generate_synthetic_ct(shape, rng)

    # windowing (clip to HU window)
    lo, hi = hu_window
    vol = np.clip(vol, lo, hi, out=vol)

    # smoothing
    vol = smooth3d(vol, sigma=sigma)

    # "muscle" mask
    m_lo, m_hi = muscle_range
    mask = (vol >= m_lo) & (vol <= m_hi)

    # stats inside mask
    if mask.any():
        vals = vol[mask]
        hu_mean = float(vals.mean())
        hu_std  = float(vals.std(ddof=0))
    else:
        hu_mean = float("nan"); hu_std = float("nan")

    elapsed = time.perf_counter() - t0
    n_vox = int(np.prod(shape))
    muscle_vox = int(mask.sum())
    muscle_vol_mm3 = float(muscle_vox * (voxel_size_mm ** 3))

    return VolumeResult(idx, n_vox, muscle_vox, muscle_vol_mm3, hu_mean, hu_std, elapsed)

def run_serial(n_vols, shape, sigma, voxel_size_mm, seed):
    results = []
    for i in range(n_vols):
        results.append(process_volume(i, shape, sigma, voxel_size_mm=voxel_size_mm, seed=seed))
    total = sum(r.elapsed_sec for r in results)
    return results, total

def run_parallel(n_vols, shape, sigma, voxel_size_mm, seed, workers):
    results = [None] * n_vols
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {
            ex.submit(process_volume, i, shape, sigma, (-200, 200), (-29, 150), voxel_size_mm, seed): i
            for i in range(n_vols)
        }
        for fut in as_completed(futs):
            i = futs[fut]
            results[i] = fut.result()
    total = time.perf_counter() - t0
    return results, total

def write_csv(path, rows, extra_summary=None):
    fieldnames = list(asdict(rows[0]).keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))
        if extra_summary:
            f.write("\n# SUMMARY\n")
            f.write(json.dumps(extra_summary, indent=2))
    return path

def write_markdown(path, header_lines, table_rows, summary_lines):
    with open(path, "w") as f:
        for line in header_lines:
            f.write(line + "\n")
        f.write("\n| vol | n_vox | muscle_vox | muscle_mm³ | hu_mean | hu_std | t(s) |\n")
        f.write("|---:|---:|---:|---:|---:|---:|---:|\n")
        for r in table_rows:
            f.write(f"| {r.idx} | {r.n_vox} | {r.muscle_vox} | {r.muscle_vol_mm3:.0f} | {r.hu_mean:.3f} | {r.hu_std:.3f} | {r.elapsed_sec:.3f} |\n")
        f.write("\n")
        for line in summary_lines:
            f.write(line + "\n")
    return path

def main():
    p = argparse.ArgumentParser(description="Task 2 CT benchmark (serial vs parallel)")
    p.add_argument("--mode", choices=["serial", "parallel", "both"], default="both")
    p.add_argument("--cpus", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "1")))
    p.add_argument("--n-vols", type=int, default=8, help="number of volumes to process")
    p.add_argument("--shape", type=str, default="256,256,128", help="z,y,x (e.g. 256,256,128)")
    p.add_argument("--sigma", type=float, default=1.2, help="3D Gaussian sigma (0 to disable)")
    p.add_argument("--voxel-mm", type=float, default=1.0, help="voxel size (mm)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-csv", default="task2_results.csv")
    p.add_argument("--out-md", default="task2_report.md")
    args = p.parse_args()

    shape = tuple(int(v) for v in args.shape.split(","))
    cpus = max(1, args.cpus or 1)

    # Tame threaded BLAS/OpenMP
    os.environ.setdefault("OMP_NUM_THREADS", str(cpus))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

    print(f"HAVE_SCIPY={HAVE_SCIPY}  MODE={args.mode}  CPUS={cpus}  N_VOLS={args.n_vols}  SHAPE={shape}  SIGMA={args.sigma}")
    print("Starting..."); t_global = time.perf_counter()

    results_serial = results_parallel = None
    T1 = Tp = None

    if args.mode in ("serial", "both"):
        results_serial, T1 = run_serial(args.n_vols, shape, args.sigma, args.voxel_mm, args.seed)
        print(f"[SERIAL] total_sec={T1:.3f}  per_vol_median={stats.median(r.elapsed_sec for r in results_serial):.3f}")

    if args.mode in ("parallel", "both"):
        workers = cpus
        results_parallel, Tp = run_parallel(args.n_vols, shape, args.sigma, args.voxel_mm, args.seed, workers=workers)
        print(f"[PARALLEL] workers={workers} total_sec={Tp:.3f}  per_vol_median={stats.median(r.elapsed_sec for r in results_parallel):.3f}")

    t_total = time.perf_counter() - t_global
    print(f"Done in {t_total:.3f}s")

    # Prepare outputs
    rows = []
    if results_serial:  rows += [r for r in results_serial]
    if results_parallel: rows += [r for r in results_parallel]

    summary = {
        "have_scipy": HAVE_SCIPY,
        "mode": args.mode,
        "cpus": cpus,
        "n_vols": args.n_vols,
        "shape": shape,
        "sigma": args.sigma,
        "serial_total_sec": T1,
        "parallel_total_sec": Tp,
        "speedup_S": (T1 / Tp) if (T1 and Tp) else None,
        "efficiency_E": ((T1 / Tp) / cpus) if (T1 and Tp) else None,
    }

    write_csv(args.out_csv, rows or [VolumeResult(0,0,0,0,math.nan,math.nan,0.0)], extra_summary=summary)

    header = [
        f"# Task 2 – CT Benchmark Report",
        f"**Mode:** {args.mode}    **CPUs:** {cpus}    **Volumes:** {args.n_vols}    **Shape:** {shape}    **Sigma:** {args.sigma}",
        f"**SciPy smoothing:** {'yes' if HAVE_SCIPY else 'no (NumPy fallback)'}",
    ]
    sumlines = []
    if T1 is not None:
        sumlines.append(f"- **Serial total:** {T1:.3f}s")
    if Tp is not None:
        sumlines.append(f"- **Parallel total ({cpus} procs):** {Tp:.3f}s")
    if T1 and Tp:
        S = T1 / Tp
        E = S / cpus
        sumlines.append(f"- **Speedup:** S = T1/Tp = {S:.3f}")
        sumlines.append(f"- **Efficiency:** E = S/p = {E:.3f}")

    write_markdown(args.out_md, header, rows[:args.n_vols], sumlines)

    # Final single-line summary for easy grepping in .out
    if T1 and Tp:
        print(f"SUMMARY MODE={args.mode} CPUS={cpus} N={args.n_vols} SHAPE={shape} SIGMA={args.sigma} S={T1/Tp:.3f} E={(T1/Tp)/cpus:.3f}")

if __name__ == "__main__":
    main()


