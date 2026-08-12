import csv
import os
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog


# ============================================================
# CONFIGURATION
# ============================================================

VDD = 5.0

V50 = VDD / 2.0
V10 = 0.10 * VDD
V90 = 0.90 * VDD

MAX_DELAY_WINDOW = 2e-9


# ============================================================
# FILE SELECTION
# ============================================================

def select_file(title):

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        title=title,
        filetypes=[
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
    )

    root.destroy()

    if not path:
        raise FileNotFoundError(
            f"No file selected for: {title}"
        )

    return path


# ============================================================
# PROJECT ROOT
# ============================================================

def find_project_root():

    current = os.path.abspath(
        os.path.dirname(__file__)
    )

    while True:

        if (
            os.path.isdir(
                os.path.join(
                    current,
                    "simulations"
                )
            )
            and
            os.path.isdir(
                os.path.join(
                    current,
                    "calculations"
                )
            )
        ):
            return current

        parent = os.path.dirname(current)

        if parent == current:
            break

        current = parent

    raise RuntimeError(
        "Could not locate VLSI project root."
    )


# ============================================================
# READ NUMERIC TABLE
# ============================================================

def read_table(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        lines = file.readlines()

    header_index = None

    for i, line in enumerate(lines):

        normalized = line.lower()

        if (
            "time" in normalized
            and "v(a)" in normalized
            and "v(b)" in normalized
            and "v(out)" in normalized
            and "i(v1)" in normalized
        ):
            header_index = i
            break

    if header_index is None:

        raise ValueError(
            "Could not find expected header:\n"
            "time V(a) V(b) V(out) I(V1)"
        )

    # LTspice exports columns separated by tabs,
    # but whitespace splitting is more robust.
    header = lines[header_index].split()

    header = [
        item.lower()
        for item in header
    ]

    time_index = header.index("time")
    a_index = header.index("v(a)")
    b_index = header.index("v(b)")
    out_index = header.index("v(out)")
    current_index = header.index("i(v1)")

    time = []
    a = []
    b = []
    out = []
    current = []

    for line in lines[header_index + 1:]:

        parts = line.split()

        if len(parts) <= max(
            time_index,
            a_index,
            b_index,
            out_index,
            current_index
        ):
            continue

        try:

            time.append(
                float(parts[time_index])
            )

            a.append(
                float(parts[a_index])
            )

            b.append(
                float(parts[b_index])
            )

            out.append(
                float(parts[out_index])
            )

            current.append(
                float(parts[current_index])
            )

        except ValueError:
            continue

    if len(time) < 20:

        raise ValueError(
            "Insufficient transient data."
        )

    time = np.asarray(time)
    a = np.asarray(a)
    b = np.asarray(b)
    out = np.asarray(out)
    current = np.asarray(current)

    order = np.argsort(time)

    return (
        time[order],
        a[order],
        b[order],
        out[order],
        current[order]
    )


# ============================================================
# LOAD VTC
# ============================================================

def load_vtc_data(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        lines = file.readlines()

    header_index = None

    for i, line in enumerate(lines):

        text = line.lower()

        if "v2" in text and "v(out)" in text:

            header_index = i
            break

    if header_index is None:

        raise ValueError(
            "Could not find VTC header."
        )

    header = lines[header_index].split()

    header = [
        item.lower()
        for item in header
    ]

    vin_index = header.index("v2")
    vout_index = header.index("v(out)")

    vin = []
    vout = []

    for line in lines[header_index + 1:]:

        parts = line.split()

        if len(parts) <= max(
            vin_index,
            vout_index
        ):
            continue

        try:

            vin.append(
                float(parts[vin_index])
            )

            vout.append(
                float(parts[vout_index])
            )

        except ValueError:
            continue

    if len(vin) < 10:

        raise ValueError(
            "Insufficient VTC data."
        )

    vin = np.asarray(vin)
    vout = np.asarray(vout)

    order = np.argsort(vin)

    return (
        vin[order],
        vout[order]
    )


# ============================================================
# STATIC CHARACTERIZATION
# ============================================================

def characterize_vtc(vin, vout):

    voh = float(
        np.max(vout)
    )

    vol = float(
        np.min(vout)
    )

    vm_index = np.argmin(
        np.abs(vin - vout)
    )

    vm = float(
        vin[vm_index]
    )

    gain = np.gradient(
        vout,
        vin
    )

    max_gain = float(
        np.min(gain)
    )

    gain_abs = np.abs(gain)

    crossings = []

    for i in range(
        len(gain_abs) - 1
    ):

        g1 = gain_abs[i]
        g2 = gain_abs[i + 1]

        if (
            (g1 - 1)
            *
            (g2 - 1)
            <= 0
        ):

            if g2 != g1:

                x = vin[i] + (
                    (1 - g1)
                    *
                    (vin[i + 1] - vin[i])
                    /
                    (g2 - g1)
                )

            else:

                x = vin[i]

            crossings.append(x)

    if len(crossings) >= 2:

        vil = float(crossings[0])
        vih = float(crossings[-1])

    else:

        vil = np.nan
        vih = np.nan

    nml = (
        vil - vol
        if not np.isnan(vil)
        else np.nan
    )

    nmh = (
        voh - vih
        if not np.isnan(vih)
        else np.nan
    )

    return {

        "VOH": voh,
        "VOL": vol,
        "VM": vm,
        "VIL": vil,
        "VIH": vih,
        "NML": nml,
        "NMH": nmh,
        "Maximum Gain": max_gain
    }


# ============================================================
# CROSSING INTERPOLATION
# ============================================================

def crossing_time(
    t1,
    y1,
    t2,
    y2,
    threshold
):

    if y2 == y1:
        return t1

    return (
        t1
        +
        (
            (threshold - y1)
            *
            (t2 - t1)
            /
            (y2 - y1)
        )
    )


# ============================================================
# FIND ALL CROSSINGS
# ============================================================

def find_crossings(
    time,
    waveform,
    threshold
):

    rising = []
    falling = []

    for i in range(
        len(waveform) - 1
    ):

        y1 = waveform[i]
        y2 = waveform[i + 1]

        if y1 < threshold <= y2:

            rising.append(
                crossing_time(
                    time[i],
                    y1,
                    time[i + 1],
                    y2,
                    threshold
                )
            )

        elif y1 > threshold >= y2:

            falling.append(
                crossing_time(
                    time[i],
                    y1,
                    time[i + 1],
                    y2,
                    threshold
                )
            )

    return rising, falling


# ============================================================
# RISE / FALL TIME
# ============================================================

def calculate_rise_fall_time(
    time,
    out
):

    rise_10, _ = find_crossings(
        time,
        out,
        V10
    )

    rise_90, _ = find_crossings(
        time,
        out,
        V90
    )

    _, fall_90 = find_crossings(
        time,
        out,
        V90
    )

    _, fall_10 = find_crossings(
        time,
        out,
        V10
    )

    rise_times = []

    for t10 in rise_10:

        candidates = [
            t90
            for t90 in rise_90
            if t90 > t10
        ]

        if candidates:

            rise_times.append(
                min(candidates) - t10
            )

    fall_times = []

    for t90 in fall_90:

        candidates = [
            t10
            for t10 in fall_10
            if t10 > t90
        ]

        if candidates:

            fall_times.append(
                min(candidates) - t90
            )

    rise_time = (
        float(np.mean(rise_times))
        if rise_times
        else np.nan
    )

    fall_time = (
        float(np.mean(fall_times))
        if fall_times
        else np.nan
    )

    return (
        rise_time,
        fall_time
    )


# ============================================================
# STATE-AWARE NOR PROPAGATION DELAY
# ============================================================

def find_valid_delay(
    time,
    input_waveform,
    other_waveform,
    output_waveform,
    input_direction,
    output_direction
):
    """
    Extract propagation delay for one NOR input.

    NOR condition:

        input rising + other input LOW
            -> output falling

        input falling + other input LOW
            -> output rising

    Propagation delay is measured using the 50% VDD
    crossing of the input and output waveforms.

    Note:
    A negative delay can occur with finite input slew when
    the output crosses 50% VDD before the input reaches its
    own 50% VDD crossing.
    """

    # --------------------------------------------------------
    # Find 50% crossings
    # --------------------------------------------------------

    input_rise, input_fall = find_crossings(
        time,
        input_waveform,
        V50
    )

    output_rise, output_fall = find_crossings(
        time,
        output_waveform,
        V50
    )

    # --------------------------------------------------------
    # Select required input/output transitions
    # --------------------------------------------------------

    if input_direction == "rise":
        input_events = input_rise
    else:
        input_events = input_fall

    if output_direction == "rise":
        output_events = output_rise
    else:
        output_events = output_fall

    delays = []

    # --------------------------------------------------------
    # Match output transition to nearest input transition
    # --------------------------------------------------------

    for t_output in output_events:

        candidates = [
            t_input
            for t_input in input_events
            if abs(t_output - t_input)
            <= MAX_DELAY_WINDOW
        ]

        if not candidates:
            continue

        # Select the closest input transition
        t_input = min(
            candidates,
            key=lambda x: abs(t_output - x)
        )

        # ----------------------------------------------------
        # Find waveform index near input transition
        # ----------------------------------------------------

        index = np.searchsorted(
            time,
            t_input
        )

        index = max(
            0,
            min(
                index,
                len(time) - 1
            )
        )

        # ----------------------------------------------------
        # Check the OTHER NOR input
        #
        # For a valid propagation event, the other input
        # must be LOW.
        # ----------------------------------------------------

        start = max(
            0,
            index - 3
        )

        end = min(
            len(time),
            index + 4
        )

        other_values = other_waveform[
            start:end
        ]

        if np.max(other_values) >= V50:
            continue

        # ----------------------------------------------------
        # Calculate propagation delay
        # ----------------------------------------------------

        delay = (
            t_output
            -
            t_input
        )

        # ----------------------------------------------------
        # Keep negative values.
        #
        # Negative delay can occur because the input has a
        # finite slew rate and the output may cross 50% VDD
        # before the input itself reaches 50% VDD.
        # ----------------------------------------------------

        delays.append(
            delay
        )

    # --------------------------------------------------------
    # Return average of valid events
    # --------------------------------------------------------

    if delays:

        return float(
            np.mean(delays)
        )

    return np.nan
# ============================================================
# COMPLETE TIMING CHARACTERIZATION
# ============================================================

def characterize_timing(
    time,
    a,
    b,
    out
):

    # NOR:
    #
    # A rising + B LOW  -> OUT falling
    # A falling + B LOW -> OUT rising
    #
    # B rising + A LOW  -> OUT falling
    # B falling + A LOW -> OUT rising

    tphl_a = find_valid_delay(
        time,
        a,
        b,
        out,
        "rise",
        "fall"
    )

    tplh_a = find_valid_delay(
        time,
        a,
        b,
        out,
        "fall",
        "rise"
    )

    tphl_b = find_valid_delay(
        time,
        b,
        a,
        out,
        "rise",
        "fall"
    )

    tplh_b = find_valid_delay(
        time,
        b,
        a,
        out,
        "fall",
        "rise"
    )

    tphl_values = [
        x
        for x in [
            tphl_a,
            tphl_b
        ]
        if not np.isnan(x)
    ]

    tplh_values = [
        x
        for x in [
            tplh_a,
            tplh_b
        ]
        if not np.isnan(x)
    ]

    all_delays = (
        tphl_values
        +
        tplh_values
    )

    return {

        "TPHL_A": tphl_a,
        "TPLH_A": tplh_a,
        "TPHL_B": tphl_b,
        "TPLH_B": tplh_b,

        "Worst-case TPHL":
            max(tphl_values)
            if tphl_values
            else np.nan,

        "Worst-case TPLH":
            max(tplh_values)
            if tplh_values
            else np.nan,

        "Average Delay":
            float(np.mean(all_delays))
            if all_delays
            else np.nan
    }


# ============================================================
# POWER CHARACTERIZATION
# ============================================================

def characterize_power(
    time,
    current
):

    # LTspice I(V1) is current ENTERING the positive
    # terminal of the voltage source.
    #
    # Therefore supply current is:
    #
    # Isupply = -I(V1)
    #
    supply_current = -current

    # Instantaneous supply power
    power = (
        VDD
        *
        supply_current
    )

    # Numerical integration
    total_charge = np.trapezoid(
        supply_current,
        time
    )

    total_energy = np.trapezoid(
        power,
        time
    )

    simulation_time = (
        time[-1] - time[0]
    )

    if simulation_time <= 0:

        raise ValueError(
            "Invalid simulation time."
        )

    average_current = (
        total_charge
        /
        simulation_time
    )

    average_power = (
        total_energy
        /
        simulation_time
    )

    peak_current = float(
        np.max(supply_current)
    )

    minimum_current = float(
        np.min(supply_current)
    )

    return {

        "Average Current":
            float(average_current),

        "Peak Current":
            peak_current,

        "Minimum Current":
            minimum_current,

        "Average Power":
            float(average_power),

        "Energy / Simulation":
            float(total_energy)
    }


# ============================================================
# VTC PLOT
# ============================================================

def generate_vtc_plot(
    vin,
    vout,
    output_file
):

    plt.figure(
        figsize=(8, 5)
    )

    plt.plot(
        vin,
        vout,
        linewidth=2
    )

    plt.xlabel(
        "Input Voltage A (V)"
    )

    plt.ylabel(
        "Output Voltage (V)"
    )

    plt.title(
        "2-Input CMOS NOR Voltage Transfer Characteristic"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        output_file,
        dpi=300
    )

    plt.close()


# ============================================================
# TRANSIENT PLOT
# ============================================================

def generate_transient_plot(
    time,
    a,
    b,
    out,
    current,
    output_file
):

    plt.figure(
        figsize=(10, 6)
    )

    plt.plot(
        time * 1e9,
        a,
        label="A"
    )

    plt.plot(
        time * 1e9,
        b,
        label="B"
    )

    plt.plot(
        time * 1e9,
        out,
        label="OUT",
        linewidth=2
    )

    plt.plot(
        time * 1e9,
        current * 1e6,
        label="I(V1) [µA]",
        alpha=0.7
    )

    plt.xlabel(
        "Time (ns)"
    )

    plt.ylabel(
        "Voltage / Current"
    )

    plt.title(
        "CMOS NOR Transient and Supply Current"
    )

    plt.legend()

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        output_file,
        dpi=300
    )

    plt.close()


# ============================================================
# CSV REPORT
# ============================================================

def generate_csv_report(
    results,
    output_file
):

    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True
    )

    units = {

        "VOH": "V",
        "VOL": "V",
        "VM": "V",
        "VIL": "V",
        "VIH": "V",
        "NML": "V",
        "NMH": "V",
        "Maximum Gain": "V/V",

        "TPHL_A": "s",
        "TPLH_A": "s",
        "TPHL_B": "s",
        "TPLH_B": "s",
        "Worst-case TPHL": "s",
        "Worst-case TPLH": "s",
        "Average Delay": "s",

        "Rise Time": "s",
        "Fall Time": "s",

        "Average Current": "A",
        "Peak Current": "A",
        "Minimum Current": "A",

        "Average Power": "W",
        "Energy / Simulation": "J"
    }

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Parameter",
            "Value",
            "Unit"
        ])

        for key, value in results.items():

            writer.writerow([
                key,
                value,
                units.get(
                    key,
                    ""
                )
            ])


