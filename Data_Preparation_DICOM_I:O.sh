# Data Preparation: DICOM Import -> 3D Volume Construction

# Important to note: Even on a big HPC clusters like ARC, there is a risk of "blowing up" RAM if we read/decompress everythign at once so we need to request the right memory in SLURM. (Stay in int16 cor CT [HU = slope*raw + intercept])
### Setup
## 1. Environment on TALC (bash)
# activate your Python env used earlier
source ~/venvs/ensf619/bin/activate
pip install --upgrade pip
pip install SimpleITK pydicom

## 2. Script (save as dicom_to_nifti.py)
import SimpleITK as sitk
import json, os, argparse

def load_all_series(dicom_dir):
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(dicom_dir)
    if not series_ids:
        raise RuntimeError(f"No DICOM series in {dicom_dir}")
    out = []
    for sid in series_ids:
        files = reader.GetGDCMSeriesFileNames(dicom_dir, sid)
        reader.SetFileNames(files)
        img = reader.Execute()
        out.append((sid, img, files))
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dicom-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--series-index", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    series = load_all_series(args.dicom_dir)
    sid, img, files = series[args.series_index]

    nii_path  = os.path.join(args.out_dir, f"volume_{args.series_index}_{sid}.nii.gz")
    json_path = os.path.join(args.out_dir, f"volume_{args.series_index}_{sid}.json")

    sitk.WriteImage(img, nii_path, useCompression=True)
    meta = {
      "series_uid": sid,
      "size": list(img.GetSize()),
      "spacing": list(img.GetSpacing()),
      "origin": list(img.GetOrigin()),
      "direction": list(img.GetDirection()),
      "n_slices": len(files),
      "first_file": os.path.basename(files[0]),
    }
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=2)

    print("WROTE", nii_path)
    print("META ", json_path)

## 3. Storage Location
# Place inputs and outputs on the fast work file system (e.g., /work/TALC/...) for higher I/O throughput

### Execution Options
## Option A: Small Batch Jobs (Single Series)

# Create dicom_to_nifti_slurm
nano dicom_to_nifti_slurm

#bash

#!/bin/bash
#SBATCH --job-name=dicom2nii
#SBATCH --partition=cpu16
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=dicom2nii_%j.out
#SBATCH --error=dicom2nii_%j.err

set -euo pipefail

# Enable the converter
module load dcm2niix 2>/dev/null || true

# Tame threaded libs (good hygiene)
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# Inputs (EDIT THESE)
IN="/work/TALC/.../SamplePatient/CT_SERIES_1"   # a directory that holds a SINGLE CT series
OUT="/work/TALC/.../outputs/SamplePatient"

mkdir -p "$OUT"

# Convert: gzip-compressed NIfTI + JSON sidecar
dcm2niix -z y -o "$OUT" -f "%s_%p_%t" "$IN"

echo "Done. Outputs in: $OUT"

# ctrl+O, Enter, ctrl+X

# Submit job
sbatch dicom_to_nifti.slurm
squeue -u $USER

###                             OR                              ###

## Option B: Many patients with a SLURM Array (better for scale)
# Create a text file called dicom_folders.txt whith one patient folder per line, specifically where each line is one directory that contains a single CT series of scans (the DICOM Files for one timepoint). Then dicom_array.slurm:
# Tip: Study (CT exam/scan) is the whole imaging session for a patient at a time point while Series is a subset of that study acquired/reconstructed in a single protocol and parameter set. Study contains many series. For our pipeling, we treat one 3D volume = one (axian, thin-slice) series.
# Example of dicom_folders.txt
nano dicom_folders.txt

/work/TALC/datasets/ct/PAT001/CT_SERIES_1
/work/TALC/datasets/ct/PAT002/CT_SERIES_2
/work/TALC/datasets/ct/PAT003/CT_SERIES_1

# ctrl+O, Enter, ctrl+X

nano dicom_array.slurm

#bash

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
module load dcm2niix 2>/dev/null || true

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

LIST="dicom_folders.txt"
IN="$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$LIST")"
[ -z "${IN:-}" ] && { echo "Empty or missing line ${SLURM_ARRAY_TASK_ID}"; exit 2; }

OUT_BASE="/work/TALC/.../outputs"
OUT="${OUT_BASE}/$(basename "$IN")"
mkdir -p "$OUT"

dcm2niix -z y -o "$OUT" -f "%s_%p_%t" "$IN"

echo "Converted: $IN -> $OUT"

# ctrl+O, Enter, ctrl+X

# Submit job
sbatch dicom_array.slurm

## After running option A or B you must document the results

### Results
## What to record?
# 1. Job metadata & resource usage (SLURM)

#bash
# After job completes, replace <JOBID>
sacct -j <JOBID> --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS,ReqMem,AllocCPUS
seff  <JOBID>

# Tu support an interactive session / small CPU job that is appropriate, expect
# State = Completed
# AllocCPUS = 2 [as an example]
# MaxRSS = low [often less than 4 GB]

/usr/bin/time -v python dicom_to_nifti.py --dicom-dir ... --out-dir ... 2>&1 | tee dicom_time.log
# Capture elapsed time and maximum set size

# 2. Output artifacts
# A compressed NIfTI scan: volume_*.nii.gz
# A JSON sidecar wit size/spacing/origin/direction: volume*.json.
# Include a snippet in your report, e.g.,: 

#json
{
  "series_uid": "1.2.840....",
  "size": [512, 512, 320],
  "spacing": [0.742, 0.742, 1.0],
  "n_slices": 320
}
