#!/bin/bash
#SBATCH --job-name=task3_sweep
#SBATCH --output=task3_%A_%a.out
#SBATCH --error=task3_%A_%a.err
#SBATCH --partition=cpu16
#SBATCH --time=00:30:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=8        # <— allocate enough cores so 2/4/8-worker runs can actually use them
#SBATCH --array=1-12%3           # <— (optional) run at most 3 array tasks at once

set -euo pipefail

# Activate your Python env
source "$HOME/venvs/ensf619/bin/activate"

# Read the (array)th row from CSV (skip header)
line=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" task3_sweep.csv)
IFS=, read -r cpus sigma z y x nvols <<< "$line"
shape="${z},${y},${x}"

# Tame threaded libs (avoid oversubscription)
export OMP_NUM_THREADS="${cpus}"
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

RID="${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"

# Mode: serial when cpus=1, else parallel
if [ "$cpus" -eq 1 ]; then MODE=serial; else MODE=parallel; fi

echo "RID=${RID} CSV_cpus=${cpus} MODE=${MODE}  SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-unset}"
echo "shape=${shape}  sigma=${sigma}  n_vols=${nvols}"

python3 task2_ct_benchmark.py \
  --mode "$MODE" \
  --cpus "$cpus" \
  --n-vols "$nvols" \
  --shape "$shape" \
  --sigma "$sigma" \
  --out-csv "results_${RID}.csv" \
  --out-md  "report_${RID}.md"

echo "DONE RID=${RID} cpus=${cpus} sigma=${sigma}"

