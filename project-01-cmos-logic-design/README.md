# Project 01 — CMOS Logic Design from First Principles

## Overview

This project develops and characterizes CMOS NAND and NOR logic gates
from transistor-level implementations.

The objective is to connect:

CMOS transistor operation
        ↓
CMOS logic topology
        ↓
LTspice transistor-level simulation
        ↓
Voltage transfer characteristics
        ↓
Noise-margin analysis
        ↓
Transient characterization
        ↓
Power characterization
        ↓
Automated Python characterization

---

## Objectives

- Understand CMOS pull-up and pull-down networks
- Design CMOS NAND and NOR gates
- Verify DC logic behavior
- Extract voltage-transfer characteristics
- Calculate VIL, VIH and noise margins
- Measure rise and fall times
- Extract propagation-delay characteristics
- Measure supply current
- Calculate average power and switching energy
- Automate characterization using Python

---

## Technology

| Parameter | Value |
|---|---:|
| Supply voltage | 5 V |
| Temperature | 27 °C |
| Simulator | LTspice |
| MOS model | standard.mos |
| Analysis | DC + transient |
| Post-processing | Python / NumPy / Matplotlib |

---

# CMOS NAND Gate

## Logic Function

Y = NOT(A · B)

The NAND gate uses:

- PMOS devices in parallel in the pull-up network
- NMOS devices in series in the pull-down network

## Characterization

| Parameter | Result |
|---|---:|
| VOH | 5.000 V |
| VOL | 0.000 V |
| VM | 2.600 V |
| VIL | 1.870 V |
| VIH | 3.460 V |
| NML | 1.870 V |
| NMH | 1.540 V |
| Maximum gain | -6.44 |
| TPHL | 10.24 ns |
| TPLH | 10.13 ns |
| Rise time | 280.04 ps |
| Fall time | 549.51 ps |
| Average power | 17.323 µW |
| Peak current | 242.929 µA |
| Energy / pattern | 346.457 fJ |

---

# CMOS NOR Gate

## Logic Function

Y = NOT(A + B)

The NOR gate uses:

- PMOS devices in series in the pull-up network
- NMOS devices in parallel in the pull-down network

## Static Characterization

| Parameter | Result |
|---|---:|
| VOH | 5.000 V |
| VOL | 0.000 V |
| VM | 2.400 V |
| VIL | 1.538 V |
| VIH | 3.125 V |
| NML | 1.538 V |
| NMH | 1.875 V |
| Maximum gain | -6.44 |

## Timing Characterization

| Parameter | Result |
|---|---:|
| TPHL A | -3.131 ps* |
| TPLH A | 6.164 ps |
| TPHL B | -17.948 ps* |
| TPLH B | 17.273 ps |
| Rise time | 54.982 ps |
| Fall time | 63.529 ps |

\* The TPHL values are raw 50%-to-50% waveform measurements obtained
with the finite-slew transient stimulus. Negative values indicate
threshold-crossing overlap and are not interpreted as negative physical
propagation delay.

## Power Characterization

| Parameter | Result |
|---|---:|
| Average current | 0.316 µA |
| Average power | 1.578 µW |
| Peak current | 58.860 µA |
| Energy / simulation | 78.913 fJ |

---

# Automated Characterization

Python scripts process LTspice exported data and automatically generate:

- VTC plots
- transient/power plots
- CSV characterization summaries
- Markdown characterization reports

The characterization flow is:

LTspice simulation
→ exported waveform data
→ Python parsing
→ numerical extraction
→ plots
→ CSV
→ Markdown report

---

# Key Engineering Observations

### NAND

The NAND gate requires series NMOS devices for the pull-down path
and therefore exhibits different timing and current characteristics
from the NOR implementation.

### NOR

The NOR gate uses parallel NMOS devices and series PMOS devices.
Its measured switching characteristics differ from the NAND gate as
a consequence of the transistor network topology.

The extracted results demonstrate the relationship between CMOS
topology, transistor-level behavior, timing, and power.

---

# Project Status

- [x] CMOS NAND schematic
- [x] CMOS NOR schematic
- [x] DC sweep
- [x] VTC extraction
- [x] Noise-margin extraction
- [x] Transient simulation
- [x] Rise/fall characterization
- [x] Propagation-delay extraction
- [x] Power characterization
- [x] Python automation
- [x] CSV reports
- [x] Markdown reports
- [x] Plots
- [ ] Final repository review