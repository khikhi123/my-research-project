#!/usr/bin/env python3
import os, re, json, subprocess, glob, csv
import pandas as pd
import matplotlib.pyplot as plt

# Find all per-run CSVs (created by the array job)
csvs = sorted(glob.glob("results_*_*.csv"))  # results_<ARR>_<TASK>.csv
if not csvs:
    raise SystemExit("No results_*.csv files found. Run the array first.")

rows = []
for path in csvs:
    # Extract job ids like 40450_3 from filename
    m = re.search(r"results_(\d+_\d+)\.csv$", path)
    if not m: 
        continue
    jobstep = m.group(1)

    # Parse CSV head (per-volume rows) + trailing JSON summary
    # The file was written by task2_ct_benchmark.py with a "# SUMMARY\n{json}" tail
    with open(path, "r") as f:
        lines = f.read().splitlines()
    # find JSON tail
    jstart = [i for i,ln in enumerate(lines) if ln.strip()=="# SUMMARY"]
    if jstart:
        j = jstart[0] + 1
        js = "\n".join(lines[j:])
        summary = json.loads(js)
    else:
        summary = {}

    # Pull run parameters
    cpus   = int(summary.get("cpus", 1))
    mode   = summary.get("mode", "parallel")
    n_vols = int(summary.get("n_vols", 0))
    shape  = tuple(summary.get("shape", [])) or None
    sigma  = float(summary.get("sigma", 0.0))

    # Get wall time & resources from sacct (ElapsedRaw in seconds)
    try:
        out = subprocess.check_output(
            ["sacct","-j",jobstep,"-n","-X","--format=JobIDRaw,ElapsedRaw,MaxRSS,ReqMem,AllocCPUS"],
            text=True
        ).strip().splitlines()
        # first line is the parent step, others are .batch/.extern
        jidraw, elapsed_raw, maxrss, reqmem, alloc = out[0].split()
        elapsed_s = float(elapsed_raw)
    except Exception as e:
        elapsed_s = float("nan"); maxrss=""; reqmem=""; alloc=str(cpus)

    rows.append({
        "jobstep": jobstep,
        "mode": mode,
        "cpus": cpus,
        "sigma": sigma,
        "n_vols": n_vols,
        "shape": shape,
        "elapsed_s": elapsed_s,
        "maxrss": maxrss,
        "reqmem": reqmem
    })

df = pd.DataFrame(rows)
if df.empty: raise SystemExit("No rows parsed.")

# Compute speedup/efficiency per sigma, using the 1-CPU run as baseline
summ = []
plots_dir = "plots_task3"; os.makedirs(plots_dir, exist_ok=True)

for s in sorted(df["sigma"].unique()):
    d = df[df["sigma"]==s].copy()
    base = d[d["cpus"]==1]
    if base.empty:
        continue
    T1 = float(base["elapsed_s"].iloc[0])
    d["speedup_S"] = T1 / d["elapsed_s"]
    d["eff_E"]     = d["speedup_S"] / d["cpus"]
    summ.append(d)

    # Plot: elapsed vs cpus
    d.sort_values("cpus").plot(x="cpus", y="elapsed_s", marker="o", legend=False)
    plt.xlabel("CPUs"); plt.ylabel("Elapsed (s)"); plt.title(f"Elapsed vs CPUs (sigma={s})")
    plt.savefig(f"{plots_dir}/elapsed_vs_cpus_sigma_{s}.png", dpi=150); plt.clf()

    # Plot: speedup vs cpus (with y=x ideal)
    d.sort_values("cpus").plot(x="cpus", y="speedup_S", marker="o", legend=False)
    xmax = int(d["cpus"].max())
    plt.plot([1,xmax],[1,xmax], linestyle="--")  # ideal line
    plt.xlabel("CPUs"); plt.ylabel("Speedup S"); plt.title(f"Speedup vs CPUs (sigma={s})")
    plt.savefig(f"{plots_dir}/speedup_vs_cpus_sigma_{s}.png", dpi=150); plt.clf()

    # Plot: efficiency vs cpus
    d.sort_values("cpus").plot(x="cpus", y="eff_E", marker="o", legend=False)
    plt.xlabel("CPUs"); plt.ylabel("Parallel efficiency E"); plt.title(f"Efficiency vs CPUs (sigma={s})")
    plt.savefig(f"{plots_dir}/efficiency_vs_cpus_sigma_{s}.png", dpi=150); plt.clf()

df2 = pd.concat(summ, ignore_index=True)
df.to_csv("task3_runs_raw.csv", index=False)
df2.to_csv("task3_runs_with_speedup.csv", index=False)

# Quick Markdown summary
with open("task3_summary.md","w") as f:
    f.write("# Task 3 – Parameter Sweep Summary\n\n")
    for s in sorted(df2["sigma"].unique()):
        d = df2[df2["sigma"]==s].sort_values("cpus")
        T1 = d.loc[d["cpus"]==1,"elapsed_s"].iloc[0]
        f.write(f"## sigma={s}\n")
        f.write(f"- Baseline T1 (1 CPU): **{T1:.3f}s**\n")
        f.write("| CPUs | Elapsed (s) | Speedup S | Efficiency E |\n|---:|---:|---:|---:|\n")
        for _,r in d.iterrows():
            f.write(f"| {int(r.cpus)} | {r.elapsed_s:.3f} | {r.speedup_S:.3f} | {r.eff_E:.3f} |\n")
        f.write("\n")

print("Wrote task3_runs_raw.csv, task3_runs_with_speedup.csv, task3_summary.md and plots in plots_task3/")

