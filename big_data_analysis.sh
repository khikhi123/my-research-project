#!/bin/bash
#SBATCH --job-name=big_data_analysis
#SBATCH --output=bigdata_%j.out
#SBATCH --error=bigdata_%j.err
#SBATCH --partition=bigmem          # change if your cluster uses a different name
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --mem=128G

set -euo pipefail

echo "Job started at : $(date)"
echo "Node           : $(hostname)"
echo "Job ID         : ${SLURM_JOB_ID:-unknown}"
echo "CPUs per task  : ${SLURM_CPUS_PER_TASK:-8}"
echo "Requested mem  : 128G"

# ---- Activate Python environment ----
if [ -f "$HOME/venvs/ensf619/bin/activate" ]; then
  source "$HOME/venvs/ensf619/bin/activate"
else
  echo "ERROR: venv ~/venvs/ensf619 not found. Create it or load a python module." >&2
  exit 2
fi

# Tame threaded libs (avoid oversubscription)
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONFAULTHANDLER=1

# (Optional) print versions to the log
python3 - <<'PY'
import sys
try:
    import numpy as np, pandas as pd
    print("Python:", sys.version.split()[0])
    print("NumPy :", np.__version__)
    print("pandas:", pd.__version__)
except Exception as e:
    print("Environment import failed:", e, file=sys.stderr)
    sys.exit(3)
PY

# ---- Run analysis ----
python3 << 'EOF'
import os, sys, time, gc, traceback
import numpy as np
import pandas as pd

print("Loading large dataset ...", flush=True)
DATA_SIZE = int(os.environ.get("DATA_SIZE", "50000000"))
rng = np.random.default_rng(42)

# Reduce accidental copies (pandas 2.x)
try:
    pd.options.mode.copy_on_write = True
except Exception:
    pass

df = None
try:
    df = pd.DataFrame({
        "id": np.arange(DATA_SIZE, dtype=np.int64),
        "value1": rng.normal(0.0, 1.0, size=DATA_SIZE),        # float64
        "value2": rng.exponential(2.0, size=DATA_SIZE),        # float64
        "category": pd.Categorical(rng.choice(list("ABC"), size=DATA_SIZE))
    })
    mem_gb = df.memory_usage(deep=True).sum() / 1e9
    print(f"Dataset shape : {df.shape}", flush=True)
    print(f"Memory usage  : {mem_gb:.2f} GB", flush=True)

    print("Computing group statistics ...", flush=True)
    # Use pure NamedAgg (flat columns) and observed=True to avoid extra rows
    result = df.groupby("category", observed=True).agg(
        v1_mean=("value1", "mean"),
        v1_std =("value1", "std"),
        v1_min =("value1", "min"),
        v1_max =("value1", "max"),
        v2_mean=("value2", "mean"),
        v2_std =("value2", "std"),
        v2_min =("value2", "min"),
        v2_max =("value2", "max"),
    )

    # Pretty print
    with pd.option_context("display.max_rows", None, "display.float_format", "{:.6f}".format):
        print("Results:", flush=True)
        print(result, flush=True)

except Exception as e:
    print("ERROR during processing:", repr(e), file=sys.stderr, flush=True)
    traceback.print_exc()
    sys.exit(1)
finally:
    del df
    gc.collect()
    print("Analysis complete!", flush=True)
EOF

echo "Job finished at: $(date)"


