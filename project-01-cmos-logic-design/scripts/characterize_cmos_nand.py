"""
CMOS NAND Gate Characterization
================================

Automated DC characterization of a 2-input CMOS NAND gate.

The script:
    1. Selects an LTspice exported VTC data file.
    2. Validates the input data.
    3. Extracts VIN and VOUT.
    4. Calculates static characterization metrics.
    5. Generates a VTC plot.
    6. Generates CSV and Markdown reports.

Expected LTspice export:
    V2
    V(out)

The other columns, if present, are ignored.

Author:
    VLSI Portfolio - Project 01
"""

# ============================================================
# Imports
# ============================================================

import csv
import os
import tkinter as tk
import re
from tkinter import filedialog

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# File Selection
# ============================================================

def select_file():
    """
    Open a file browser and allow the user to select
    the LTspice VTC export file.
    """

    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select NAND VTC Data File",
        filetypes=[
            ("Text files", "*.txt"),
            ("CSV files", "*.csv"),
            ("All files", "*.*")
        ]
    )

    root.destroy()

    if not file_path:
        raise FileNotFoundError(
            "No VTC data file was selected."
        )

    return file_path

def select_timing_log():
    """
    Open a file browser and allow the user to select
    the LTspice transient measurement log.
    """

    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select NAND LTspice Timing/Power Log",
        filetypes=[
            ("Log files", "*.log"),
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
    )

    root.destroy()

    if not file_path:
        raise FileNotFoundError(
            "No LTspice timing/power log was selected."
        )

    return file_path



# ============================================================
# LTspice Data Loading
# ============================================================

