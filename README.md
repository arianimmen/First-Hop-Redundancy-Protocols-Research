# Automated Evaluation of FHRPs Using Python and GNS3

This repository contains the implementation, datasets, and analysis for the study:

**Automated Evaluation of First Hop Redundancy Protocols (VRRP and HSRP) Using Python and GNS3**  
A. Immen, 2025

The project provides a fully automated and reproducible framework to evaluate the performance of First Hop Redundancy Protocols (FHRPs), specifically **VRRP** and **HSRP**, under controlled failure scenarios.

---

## Abstract

This study introduces a fully automated approach for evaluating First Hop Redundancy Protocols (VRRP and HSRP) using Python and GNS3. Previous comparisons were often limited by small datasets or relied on manual or semi-automated measurements.

To address these limitations, a Python-based automation script was developed that:
- Triggers controlled router failures
- Collects router CPU statistics via Telnet
- Gathers protocol and failover logs in CSV format for analysis

Each protocol was evaluated using **500 automated failover trials**. After data cleaning, the final dataset consists of:
- **473 VRRP samples**
- **455 optimized HSRP samples**
- **431 default HSRP samples**

Results show that:
- With default timers, **VRRP outperforms HSRP overall**
- **HSRP with optimized timers** outperforms VRRP in failover speed, at the cost of **increased packet loss and higher CPU utilization**

This repository includes the automation scripts, datasets, and Jupyter notebooks used for analysis, enabling reproducible experiments for network engineers and researchers.

---

## Repository Structure
```
.
├── scripts/ # Python automation scripts
├── datasets/ # Collected CSV datasets
├── notebooks/ # Jupyter notebooks for analysis and visualization
├── gns3/ # GNS3 project files and topology
└── README.md
```
## Reproducibility

All experiments are designed to be reproducible.  
You can rerun the automation scripts to generate new datasets or modify protocol timers and topology parameters for further research.

---

## Citation

If you use this work in academic or professional research, please cite:

A. Immen, “Automated Evaluation of FHRPs Using Python and GNS3,”
GitHub repository, 2025.
Available: https://github.com/arianimmen/First-Hop-Redundancy-Protocols-Research/


