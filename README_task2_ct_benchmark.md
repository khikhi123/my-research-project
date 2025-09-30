#task2_ct_benchmark.py: Synthetic CT-like workload - builds 3D volumes and applies Gaussian smoothing. Supports serial and parallel (Python multiprocessing)

# Quick tests
# Serial (1 CPU)
python3 task2_ct_benchmark.py --mode serial --cpus 1 --n-vols 8 --shape 256,256,128 --sigma 1.2

# Parallel (8 CPUs)
python3 task2_ct_benchmark.py --mode parallel --cpus 8 --n-vols 8 --shape 256,256,128 --sigma 1.2

# SLURM sweep example
# Serial
sbatch --partition=cpu16 --time=00:20:00 --mem=4G \
  --cpus-per-task=1 \
  --wrap="python3 task2_ct_benchmark.py --mode serial --cpus \$SLURM_CPUS_PER_TASK --n-vols 8 --shape 256,256,128 --sigma 1.2"

# Parallel (2,4,8,16 CPUs)
for c in 2 4 8 16; do
  sbatch --partition=cpu16 --time=00:20:00 --mem=4G \
    --cpus-per-task=$c \
    --wrap="python3 task2_ct_benchmark.py --mode parallel --cpus \$SLURM_CPUS_PER_TASK --n-vols 8 --shape 256,256,128 --sigma 1.2"
done

