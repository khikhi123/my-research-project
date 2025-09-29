## Task 2 - Scientific Computing Job
#  A) numerical_analysis.sh: Runs a CPU-boudn numerical demo, activates your venv, and prints timing 

# Run
sbatch numerical_analysis.sh

# Monitor & Inspect
squeue -u $USER
sacct -S today -n -X --name numerical_analysis \
  --format=JobID,State,Elapsed,MaxRSS,ReqMem,AllocCPUS
seff <JOBID>

# Logs produced by the script (if applicable)
ls -1 analysis_*.out analysis_*.err 2>/dev/null
tail -n +1 analysis_*.out analysis_*.err