## def load_data(file_path):
    """
    Load VIN and VOUT from an LTspice exported data file.

    Expected columns include:

        V2
        V(out)

    Additional LTspice columns are ignored.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    if not lines:
        raise ValueError(
            "The selected file is empty."
        )
def load_data(file_path):
    """
    Load VIN and VOUT from the LTspice NAND VTC export.
    """

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        lines = file.readlines()

    if not lines:
        raise ValueError(
            "The selected VTC file is empty."
        )

    # --------------------------------------------------------
    # Find LTspice header
    # --------------------------------------------------------

    header_index = None

    for index, line in enumerate(lines):

        stripped = line.strip()

        if "V2" in stripped and "V(out)" in stripped:
            header_index = index
            break

    if header_index is None:
        raise ValueError(
            "Could not find V2 and V(out) "
            "in the selected VTC file."
        )

    header = lines[header_index].strip()

    # --------------------------------------------------------
    # Determine columns
    # --------------------------------------------------------

    columns = header.split("\t")

    if len(columns) < 2:
        columns = header.split()

    normalized_columns = [
        column.strip().lower()
        for column in columns
    ]

    try:
        vin_index = normalized_columns.index("v2")
    except ValueError:
        raise ValueError(
            "Could not find the V2 input column."
        )

    vout_index = None

    for index, column in enumerate(
        normalized_columns
    ):

        if column in (
            "v(out)",
            "v(out )"
        ):

            vout_index = index
            break

    if vout_index is None:
        raise ValueError(
            "Could not find the V(out) output column."
        )

    # --------------------------------------------------------
    # Read numerical data
    # --------------------------------------------------------

    vin = []
    vout = []

    for line in lines[
        header_index + 1:
    ]:

        stripped = line.strip()

        if not stripped:
            continue

        parts = stripped.split("\t")

        if len(parts) <= max(
            vin_index,
            vout_index
        ):

            parts = stripped.split()

        try:

            input_value = float(
                parts[vin_index]
            )

            output_value = float(
                parts[vout_index]
            )

        except (
            ValueError,
            IndexError
        ):

            continue

        vin.append(input_value)
        vout.append(output_value)

    if len(vin) < 10:
        raise ValueError(
            "Insufficient numerical VTC data found."
        )

    vin = np.array(vin)
    vout = np.array(vout)

    # --------------------------------------------------------
    # Sort by input voltage
    # --------------------------------------------------------

    sort_indices = np.argsort(vin)

    vin = vin[sort_indices]
    vout = vout[sort_indices]

    return vin, vout

def load_timing_results(log_file):
    """
    Extract timing and raw power measurements from
    the LTspice SPICE Error Log.
    """

    with open(
        log_file,
        "r",
        encoding="utf-8"
    ) as file:

        text = file.read()

    patterns = {
        "TPHL":
            r"tphl=([+-]?[0-9.eE+-]+)",

        "TPLH":
            r"tplh=([+-]?[0-9.eE+-]+)",

        "Rise Time":
            r"rise_time=([+-]?[0-9.eE+-]+)",

        "Fall Time":
            r"fall_time=([+-]?[0-9.eE+-]+)",

        "Average Current":
            r"iavg:\s*AVG\(I\(V1\)\)=([+-]?[0-9.eE+-]+)",

        "Peak Current":
            r"imax:\s*MAX\(ABS\(I\(V1\)\)\)=([+-]?[0-9.eE+-]+)",

        "Minimum Current":
            r"imin:\s*MIN\(I\(V1\)\)=([+-]?[0-9.eE+-]+)"
    }

    results = {}

    for key, pattern in patterns.items():

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match is None:
            raise ValueError(
                f"Could not find '{key}' in LTspice log."
            )

        results[key] = float(
            match.group(1)
        )

    return results


    # --------------------------------------------------------
    # Locate the header
    # --------------------------------------------------------

    header_index = None

    for index, line in enumerate(lines):

        stripped = line.strip()

        if "V2" in stripped and "V(out)" in stripped:
            header_index = index
            break

    if header_index is None:
        raise ValueError(
            "Could not find the expected LTspice columns "
            "'V2' and 'V(out)'."
        )

    header = lines[header_index].strip()

    # --------------------------------------------------------
    # Determine column positions
    # --------------------------------------------------------

    columns = header.split("\t")

    if len(columns) < 2:
        columns = header.split()

    normalized_columns = [
        column.strip().lower()
        for column in columns
    ]

    try:
        vin_index = normalized_columns.index("v2")
    except ValueError:
        raise ValueError(
            "Could not find the V2 input column."
        )

    # LTspice may represent the output with slightly
    # different capitalization.
    vout_index = None

    for index, column in enumerate(normalized_columns):

        if column in ("v(out)", "v(out )"):
            vout_index = index
            break

    if vout_index is None:
        raise ValueError(
            "Could not find the V(out) output column."
        )

    # --------------------------------------------------------
    # Read numerical data
    # --------------------------------------------------------

    vin = []
    vout = []

    for line in lines[header_index + 1:]:

        stripped = line.strip()

        if not stripped:
            continue

        parts = stripped.split("\t")

        if len(parts) <= max(vin_index, vout_index):
            parts = stripped.split()

        try:
            input_value = float(parts[vin_index])
            output_value = float(parts[vout_index])

        except (ValueError, IndexError):
            continue

        vin.append(input_value)
        vout.append(output_value)

    if len(vin) < 10:
        raise ValueError(
            "Insufficient numerical data was found."
        )

    vin = np.array(vin)
    vout = np.array(vout)

    # --------------------------------------------------------
    # Sort by input voltage
    # --------------------------------------------------------

    sort_indices = np.argsort(vin)

    vin = vin[sort_indices]
    vout = vout[sort_indices]

    return vin, vout


# ============================================================
# Static Parameters
# ============================================================

def calculate_static_parameters(vin, vout):
    """
    Calculate VOH, VOL and VM.
    """

    voh = np.max(vout)
    vol = np.min(vout)

    # Switching threshold:
    # point where VIN and VOUT are closest.
    vm_index = np.argmin(
        np.abs(vin - vout)
    )

    vm = vin[vm_index]

    return {
        "VOH": voh,
        "VOL": vol,
        "VM": vm
    }


# ============================================================
# Gain
# ============================================================

def calculate_gain(vin, vout):
    """
    Calculate dVOUT/dVIN using numerical differentiation.
    """

    gain = np.gradient(vout, vin)

    return gain


def calculate_max_gain(gain):
    """
    Return the most negative gain of the inverter-like
    NAND VTC.
    """

    return np.min(gain)


# ============================================================
# VIL / VIH
# ============================================================

def calculate_vil_vih(vin, gain):
    """
    Find the two locations where the VTC slope crosses -1.
    """

    target = gain + 1

    crossing_indices = np.where(
        np.diff(np.sign(target))
    )[0]

    if len(crossing_indices) < 2:

        raise ValueError(
            "Could not determine VIL and VIH.\n"
            "Increase the DC sweep resolution."
        )

    vil = vin[crossing_indices[0]]
    vih = vin[crossing_indices[-1]]

    return vil, vih


# ============================================================
# Noise Margins
# ============================================================

def calculate_noise_margin(
    voh,
    vol,
    vil,
    vih
):
    """
    Calculate low and high noise margins.
    """

    nml = vil - vol
    nmh = voh - vih

    return nml, nmh

def calculate_dynamic_parameters(
    timing_results,
    vdd=5.0,
    pattern_period=20e-9
):
    """
    Calculate derived timing and power parameters.

    Average power and energy are calculated in Python
    from the raw LTspice current measurement.
    """

    tphl = timing_results["TPHL"]
    tplh = timing_results["TPLH"]

    average_current = timing_results[
        "Average Current"
    ]

    peak_current = timing_results[
        "Peak Current"
    ]

    minimum_current = timing_results[
        "Minimum Current"
    ]

    rise_time = timing_results[
        "Rise Time"
    ]

    fall_time = timing_results[
        "Fall Time"
    ]

    # Average propagation delay
    average_delay = (
        tphl + tplh
    ) / 2

    # Average power
    average_power = (
        vdd *
        abs(average_current)
    )

    # Energy over one complete 20 ns
    # input pattern
    energy_per_pattern = (
        average_power *
        pattern_period
    )

    return {
        "TPHL": tphl,
        "TPLH": tplh,
        "Rise Time": rise_time,
        "Fall Time": fall_time,
        "Average Delay": average_delay,
        "Average Current": average_current,
        "Peak Current": peak_current,
        "Minimum Current": minimum_current,
        "Average Power": average_power,
        "Energy / Pattern": energy_per_pattern
    }

# ============================================================
# Plot
# ============================================================

def generate_plot(
    vin,
    vout,
    vil,
    vih,
    vm,
    output_directory
):
    """
    Generate and save the NAND voltage transfer curve.
    """

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    output_path = os.path.join(
        output_directory,
        "cmos_nand_vtc_plot.png"
    )

    plt.figure(figsize=(8, 5))

    plt.plot(
        vin,
        vout,
        label="CMOS NAND VTC"
    )

    plt.axvline(
        vil,
        linestyle="--",
        label=f"VIL = {vil:.3f} V"
    )

    plt.axvline(
        vih,
        linestyle="--",
        label=f"VIH = {vih:.3f} V"
    )

    plt.axvline(
        vm,
        linestyle=":",
        label=f"VM = {vm:.3f} V"
    )

    plt.xlabel("Input Voltage A (V)")
    plt.ylabel("Output Voltage (V)")

    plt.title(
        "CMOS NAND Gate Voltage Transfer Characteristic"
    )

    plt.grid(True)
    plt.legend()

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=300
    )

    plt.close()

    return output_path


# ============================================================
# CSV Report
# ============================================================

def generate_csv_report(
    results,
    output_directory
):
    """
    Save characterization results as CSV.
    """

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    output_path = os.path.join(
        output_directory,
        "cmos_nand_characterization_summary.csv"
    )

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            ["Parameter", "Value", "Unit"]
        )

        writer.writerow(
            ["VOH", results["VOH"], "V"]
        )

        writer.writerow(
            ["VOL", results["VOL"], "V"]
        )

        writer.writerow(
            ["VM", results["VM"], "V"]
        )

        writer.writerow(
            ["VIL", results["VIL"], "V"]
        )

        writer.writerow(
            ["VIH", results["VIH"], "V"]
        )

        writer.writerow(
            ["NML", results["NML"], "V"]
        )

        writer.writerow(
            ["NMH", results["NMH"], "V"]
        )

        writer.writerow(
            ["Maximum Gain", results["Maximum Gain"], "V/V"]
        )

        writer.writerow(
            ["TPHL", results["TPHL"], "s"]
        )

        writer.writerow(
            ["TPLH", results["TPLH"], "s"]
        )

        writer.writerow(
            ["Rise Time", results["Rise Time"], "s"]
        )

        writer.writerow(
            ["Fall Time", results["Fall Time"], "s"]
        )

        writer.writerow(
            ["Average Delay", results["Average Delay"], "s"]
        )

        writer.writerow(
            ["Average Current",
             results["Average Current"], "A"]
        )

        writer.writerow(
            ["Average Power",
             results["Average Power"], "W"]
        )

        writer.writerow(
            ["Peak Current",
             results["Peak Current"], "A"]
        )

        writer.writerow(
            ["Minimum Current",
             results["Minimum Current"], "A"]
        )

        writer.writerow(
            ["Energy / Pattern",
             results["Energy / Pattern"], "J"]
        )



    return output_path


# ============================================================
# Markdown Report
# ============================================================

def generate_markdown_report(
    results,
    output_directory
):
    """
    Save characterization results as Markdown.
    """

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    output_path = os.path.join(
        output_directory,
        "cmos_nand_characterization.md"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "# CMOS NAND Gate Characterization\n\n"
        )

        file.write(
            "## DC Characterization\n\n"
        )

        file.write(
            "| Parameter | Value |\n"
        )

        file.write(
            "|---|---:|\n"
        )

        file.write(
            f"| VOH | {results['VOH']:.4f} V |\n"
        )

        file.write(
            f"| VOL | {results['VOL']:.4f} V |\n"
        )

        file.write(
            f"| VM | {results['VM']:.4f} V |\n"
        )

        file.write(
            f"| VIL | {results['VIL']:.4f} V |\n"
        )

        file.write(
            f"| VIH | {results['VIH']:.4f} V |\n"
        )

        file.write(
            f"| NML | {results['NML']:.4f} V |\n"
        )

        file.write(
            f"| NMH | {results['NMH']:.4f} V |\n"
        )

        file.write(
            f"| Maximum Gain | "
            f"{results['Maximum Gain']:.2f} V/V |\n"
        )

        file.write(
            "\n## Characterization Condition\n\n"
        )

        file.write(
            "Input A was swept from 0 V to 5 V while "
            "Input B was held at 5 V.\n"
        )

        file.write(
            "\n## Timing Characterization\n\n"
        )

        file.write(
            f"- **TPHL:** "
            f"{results['TPHL'] * 1e9:.3f} ns\n"
        )

        file.write(
            f"- **TPLH:** "
            f"{results['TPLH'] * 1e9:.3f} ns\n"
        )

        file.write(
            f"- **Rise Time:** "
            f"{results['Rise Time'] * 1e12:.3f} ps\n"
        )

        file.write(
            f"- **Fall Time:** "
            f"{results['Fall Time'] * 1e12:.3f} ps\n"
        )

        file.write(
            f"- **Average Delay:** "
            f"{results['Average Delay'] * 1e9:.3f} ns\n"
        )

        file.write(
            "\n## Power Characterization\n\n"
        )

        file.write(
            f"- **Average Current:** "
            f"{results['Average Current'] * 1e6:.3f} µA\n"
        )

        file.write(
            f"- **Average Power:** "
            f"{results['Average Power'] * 1e6:.3f} µW\n"
        )

        file.write(
            f"- **Peak Current:** "
            f"{results['Peak Current'] * 1e6:.3f} µA\n"
        )

        file.write(
            f"- **Minimum Current:** "
            f"{results['Minimum Current'] * 1e6:.3f} µA\n"
        )

        file.write(
            f"- **Energy / Pattern:** "
            f"{results['Energy / Pattern'] * 1e15:.3f} fJ\n"
        )

    return output_path


# ============================================================
# Display Results
# ============================================================

def print_results(
    results,
    selected_file
):
    """
    Print characterization results.
    """

    print()

    print("=" * 60)
    print(" CMOS NAND GATE CHARACTERIZATION")
    print("=" * 60)

    print(
        f"Selected File : {selected_file}"
    )

    print("-" * 60)

    print(
        f"VOH : {results['VOH']:.4f} V"
    )

    print(
        f"VOL : {results['VOL']:.4f} V"
    )

    print(
        f"VM  : {results['VM']:.4f} V"
    )

    print()

    print(
        f"VIL : {results['VIL']:.4f} V"
    )

    print(
        f"VIH : {results['VIH']:.4f} V"
    )

    print()

    print(
        f"NML : {results['NML']:.4f} V"
    )

    print(
        f"NMH : {results['NMH']:.4f} V"
    )

    print()

    print(
        f"Maximum Gain : "
        f"{results['Maximum Gain']:.2f}"
    )

    print()

    print("-" * 60)
    print(" TIMING CHARACTERIZATION")
    print("-" * 60)

    print(
        f"TPHL            : "
        f"{results['TPHL'] * 1e9:.2f} ns"
    )

    print(
        f"TPLH            : "
        f"{results['TPLH'] * 1e9:.2f} ns"
    )

    print(
        f"Rise Time       : "
        f"{results['Rise Time'] * 1e12:.2f} ps"
    )

    print(
        f"Fall Time       : "
        f"{results['Fall Time'] * 1e12:.2f} ps"
    )

    print(
        f"Average Delay   : "
        f"{results['Average Delay'] * 1e9:.2f} ns"
    )

    print()

    print("-" * 60)
    print(" POWER CHARACTERIZATION")
    print("-" * 60)

    print(
        f"Average Current      : "
        f"{results['Average Current'] * 1e6:.3f} µA"
    )

    print(
        f"Average Power        : "
        f"{results['Average Power'] * 1e6:.3f} µW"
    )

    print(
        f"Peak Current         : "
        f"{results['Peak Current'] * 1e6:.3f} µA"
    )

    print(
        f"Minimum Current      : "
        f"{results['Minimum Current'] * 1e6:.3f} µA"
    )

    print(
        f"Energy / Pattern     : "
        f"{results['Energy / Pattern'] * 1e15:.3f} fJ"
    )


# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Select input file
    # --------------------------------------------------------

    selected_file = select_file()

    # --------------------------------------------------------
    # Load LTspice data
    # --------------------------------------------------------

    vin, vout = load_data(
        selected_file
    )

    # --------------------------------------------------------
    # Static characterization
    # --------------------------------------------------------

    results = calculate_static_parameters(
        vin,
        vout
    )

    # --------------------------------------------------------
    # Gain
    # --------------------------------------------------------

    gain = calculate_gain(
        vin,
        vout
    )

    max_gain = calculate_max_gain(
        gain
    )

    # --------------------------------------------------------
    # VIL / VIH
    # --------------------------------------------------------

    vil, vih = calculate_vil_vih(
        vin,
        gain
    )

    # --------------------------------------------------------
    # Noise margins
    # --------------------------------------------------------

    nml, nmh = calculate_noise_margin(
        results["VOH"],
        results["VOL"],
        vil,
        vih
    )

        # --------------------------------------------------------
    # LTspice timing and power log
    # --------------------------------------------------------

    timing_log = select_timing_log()

    timing_results = load_timing_results(
        timing_log
    )

    # --------------------------------------------------------
    # Dynamic characterization
    # --------------------------------------------------------

    dynamic_results = calculate_dynamic_parameters(
        timing_results
    )

    # --------------------------------------------------------
    # Store all results
    # --------------------------------------------------------

    results["TPHL"] = dynamic_results["TPHL"]
    results["TPLH"] = dynamic_results["TPLH"]
    results["Rise Time"] = dynamic_results["Rise Time"]
    results["Fall Time"] = dynamic_results["Fall Time"]
    results["Average Delay"] = dynamic_results["Average Delay"]

    results["Average Current"] = dynamic_results[
        "Average Current"
    ]

    results["Peak Current"] = dynamic_results[
        "Peak Current"
    ]

    results["Minimum Current"] = dynamic_results[
        "Minimum Current"
    ]

    results["Average Power"] = dynamic_results[
        "Average Power"
    ]

    results["Energy / Pattern"] = dynamic_results[
        "Energy / Pattern"
    ]


    # --------------------------------------------------------
    # Store results
    # --------------------------------------------------------

    results["Maximum Gain"] = max_gain
    results["VIL"] = vil
    results["VIH"] = vih
    results["NML"] = nml
    results["NMH"] = nmh

    # --------------------------------------------------------
    # Project root
    # --------------------------------------------------------

    project_root = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    # --------------------------------------------------------
    # Output directories
    # --------------------------------------------------------

    image_directory = os.path.join(
        project_root,
        "images"
    )

    calculation_directory = os.path.join(
        project_root,
        "calculations"
    )

    simulation_directory = os.path.join(
        project_root,
        "simulations"
    )

    # --------------------------------------------------------
    # Generate outputs
    # --------------------------------------------------------

    plot_path = generate_plot(
        vin,
        vout,
        vil,
        vih,
        results["VM"],
        image_directory
    )

    csv_path = generate_csv_report(
        results,
        simulation_directory
    )

    markdown_path = generate_markdown_report(
        results,
        calculation_directory
    )

    # --------------------------------------------------------
    # Display results
    # --------------------------------------------------------

    print_results(
        results,
        selected_file
    )

    print()

    print(
        f"VTC Plot saved to:\n{plot_path}"
    )

    print(
        f"CSV Summary saved to:\n{csv_path}"
    )

    print(
        f"Markdown Report saved to:\n{markdown_path}"
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()