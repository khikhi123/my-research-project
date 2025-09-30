#!/bin/bash
#SBATCH --job-name=dicom_array
#SBATCH --partition=cpu16
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --array=1-100
#SBATCH --output=dicom_%A_%a.out
#SBATCH --error=dicom_%A_%a.err

set -euo pipefail
source ~/venvs/ensf619/bin/activate
line=$(sed -n "${SLURM_ARRAY_TASK_ID}p" dicom_folders.txt)

outdir="/work/TALC/.../outputs/$(basename "$line")"
python dicom_to_nifti.py --dicom-dir "$line" --out-dir "$outdir"

