#!/bin/bash
#SBATCH --job-name=dicom2nii
#SBATCH --partition=cpu16
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=dicom2nii_%j.out
#SBATCH --error=dicom2nii_%j.err

set -euo pipefail
source ~/venvs/ensf619/bin/activate

python dicom_to_nifti.py \
  --dicom-dir /work/TALC/.../SamplePatient \
  --out-dir  /work/TALC/.../outputs/SamplePatient

