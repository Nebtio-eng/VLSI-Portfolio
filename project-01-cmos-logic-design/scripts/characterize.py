"""
============================================================
CMOS Characterization Tool
Project : CMOS Logic Design from First Principles
Author  : Benito A.T.
Version : 1.0
============================================================

Current Features
----------------
✓ File browser
✓ LTspice format verification
✓ Automatic data loading
✓ VOH calculation
✓ VOL calculation
✓ VM calculation

Future Features
---------------
□ Gain
□ VIL
□ VIH
□ Noise Margin
□ Plot Generation
□ CSV Export
□ Markdown Report
□ Engineering Report
"""

from pathlib import Path
from tkinter import Tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter.filedialog import askopenfilename
from datetime import datetime
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd


# ============================================================
# Characterization Report Layout
# ============================================================

STATIC_PARAMETERS = [
    ("VOH", "V", 4),
    ("VOL", "V", 4),
    ("VM", "V", 4),
    ("VIL", "V", 4),
    ("VIH", "V", 4),
    ("NML", "V", 4),
    ("NMH", "V", 4),
    ("Maximum Gain", "V/V", 2),
]

TIMING_PARAMETERS = [
    ("TPHL", "ps", 2),
    ("TPLH", "ps", 2),
    ("Rise Time", "ps", 2),
    ("Fall Time", "ps", 2),
    ("Average Delay", "ps", 2),
]

POWER_PARAMETERS = [
    ("Average Current", "µA", 3),
    ("Average Power", "µW", 3),
    ("Peak Current", "µA", 3),
    ("Minimum Current", "µA", 3),
    ("Energy per Transition", "fJ", 3),
]

# ============================================================
# Unit Conversion
# ============================================================

def format_value(parameter, value):
    """
    Convert SI units into engineering units for display.
    """

    if parameter in ["TPHL", "TPLH", "Rise Time", "Fall Time", "Average Delay"]:
        return value * 1e12

    if parameter in ["Average Current", "Peak Current", "Minimum Current"]:
        return value * 1e6

    if parameter == "Average Power":
        return value * 1e6

    if parameter == "Energy per Transition":
        return value * 1e15

    return value


# ============================================================
# File Selection
# ============================================================

def select_file() -> Path:
    """
    Opens a file browser and returns the selected LTspice export.
    """

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    filename = askopenfilename(
        title="Select LTspice DC Sweep Export",
        filetypes=[
            ("Text Files", "*.txt"),
            ("All Files", "*.*")
        ]
    )

    if not filename:
        raise SystemExit("No file selected.")

    return Path(filename)

# ============================================================
# Select Timing Log
# ============================================================

def select_timing_log():

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    filename = askopenfilename(
        title="Select LTspice Timing Log",
        filetypes=[
            ("Text Files", "*.txt"),
            ("Log Files", "*.log"),
            ("All Files", "*.*")
        ]
    )

    if not filename:
        raise SystemExit("No timing log selected.")

    return Path(filename)



# ============================================================
# Design Name
# ============================================================

def get_design_name():
    """
    Ask the user for the design name.

    Examples
    --------
    inverter
    nand
    xor
    INV_X1
    NAND2_X2
    """

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    design_name = simpledialog.askstring(
        title="Design Name",
        prompt="Enter Design Name:"
    )

    if design_name is None:
        raise SystemExit("Operation cancelled.")

    design_name = design_name.strip()

    if design_name == "":
        raise ValueError("Design name cannot be empty.")

    return design_name



# ============================================================
# File Verification
# ============================================================

def verify_file(df: pd.DataFrame):

    required_columns = [
        "V(vin)",
        "V(vout)"
    ]

    missing = []

    for column in required_columns:
        if column not in df.columns:
            missing.append(column)

    if missing:

        message = (
            "Invalid LTspice export.\n\n"
            "Missing columns:\n"
            + "\n".join(missing)
        )

        messagebox.showerror("Verification Failed", message)

        raise ValueError(message)


# ============================================================
# Load Data
# ============================================================

def load_data(file_path: Path):

    df = pd.read_csv(
        file_path,
        sep=r"\s+"
    )

    verify_file(df)

    vin = df["V(vin)"].to_numpy()
    vout = df["V(vout)"].to_numpy()

    return vin, vout

import re

# ============================================================
# Load Timing Results
# ============================================================

