#!/bin/bash
#SBATCH --job-name=hello_world
#SBATCH --output=hello_world.out
#SBATCH --time=00:01:00
#SBATCH --partition=cpu16

# Set up environment
echo "Job started at : $(date)"
echo "Running on node : $(hostname)"
echo "Job ID : $SLURM_JOB_ID"

# Do something simple
echo "Hello from SLURM!"

