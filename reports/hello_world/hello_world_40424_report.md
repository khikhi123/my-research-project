# hello_world SLURM Run

**Job ID:** 40424  
**Date:** Mon Sep 29 05:56:56 MDT 2025

## Accounting (sacct)
```
JobID           JobName      State ExitCode    Elapsed     MaxRSS     AveRSS     ReqMem  AllocCPUS 
------------ ---------- ---------- -------- ---------- ---------- ---------- ---------- ---------- 
40424        hello_wor+  COMPLETED      0:0   00:00:01                               1G          1 
40424.batch       batch  COMPLETED      0:0   00:00:01       872K       872K                     1 
40424.extern     extern  COMPLETED      0:0   00:00:01       284K       284K                     1 
```

## Efficiency (seff)
```
Job ID: 40424
Cluster: talc-admin
User/Group: khiran.arumugam/khiran.arumugam
State: COMPLETED (exit code 0)
Cores: 1
CPU Utilized: 00:00:00
CPU Efficiency: 0.00% of 00:00:01 core-walltime
Job Wall-clock time: 00:00:01
Memory Utilized: 872.00 KB
Memory Efficiency: 0.08% of 1.00 GB (1.00 GB/core)
```

## Collected logs
- hello_world_40424.extern_report.md
- hello_world_40424_report.md
- hello_world_40424        _report.md
- hello_world.out
- sacct_40424.extern.txt
- sacct_40424.txt
- sacct_40424        .txt
- seff_40424.extern.txt
- seff_40424.txt
- seff_40424        .txt

## Stdout
```
Job started at : Mon Sep 29 04:54:52 MDT 2025
Running on node : n25
Job ID : 40424
Hello from SLURM!
```
