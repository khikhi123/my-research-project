#!/bin/bash
#SBATCH --job-name=numerical_analysis
#SBATCH --output=analysis_%j.out
#SBATCH --error=analysis_%j.err
#SBATCH --partition=cpu16
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --time=00:20:00
#SBATCH --mem=4G

# --- Python environment (choose ONE of the sections below) ---

## Option A: Use a venv in your home (recommended; no modules needed)
source ~/venvs/ensf619/bin/activate

## Option B: Use a Python module instead of venv (comment out Option A if using this)
# module purge
# module avail python            # for discovery (interactive)
# module load python/3.10        # <-- adjust to a version that exists on TALC

# Make OpenMP/BLAS not fight with multiprocessing
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

python3 << 'EOF'
import numpy as np
import multiprocessing as mp
import time, os

def monte_carlo_pi(n: int, seed=None) -> float:
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1.0, 1.0, n)
    y = rng.uniform(-1.0, 1.0, n)
    inside = np.count_nonzero(x*x + y*y <= 1.0)
    return 4.0 * inside / n

if __name__ == "__main__":
    n_total = 5_000_000  # start small; scale after it works
    n_proc  = min(16, os.cpu_count() or 16)
    n_per   = n_total // n_proc

    seeds = [int(time.time()) + i for i in range(n_proc)]

    t0 = time.time()
    with mp.Pool(processes=n_proc) as pool:
        ests = pool.starmap(monte_carlo_pi, [(n_per, s) for s in seeds])

    rem = n_total - n_per * n_proc
    if rem:
        ests.append(monte_carlo_pi(rem, seeds[-1]+1))

    pi_est = float(np.mean(ests))
    dt = time.time() - t0

    print(f"Job started at : {time.ctime()}")
    print(f"Running on node: {os.uname().nodename}")
    print(f"SLURM_CPUS_PER_TASK: {os.environ.get('SLURM_CPUS_PER_TASK')}")
    print(f"Processes used : {n_proc}")
    print(f"Total samples  : {n_total:,}")
    print(f"Pi estimate    : {pi_est:.8f}")
    print(f"Abs error      : {abs(pi_est - np.pi):.8f}")
    print(f"Elapsed (s)    : {dt:.2f}")
EOF