# ============================================================
# MARKDOWN REPORT
# ============================================================

def fmt(
    value,
    multiplier=1,
    unit=""
):

    if value is None:
        return "N/A"

    if np.isnan(value):
        return "N/A"

    return (
        f"{value * multiplier:.3f} {unit}"
    )


def generate_markdown_report(
    results,
    output_file
):

    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "# CMOS NOR Gate Characterization\n\n"
        )

        file.write(
            "## Static Characterization\n\n"
        )

        file.write(
            f"- VOH: {results['VOH']:.4f} V\n"
        )

        file.write(
            f"- VOL: {results['VOL']:.4f} V\n"
        )

        file.write(
            f"- VM: {results['VM']:.4f} V\n"
        )

        file.write(
            f"- VIL: {results['VIL']:.4f} V\n"
        )

        file.write(
            f"- VIH: {results['VIH']:.4f} V\n"
        )

        file.write(
            f"- NML: {results['NML']:.4f} V\n"
        )

        file.write(
            f"- NMH: {results['NMH']:.4f} V\n"
        )

        file.write(
            f"- Maximum Gain: "
            f"{results['Maximum Gain']:.4f} V/V\n"
        )

        file.write(
            "\n## Timing Characterization\n\n"
        )

        for key in [
            "TPHL_A",
            "TPLH_A",
            "TPHL_B",
            "TPLH_B",
            "Worst-case TPHL",
            "Worst-case TPLH",
            "Average Delay"
        ]:

            file.write(
                f"- {key}: "
                f"{fmt(results[key], 1e12, 'ps')}\n"
            )

        file.write(
            f"- Rise Time: "
            f"{fmt(results['Rise Time'], 1e12, 'ps')}\n"
        )

        file.write(
            f"- Fall Time: "
            f"{fmt(results['Fall Time'], 1e12, 'ps')}\n"
        )

        file.write(
            "\n## Power Characterization\n\n"
        )

        file.write(
            f"- Average Current: "
            f"{fmt(results['Average Current'], 1e6, 'µA')}\n"
        )

        file.write(
            f"- Peak Current: "
            f"{fmt(results['Peak Current'], 1e6, 'µA')}\n"
        )

        file.write(
            f"- Minimum Current: "
            f"{fmt(results['Minimum Current'], 1e6, 'µA')}\n"
        )

        file.write(
            f"- Average Power: "
            f"{fmt(results['Average Power'], 1e6, 'µW')}\n"
        )

        file.write(
            f"- Energy / Simulation: "
            f"{fmt(results['Energy / Simulation'], 1e15, 'fJ')}\n"
        )


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def print_results(results):

    print()
    print("=" * 60)
    print(" CMOS NOR GATE CHARACTERIZATION")
    print("=" * 60)

    print()
    print("STATIC CHARACTERIZATION")
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

    print(
        f"VIL : {results['VIL']:.4f} V"
    )

    print(
        f"VIH : {results['VIH']:.4f} V"
    )

    print(
        f"NML : {results['NML']:.4f} V"
    )

    print(
        f"NMH : {results['NMH']:.4f} V"
    )

    print(
        f"Maximum Gain : "
        f"{results['Maximum Gain']:.2f}"
    )

    print()
    print("TIMING CHARACTERIZATION")
    print("-" * 60)

    for key in [
        "TPHL_A",
        "TPLH_A",
        "TPHL_B",
        "TPLH_B",
        "Worst-case TPHL",
        "Worst-case TPLH",
        "Average Delay"
    ]:

        value = results[key]

        if np.isnan(value):

            text = "N/A"

        else:

            text = (
                f"{value * 1e12:.3f} ps"
            )

        print(
            f"{key:<20}: {text}"
        )

    print(
        f"{'Rise Time':<20}: "
        f"{results['Rise Time'] * 1e12:.3f} ps"
    )

    print(
        f"{'Fall Time':<20}: "
        f"{results['Fall Time'] * 1e12:.3f} ps"
    )

    print()
    print("POWER CHARACTERIZATION")
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
        f"Energy / Simulation  : "
        f"{results['Energy / Simulation'] * 1e15:.3f} fJ"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    project_root = find_project_root()

    # --------------------------------------------------------
    # VTC
    # --------------------------------------------------------

    vtc_file = select_file(
        "Select NOR VTC Data File"
    )

    print()
    print(
        f"Selected VTC File : {vtc_file}"
    )

    vin, vout = load_vtc_data(
        vtc_file
    )

    static_results = characterize_vtc(
        vin,
        vout
    )

    # --------------------------------------------------------
    # TRANSIENT
    # --------------------------------------------------------

    transient_file = select_file(
        "Select NOR Transient Data File"
    )

    print(
        f"Selected Transient File : "
        f"{transient_file}"
    )

    (
        time,
        a,
        b,
        out,
        current
    ) = read_table(
        transient_file
    )

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------

    timing_results = characterize_timing(
        time,
        a,
        b,
        out
    )

    rise_time, fall_time = (
        calculate_rise_fall_time(
            time,
            out
        )
    )

    # --------------------------------------------------------
    # Power
    # --------------------------------------------------------

    power_results = characterize_power(
        time,
        current
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    results = {

        **static_results,

        **timing_results,

        "Rise Time":
            rise_time,

        "Fall Time":
            fall_time,

        **power_results
    }

    # --------------------------------------------------------
    # Directories
    # --------------------------------------------------------

    images_dir = os.path.join(
        project_root,
        "images",
        "cmos_nor"
    )

    simulations_dir = os.path.join(
        project_root,
        "simulations",
        "cmos_nor"
    )

    calculations_dir = os.path.join(
        project_root,
        "calculations",
        "cmos_nor"
    )

    os.makedirs(
        images_dir,
        exist_ok=True
    )

    os.makedirs(
        simulations_dir,
        exist_ok=True
    )

    os.makedirs(
        calculations_dir,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Output files
    # --------------------------------------------------------

    vtc_plot = os.path.join(
        images_dir,
        "cmos_nor_vtc_plot.png"
    )

    transient_plot = os.path.join(
        images_dir,
        "cmos_nor_transient_power_plot.png"
    )

    csv_file = os.path.join(
        simulations_dir,
        "cmos_nor_characterization_summary.csv"
    )

    markdown_file = os.path.join(
        calculations_dir,
        "cmos_nor_characterization.md"
    )

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    generate_vtc_plot(
        vin,
        vout,
        vtc_plot
    )

    generate_transient_plot(
        time,
        a,
        b,
        out,
        current,
        transient_plot
    )

    generate_csv_report(
        results,
        csv_file
    )

    generate_markdown_report(
        results,
        markdown_file
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print_results(
        results
    )

    print()
    print(
        "VTC Plot saved to:"
    )
    print(vtc_plot)

    print()
    print(
        "Transient/Power Plot saved to:"
    )
    print(transient_plot)

    print()
    print(
        "CSV Summary saved to:"
    )
    print(csv_file)

    print()
    print(
        "Markdown Report saved to:"
    )
    print(markdown_file)


if __name__ == "__main__":
    main()