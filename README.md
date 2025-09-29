# From my working repo (e.g., ~/ensf619-local)
cat > README.md <<'MARKDOWN'
# HPC SLURM Assignment 4 – Tasks 2 & 3

This repo contains SLURM job scripts and Python code used to:
- run and time CPU-heavy scientific workloads,
- scale them from serial to parallel,
- sweep parameters with a job array,
- collect results and make plots.

---

## Prerequisites

- Python venv at `~/venvs/ensf619` with: `numpy`, `pandas`, `matplotlib`
  ```bash
  source ~/venvs/ensf619/bin/activate
  pip install --upgrade numpy pandas matplotlib
  deactivate

# ENSF 619 Project