def load_timing_results(log_file):

    measurements = {}

    with open(log_file, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip().lower()

            if line.startswith("tphl="):
                measurements["TPHL"] = float(line.split("=")[1].split()[0])

            elif line.startswith("tplh="):
                measurements["TPLH"] = float(line.split("=")[1].split()[0])

            elif line.startswith("rise_time="):
                measurements["Rise Time"] = float(line.split("=")[1].split()[0])

            elif line.startswith("fall_time="):
                measurements["Fall Time"] = float(line.split("=")[1].split()[0])

            elif line.startswith("iavg:"):
                measurements["Average Current"] = float(line.split("=")[1].split()[0])

            elif line.startswith("imax:"):
                measurements["Peak Current"] = float(line.split("=")[1].split()[0])

            elif line.startswith("imin:"):
                measurements["Minimum Current"] = float(line.split("=")[1].split()[0])

    required = [
        "TPHL",
        "TPLH",
        "Rise Time",
        "Fall Time",
        "Average Current",
        "Peak Current",
        "Minimum Current",
    ]

    for item in required:
        if item not in measurements:
            raise ValueError(f"Could not find '{item}' in timing log.")

    measurements["Average Delay"] = (
        measurements["TPHL"] +
        measurements["TPLH"]
    ) / 2

    VDD = 5.0
    CLOCK_PERIOD = 10e-9

    measurements["Average Power"] = abs(measurements["Average Current"]) * VDD

    measurements["Energy per Transition"] = (
        measurements["Average Power"] * CLOCK_PERIOD
    )

    return measurements

# ============================================================
# Characterization
# ============================================================

def calculate_static_parameters(vin, vout):

    voh = np.max(vout)

    vol = np.min(vout)

    vm_index = np.argmin(np.abs(vin - vout))

    vm = vin[vm_index]

    return {
        "VOH": voh,
        "VOL": vol,
        "VM": vm
    }


# ============================================================
# Gain Calculation
# ============================================================

def calculate_gain(vin, vout):
    """
    Calculate the derivative dVout/dVin.
    """

    gain = np.gradient(vout, vin)

    return gain


# ============================================================
# Maximum Gain
# ============================================================

def calculate_max_gain(gain):
    """
    Returns the steepest negative gain.
    """

    return np.min(gain)


# ============================================================
# VIL / VIH
# ============================================================

def calculate_vil_vih(vin, gain):
    """
    Finds the two locations where gain is closest to -1.
    """

    indices = np.where(np.diff(np.sign(gain + 1)))[0]

    if len(indices) < 2:
        raise ValueError(
            "Could not determine VIL and VIH.\n"
            "Increase the DC sweep resolution."
        )

    vil = vin[indices[0]]
    vih = vin[indices[-1]]

    return vil, vih

# ============================================================
# Noise Margins
# ============================================================

def calculate_noise_margin(voh, vol, vil, vih):

    nml = vil - vol
    nmh = voh - vih

    return nml, nmh

# ============================================================
# Display Results
# ============================================================

def print_results(results, selected_file):

    print()

    print("=" * 60)
    print(" CMOS INVERTER CHARACTERIZATION")
    print("=" * 60)

    print(f"Selected File : {selected_file}")

    print("-" * 60)

    print(f"VOH : {results['VOH']:.4f} V")
    print(f"VOL : {results['VOL']:.4f} V")
    print(f"VM  : {results['VM']:.4f} V")

    print()

    print(f"VIL : {results['VIL']:.4f} V")
    print(f"VIH : {results['VIH']:.4f} V")

    print()

    print(f"NML : {results['NML']:.4f} V")
    print(f"NMH : {results['NMH']:.4f} V")

    print()

    print(f"Maximum Gain : {results['Maximum Gain']:.2f}")

    print()
    print("-" * 60)
    print("TIMING CHARACTERIZATION")
    print("-" * 60)

    print(f"TPHL            : {results['TPHL']*1e12:.2f} ps")
    print(f"TPLH            : {results['TPLH']*1e12:.2f} ps")
    print(f"Rise Time       : {results['Rise Time']*1e12:.2f} ps")
    print(f"Fall Time       : {results['Fall Time']*1e12:.2f} ps")
    print(f"Average Delay   : {results['Average Delay']*1e12:.2f} ps")

    print()
    print("-" * 60)
    print("POWER CHARACTERIZATION")
    print("-" * 60)

    print(
        f"Average Current      : "
        f"{results['Average Current']*1e6:.3f} µA"
    )

    print(
        f"Average Power        : "
        f"{results['Average Power']*1e6:.3f} µW"
    )

    print(
        f"Peak Current         : "
        f"{results['Peak Current']*1e6:.3f} µA"
    )

    print(
        f"Minimum Current      : "
        f"{results['Minimum Current']*1e6:.3f} µA"
    )

    print(
        f"Energy / Transition  : "
        f"{results['Energy per Transition']*1e15:.3f} fJ"
    )

# ============================================================
# Save Engineering Report
# ============================================================

def save_report(results, design_name, selected_file):
    """
    Saves a professional engineering report.
    """

    project_root = Path(__file__).resolve().parent.parent

    report_dir = project_root / "reports"

    report_dir.mkdir(exist_ok=True)

    report_file = report_dir / f"{design_name}_characterization_report.txt"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(report_file, "w", encoding="utf-8") as report:

        # ------------------------------------------------------------
        # Static Characterization
        # ------------------------------------------------------------

        report.write("-" * 60 + "\n")
        report.write("STATIC CHARACTERIZATION\n")
        report.write("-" * 60 + "\n\n")

        for parameter, unit, precision in STATIC_PARAMETERS:

            value = format_value(parameter, results[parameter])

            report.write(
                f"{parameter:<22}: {value:.{precision}f} {unit}\n"
            )

        report.write("\n")

        # ------------------------------------------------------------
        # Timing Characterization
        # ------------------------------------------------------------

        report.write("-" * 60 + "\n")
        report.write("TIMING CHARACTERIZATION\n")
        report.write("-" * 60 + "\n\n")

        for parameter, unit, precision in TIMING_PARAMETERS:

            value = format_value(parameter, results[parameter])

            report.write(
                f"{parameter:<22}: {value:.{precision}f} {unit}\n"
            )

        report.write("\n")

        # ------------------------------------------------------------
        # Power Characterization
        # ------------------------------------------------------------

        report.write("-" * 60 + "\n")
        report.write("POWER CHARACTERIZATION\n")
        report.write("-" * 60 + "\n\n")

        for parameter, unit, precision in POWER_PARAMETERS:

            value = format_value(parameter, results[parameter])

            report.write(
                f"{parameter:<22}: {value:.{precision}f} {unit}\n"
            )

        report.write("\n")


# ============================================================
# Generate VTC Plot
# ============================================================

def generate_vtc_plot(vin, vout, results, design_name):

    project_root = Path(__file__).resolve().parent.parent

    image_dir = project_root / "images"

    image_dir.mkdir(exist_ok=True)

    output_file = image_dir / f"{design_name}_vtc_plot.png"

    plt.figure(figsize=(8, 6))

    plt.plot(
        vin,
        vout,
        linewidth=2,
        label="Voltage Transfer Curve"
    )

    plt.scatter(
        results["VM"],
        results["VM"],
        s=80,
        label="VM"
    )

    plt.scatter(
        results["VIL"],
        np.interp(results["VIL"], vin, vout),
        s=80,
        label="VIL"
    )

    plt.scatter(
        results["VIH"],
        np.interp(results["VIH"], vin, vout),
        s=80,
        label="VIH"
    )

    plt.xlabel("Input Voltage (V)")
    plt.ylabel("Output Voltage (V)")

    plt.title(f"{design_name} Voltage Transfer Characteristic")

    plt.grid(True)

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        output_file,
        dpi=300
    )

    plt.close()

    print(f"VTC Plot saved to:\n{output_file}")

# ============================================================
# Save CSV Summary
# ============================================================

def save_csv(results, design_name):

    project_root = Path(__file__).resolve().parent.parent

    csv_file = (
        project_root
        / "simulations"
        / f"{design_name}_characterization_summary.csv"
    )

    rows = []

    for section in (
            STATIC_PARAMETERS,
            TIMING_PARAMETERS,
            POWER_PARAMETERS,
        ):

            for parameter, unit, precision in section:

                rows.append({

                    "Parameter": parameter,

                    "Value": format_value(parameter,results[parameter]),
                    "Unit": unit

                })

    df = pd.DataFrame(rows)
    df.to_csv(csv_file, index=False)

    print(f"CSV Summary saved to:\n{csv_file}")

# ============================================================
# Save Markdown Report
# ============================================================

def save_markdown(results, design_name):

    project_root = Path(__file__).resolve().parent.parent

    md_file = (
        project_root
        / "calculations"
        / f"{design_name}_characterization.md"
    )

    with open(md_file, "w", encoding="utf-8") as f:

        sections = [

            ("Static Characterization", STATIC_PARAMETERS),

            ("Timing Characterization", TIMING_PARAMETERS),

            ("Power Characterization", POWER_PARAMETERS),

        ]

        for title, parameters in sections:

            f.write(f"## {title}\n\n")

            f.write("| Parameter | Value | Unit |\n")
            f.write("|-----------|------:|:----:|\n")

            for parameter, unit, precision in parameters:

                value = format_value(
                    parameter,
                    results[parameter]
                )

                f.write(
                    f"| {parameter} | "
                    f"{value:.{precision}f} | "
                    f"{unit} |\n"
                )

            f.write("\n")

    print(f"Markdown Report saved to:\n{md_file}")




# ============================================================
# Main
# ============================================================

def main():

    selected_file = select_file()

    timing_log = select_timing_log()

    design_name = get_design_name()

    vin, vout = load_data(selected_file)

    results = calculate_static_parameters(
        vin,
        vout
    )

    timing_results = load_timing_results(timing_log)

    results.update(timing_results)

    gain = calculate_gain(vin, vout)

    max_gain = calculate_max_gain(gain)

    vil, vih = calculate_vil_vih(vin, gain)

    nml, nmh = calculate_noise_margin(
        results["VOH"],
        results["VOL"],
                vil,
                vih
                    )

    results["Maximum Gain"] = max_gain
    results["VIL"] = vil
    results["VIH"] = vih
    results["NML"] = nml
    results["NMH"] = nmh

    print_results(
        results,
        selected_file
    )

    save_report(
    results,
    design_name,
    selected_file
            )

    generate_vtc_plot(
    vin,
    vout,
    results,
    design_name
            )

    save_csv(
    results,
    design_name
    )

    save_markdown(
    results,
    design_name
        )

    print()
    print(f"Design Name : {design_name}")


if __name__ == "__main__":
    main()