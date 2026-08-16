"""
CMOS XOR CHARACTERIZATION
Project 01 - CMOS Logic Design

Datasets:
1. Transient: time, V(a), V(b), V(out), I(Vdd)
2. VTC: V1, V(out), stepped Bval=0 and Bval=5
3. DC: A/B operating points with I(Vdd)

Outputs:
- TPHL / TPLH
- Average / worst delay
- Rise / fall time
- Dynamic current / power
- Dynamic energy
- Static current / power for all 4 states
- VTC parameters
- VOH / VOL / VM
- VIL / VIH / NML / NMH
- Plots
- CSV / Markdown / TXT reports
"""

from pathlib import Path
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import csv
import re

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

VDD = 5.0
V50 = VDD / 2
V10 = 0.1 * VDD
V90 = 0.9 * VDD

MAX_DELAY = 5e-9
SIMULTANEOUS_WINDOW = 0.25e-9


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

IMG = ROOT / "images" / "cmos_xor"
SIM = ROOT / "simulations" / "cmos_xor"
CALC = ROOT / "calculations" / "cmos_xor"
REPORT = ROOT / "reports"

for folder in (IMG, SIM, CALC, REPORT):
    folder.mkdir(parents=True, exist_ok=True)


# ============================================================
# FILE SELECTION
# ============================================================

def select_file(title):

    root = Tk()
    root.withdraw()

    path = askopenfilename(
        title=title,
        filetypes=[
            ("Text files", "*.txt"),
            ("CSV files", "*.csv"),
            ("All files", "*.*")
        ]
    )

    root.destroy()

    if not path:
        raise SystemExit("No file selected.")

    return Path(path)


# ============================================================
# CROSSING DETECTION
# ============================================================

def crossings(t, y, level):

    rise = []
    fall = []

    for i in range(len(y) - 1):

        dy = y[i + 1] - y[i]

        if dy == 0:
            continue

        if y[i] < level <= y[i + 1]:

            tr = t[i] + (
                (level - y[i]) / dy
            ) * (t[i + 1] - t[i])

            if not rise or tr - rise[-1] > 1e-12:
                rise.append(tr)

        elif y[i] > level >= y[i + 1]:

            tf = t[i] + (
                (level - y[i]) / dy
            ) * (t[i + 1] - t[i])

            if not fall or tf - fall[-1] > 1e-12:
                fall.append(tf)

    return np.asarray(rise), np.asarray(fall)


# ============================================================
# TRANSIENT LOADING
# ============================================================

def load_transient(path):

    required = {
        "time",
        "v(a)",
        "v(b)",
        "v(out)",
        "i(vdd)"
    }

    with open(
        path,
        encoding="utf-8",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    header = None
    header_index = None

    for i, line in enumerate(lines):

        cols = line.strip().lower().split()

        if required.issubset(cols):

            header = cols
            header_index = i
            break

    if header is None:

        raise ValueError(
            "Could not find transient header.\n"
            "Expected: time V(a) V(b) V(out) I(Vdd)"
        )

    idx = {
        name: header.index(name)
        for name in required
    }

    data = []

    for line in lines[header_index + 1:]:

        text = line.strip()

        if not text:
            continue

        if text.lower().startswith(
            (
                "step information:",
                "measurement:",
                "warning:"
            )
        ):
            continue

        parts = text.split()

        try:

            data.append([
                float(parts[idx["time"]]),
                float(parts[idx["v(a)"]]),
                float(parts[idx["v(b)"]]),
                float(parts[idx["v(out)"]]),
                float(parts[idx["i(vdd)"]])
            ])

        except (ValueError, IndexError):
            continue

    if not data:
        raise ValueError(
            "No transient numerical data found."
        )

    data = np.asarray(data)

    # Sort by time
    data = data[
        np.argsort(data[:, 0])
    ]

    # Remove duplicate timestamps
    _, unique = np.unique(
        data[:, 0],
        return_index=True
    )

    data = data[
        np.sort(unique)
    ]

    print(
        f"\nDetected transient samples: "
        f"{len(data)}"
    )

    return data.T


# ============================================================
# STATIC DC DATA LOADING
# ============================================================

def load_static_dc(path):

    """
    Read the separate DC operating-point dataset.

    Expected LTspice structure:

        Step Information: A=0 B=0
        ...
        I(Vdd)

    Four states are required:

        00
        01
        10
        11
    """

    with open(
        path,
        encoding="utf-8",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    states = {}
    current_state = None
    header = None

    for line in lines:

        text = line.strip()
        lower = text.lower()

        # --------------------------------------------
        # Detect operating point
        # --------------------------------------------

        if lower.startswith(
            "step information:"
        ):

            match_a = re.search(
                r"a\s*=\s*([01](?:\.\d+)?)",
                lower
            )

            match_b = re.search(
                r"b\s*=\s*([01](?:\.\d+)?)",
                lower
            )

            if match_a and match_b:

                a = int(
                    float(match_a.group(1)) >= 0.5
                )

                b = int(
                    float(match_b.group(1)) >= 0.5
                )

                current_state = f"{a}{b}"

                states.setdefault(
                    current_state,
                    {}
                )

            else:
                current_state = None

            header = None
            continue

        if not text:
            continue

        cols = text.lower().split()

        # --------------------------------------------
        # Detect data header
        # --------------------------------------------

        if "i(vdd)" in cols:

            header = cols
            continue

        if (
            current_state is None
            or header is None
        ):
            continue

        try:

            current = float(
                cols[header.index("i(vdd)")]
            )

        except (ValueError, IndexError):

            continue

        states[
            current_state
        ]["current"] = current

    # --------------------------------------------
    # Validate all four states
    # --------------------------------------------

    for name in (
        "00",
        "01",
        "10",
        "11"
    ):

        if (
            name not in states
            or
            "current" not in states[name]
        ):

            raise ValueError(
                f"Missing DC operating point: "
                f"state {name}"
            )

    return states


# ============================================================
# LOGIC STATE
# ============================================================

def state(value):

    return int(
        value >= V50
    )


def state_before(t, y, event):

    i = np.searchsorted(
        t,
        event
    ) - 1

    i = max(
        0,
        min(
            i,
            len(y) - 1
        )
    )

    return state(y[i])


def state_after(t, y, event):

    i = np.searchsorted(
        t,
        event
    ) + 1

    i = max(
        0,
        min(
            i,
            len(y) - 1
        )
    )

    return state(y[i])


# ============================================================
# TIMING CHARACTERIZATION
# ============================================================

def timing_analysis(t, a, b, out):

    ar, af = crossings(
        t,
        a,
        V50
    )

    br, bf = crossings(
        t,
        b,
        V50
    )

    orise, ofall = crossings(
        t,
        out,
        V50
    )

    events = []

    for x, name, direction in [
        (ar, "A", "rise"),
        (af, "A", "fall"),
        (br, "B", "rise"),
        (bf, "B", "fall")
    ]:

        for te in x:

            events.append({
                "time": te,
                "input": name,
                "direction": direction
            })

    events.sort(
        key=lambda e: e["time"]
    )

    # --------------------------------------------
    # Group simultaneous input changes
    # --------------------------------------------

    groups = []

    for event in events:

        if (
            groups
            and
            event["time"]
            -
            groups[-1][-1]["time"]
            <= SIMULTANEOUS_WINDOW
        ):

            groups[-1].append(event)

        else:

            groups.append(
                [event]
            )

    valid = []
    multi = []
    unmatched = []
    no_output = []

    # --------------------------------------------
    # Characterize each event
    # --------------------------------------------

    for group in groups:

        inputs = {
            e["input"]
            for e in group
        }

        if len(inputs) > 1:

            multi.append(group)
            continue

        event = group[0]
        te = event["time"]

        ab = state_before(
            t,
            a,
            te
        )

        bb = state_before(
            t,
            b,
            te
        )

        aa = state_after(
            t,
            a,
            te
        )

        ba = state_after(
            t,
            b,
            te
        )

        out_before = ab ^ bb
        out_after = aa ^ ba

        # Input changed but XOR output did not
        if out_before == out_after:

            no_output.append(event)
            continue

        expected = (
            "rise"
            if out_after > out_before
            else "fall"
        )

        delay_type = (
            "TPLH"
            if expected == "rise"
            else "TPHL"
        )

        output_events = (
            orise
            if expected == "rise"
            else ofall
        )

        candidates = output_events[
            (output_events > te)
            &
            (
                output_events - te
                <= MAX_DELAY
            )
        ]

        if not len(candidates):

            unmatched.append(event)
            continue

        tout = candidates[
            np.argmin(
                candidates - te
            )
        ]

        valid.append({
            "input": event["input"],
            "direction": event["direction"],
            "type": delay_type,
            "input_time": te,
            "output_time": tout,
            "delay": tout - te,
            "state_before": f"{ab}{bb}",
            "state_after": f"{aa}{ba}"
        })

    # --------------------------------------------
    # Group delays
    # --------------------------------------------

    summary = {}

    for name in (
        "A",
        "B"
    ):

        for delay_type in (
            "TPHL",
            "TPLH"
        ):

            summary[
                f"{delay_type}_{name}"
            ] = [
                e["delay"]
                for e in valid
                if (
                    e["input"] == name
                    and
                    e["type"] == delay_type
                )
            ]

    all_tphl = (
        summary["TPHL_A"]
        +
        summary["TPHL_B"]
    )

    all_tplh = (
        summary["TPLH_A"]
        +
        summary["TPLH_B"]
    )

    all_delays = (
        all_tphl
        +
        all_tplh
    )

    summary.update({

        "Worst_TPHL":
            max(all_tphl)
            if all_tphl
            else np.nan,

        "Worst_TPLH":
            max(all_tplh)
            if all_tplh
            else np.nan,

        "Average_Delay":
            np.mean(all_delays)
            if all_delays
            else np.nan,

        "valid": valid,
        "multi": multi,
        "unmatched": unmatched,
        "no_output": no_output
    })

    return summary


# ============================================================
# RISE / FALL TIME
# ============================================================

def rise_fall_time(t, out):

    rise50, fall50 = crossings(
        t,
        out,
        V50
    )

    rise10, _ = crossings(
        t,
        out,
        V10
    )

    _, rise90 = crossings(
        t,
        out,
        V90
    )

    _, fall10 = crossings(
        t,
        out,
        V10
    )

    fall90, _ = crossings(
        t,
        out,
        V90
    )

    rise_times = []
    fall_times = []

    # --------------------------------------------
    # Rising transitions
    # --------------------------------------------

    for t50 in rise50:

        previous = fall50[
            fall50 < t50
        ]

        next_rise = rise50[
            rise50 > t50
        ]

        start = (
            max(previous)
            if len(previous)
            else t[0]
        )

        end = (
            min(next_rise)
            if len(next_rise)
            else t[-1]
        )

        r10 = rise10[
            (rise10 < t50)
            &
            (rise10 > start)
        ]

        r90 = rise90[
            (rise90 > t50)
            &
            (rise90 < end)
        ]

        if (
            len(r10)
            and
            len(r90)
            and
            r90[0] > r10[-1]
        ):

            rise_times.append(
                r90[0] - r10[-1]
            )

    # --------------------------------------------
    # Falling transitions
    # --------------------------------------------

    for t50 in fall50:

        previous = rise50[
            rise50 < t50
        ]

        next_fall = fall50[
            fall50 > t50
        ]

        start = (
            max(previous)
            if len(previous)
            else t[0]
        )

        end = (
            min(next_fall)
            if len(next_fall)
            else t[-1]
        )

        f90 = fall90[
            (fall90 < t50)
            &
            (fall90 > start)
        ]

        f10 = fall10[
            (fall10 > t50)
            &
            (fall10 < end)
        ]

        if (
            len(f90)
            and
            len(f10)
            and
            f10[0] > f90[-1]
        ):

            fall_times.append(
                f10[0] - f90[-1]
            )

    return {

        "rise":
            np.mean(rise_times)
            if rise_times
            else np.nan,

        "fall":
            np.mean(fall_times)
            if fall_times
            else np.nan,

        "rise_values":
            rise_times,

        "fall_values":
            fall_times
    }


# ============================================================
# DYNAMIC POWER CHARACTERIZATION
# ============================================================

def power_analysis(
    t,
    current,
    timing
):

    current_abs = np.abs(
        current
    )

    power = (
        VDD *
        current_abs
    )

    duration = (
        t[-1] -
        t[0]
    )

    energy = np.trapezoid(
        power,
        t
    )

    average_power = (
        energy /
        duration
    )

    transitions = len(
        timing["valid"]
    )

    return {

        "average_current":
            average_power / VDD,

        "peak_current":
            np.max(current_abs),

        "minimum_current":
            np.min(current_abs),

        "average_power":
            average_power,

        "peak_power":
            np.max(power),

        "energy":
            energy,

        "energy_per_transition":
            (
                energy / transitions
                if transitions
                else np.nan
            ),

        "waveform":
            power
    }


# ============================================================
# STATIC POWER CHARACTERIZATION
# ============================================================

def static_power(
    t,
    a,
    b,
    current,
    dc_data=None
):

    """
    Preserve the original function interface.

    Preferred method:
        use the separate DC dataset.

    Fallback:
        estimate static power from the transient data.
    """

    # ========================================================
    # PREFERRED: ACTUAL DC OPERATING POINTS
    # ========================================================

    if dc_data is not None:

        result = {}

        for name in (
            "00",
            "01",
            "10",
            "11"
        ):

            i_static = abs(
                dc_data[name]["current"]
            )

            result[name] = {

                "current":
                    i_static,

                "power":
                    VDD *
                    i_static
            }

        powers = [
            x["power"]
            for x in result.values()
        ]

        return {

            "states":
                result,

            "average":
                np.mean(powers),

            "maximum":
                np.max(powers)
        }

    # ========================================================
    # BACKWARD-COMPATIBLE TRANSIENT FALLBACK
    # ========================================================

    current_abs = np.abs(
        current
    )

    result = {}

    ar, af = crossings(
        t,
        a,
        V50
    )

    br, bf = crossings(
        t,
        b,
        V50
    )

    events = np.sort(
        np.concatenate([
            ar,
            af,
            br,
            bf
        ])
    )

    boundaries = np.concatenate([
        [t[0]],
        events,
        [t[-1]]
    ])

    for av in (
        0,
        1
    ):

        for bv in (
            0,
            1
        ):

            samples = []

            for start, end in zip(
                boundaries[:-1],
                boundaries[1:]
            ):

                if end <= start:
                    continue

                duration = (
                    end -
                    start
                )

                q1 = (
                    start +
                    0.25 * duration
                )

                q3 = (
                    start +
                    0.75 * duration
                )

                mask = (
                    (t >= q1)
                    &
                    (t <= q3)
                    &
                    (
                        (a >= V50).astype(int)
                        == av
                    )
                    &
                    (
                        (b >= V50).astype(int)
                        == bv
                    )
                )

                if np.any(mask):

                    samples.extend(
                        current_abs[mask]
                    )

            if samples:

                i_static = np.mean(
                    samples
                )

                result[f"{av}{bv}"] = {

                    "current":
                        i_static,

                    "power":
                        VDD *
                        i_static
                }

    powers = [
        x["power"]
        for x in result.values()
    ]

    return {

        "states":
            result,

        "average":
            np.mean(powers)
            if powers
            else np.nan,

        "maximum":
            np.max(powers)
            if powers
            else np.nan
    }


# ============================================================
# VTC LOADING
# ============================================================

def load_vtc(path):

    with open(
        path,
        encoding="utf-8",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    header_index = None

    for i, line in enumerate(lines):

        cols = (
            line.strip()
            .lower()
            .split()
        )

        if {
            "v1",
            "v(out)"
        }.issubset(cols):

            header_index = i
            break

    if header_index is None:

        raise ValueError(
            "Could not find VTC header."
        )

    header = (
        lines[header_index]
        .strip()
        .lower()
        .split()
    )

    vin_index = header.index(
        "v1"
    )

    out_index = header.index(
        "v(out)"
    )

    datasets = []
    current = []
    step = None

    def save():

        nonlocal current

        if len(current) > 5:

            datasets.append(
                (
                    step,
                    np.asarray(current)
                )
            )

        current = []

    for line in lines[
        header_index + 1:
    ]:

        text = line.strip()

        if not text:
            continue

        lower = text.lower()

        if lower.startswith(
            "step information:"
        ):

            save()

            if "bval=0" in lower:
                step = 0.0

            elif "bval=5" in lower:
                step = 5.0

            else:
                step = None

            continue

        parts = text.split()

        try:

            current.append([
                float(parts[vin_index]),
                float(parts[out_index])
            ])

        except (
            ValueError,
            IndexError
        ):

            continue

    save()

    curves = {

        "B=0":
            next(
                (
                    d
                    for s, d
                    in datasets
                    if s == 0
                ),
                None
            ),

        "B=5":
            next(
                (
                    d
                    for s, d
                    in datasets
                    if s == 5
                ),
                None
            )
    }

    # Fallback if labels were not preserved
    if (
        any(
            v is None
            for v in curves.values()
        )
        and
        len(datasets) >= 2
    ):

        curves = {

            "B=0":
                datasets[0][1],

            "B=5":
                datasets[1][1]
        }

    return {
        k: v
        for k, v in curves.items()
        if v is not None
    }


# ============================================================
# VTC CHARACTERIZATION
# ============================================================

def characterize_vtc(data):

    if data is None:
        return None

    order = np.argsort(
        data[:, 0]
    )

    vin = data[
        order,
        0
    ]

    vout = data[
        order,
        1
    ]

    # Remove duplicate input points
    vin, indices = np.unique(
        vin,
        return_index=True
    )

    vout = vout[
        indices
    ]

    # Prevent numerical overshoot from
    # becoming an unrealistic VOH/VOL.
    vout_physical = np.clip(
        vout,
        0.0,
        VDD
    )

    n = len(
        vout_physical
    )

    endpoint_count = max(
        3,
        int(0.01 * n)
    )

    first = vout_physical[
        :endpoint_count
    ]

    last = vout_physical[
        -endpoint_count:
    ]

    # Determine whether curve is
    # inverting or non-inverting.
    if np.mean(last) > np.mean(first):

        vol = np.mean(first)
        voh = np.mean(last)

    else:

        voh = np.mean(first)
        vol = np.mean(last)

    # --------------------------------------------------------
    # Gain
    # --------------------------------------------------------

    gain = np.gradient(
        vout_physical,
        vin
    )

    max_gain = np.max(
        gain
    )

    min_gain = np.min(
        gain
    )

    # --------------------------------------------------------
    # VM
    # --------------------------------------------------------

    vm_index = np.argmin(
        np.abs(
            vout_physical -
            vin
        )
    )

    vm = vin[
        vm_index
    ]

    # --------------------------------------------------------
    # Noise margins
    #
    # For inverter-like curves:
    # dVout/dVin = -1
    # gives VIL and VIH.
    # --------------------------------------------------------

    vil = np.nan
    vih = np.nan
    nml = np.nan
    nmh = np.nan

    if min_gain < -1:

        idx = np.where(
            (
                gain[:-1] + 1
            )
            *
            (
                gain[1:] + 1
            )
            <= 0
        )[0]

        if len(idx) >= 2:

            vil = vin[
                idx[0]
            ]

            vih = vin[
                idx[-1]
            ]

            nml = (
                vil -
                vol
            )

            nmh = (
                voh -
                vih
            )

    return {

        "vin":
            vin,

        "vout":
            vout_physical,

        "voh":
            voh,

        "vol":
            vol,

        "raw_voh":
            np.max(vout),

        "raw_vol":
            np.min(vout),

        "vm":
            vm,

        "max_gain":
            max_gain,

        "min_gain":
            min_gain,

        "vil":
            vil,

        "vih":
            vih,

        "nml":
            nml,

        "nmh":
            nmh,

        "type":
            (
                "Inverting"
                if min_gain < 0
                else "Non-inverting"
            )
    }


# ============================================================
# PLOTS
# ============================================================

def make_plots(
    t,
    a,
    b,
    out,
    power,
    timing,
    vtc
):

    # --------------------------------------------------------
    # Transient
    # --------------------------------------------------------

    plt.figure(
        figsize=(11, 6)
    )

    plt.plot(
        t * 1e9,
        a,
        label="A"
    )

    plt.plot(
        t * 1e9,
        b,
        label="B"
    )

    plt.plot(
        t * 1e9,
        out,
        label="OUT",
        linewidth=2
    )

    plt.axhline(
        V50,
        linestyle="--",
        alpha=0.4
    )

    for event in timing["valid"]:

        plt.axvline(
            event["input_time"] * 1e9,
            linestyle=":",
            alpha=0.4
        )

        plt.axvline(
            event["output_time"] * 1e9,
            linestyle="--",
            alpha=0.4
        )

    plt.xlabel("Time (ns)")
    plt.ylabel("Voltage (V)")
    plt.title(
        "CMOS XOR Transient Characterization"
    )
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        IMG /
        "xor_transient_characterization.png",
        dpi=300
    )

    plt.close()

    # --------------------------------------------------------
    # Power
    # --------------------------------------------------------

    plt.figure(
        figsize=(11, 5)
    )

    plt.plot(
        t * 1e9,
        power["waveform"] * 1e6
    )

    plt.xlabel("Time (ns)")
    plt.ylabel("Power (µW)")
    plt.title(
        "CMOS XOR Instantaneous Power"
    )
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        IMG /
        "xor_power_characterization.png",
        dpi=300
    )

    plt.close()

    # --------------------------------------------------------
    # VTC
    # --------------------------------------------------------

    plt.figure(
        figsize=(9, 6)
    )

    for name, curve in vtc.items():

        plt.plot(
            curve["vin"],
            curve["vout"],
            linewidth=2,
            label=name
        )

        plt.scatter(
            curve["vm"],
            np.interp(
                curve["vm"],
                curve["vin"],
                curve["vout"]
            ),
            s=50
        )

    plt.axhline(
        V50,
        linestyle="--",
        alpha=0.4
    )

    plt.axvline(
        V50,
        linestyle=":",
        alpha=0.4
    )

    plt.xlabel("Input A (V)")
    plt.ylabel("Output (V)")
    plt.title(
        "CMOS XOR Conditional VTC"
    )
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        IMG /
        "xor_vtc_characterization.png",
        dpi=300
    )

    plt.close()


# ============================================================
# REPORT HELPERS
# ============================================================

def add_row(
    rows,
    name,
    category,
    value,
    unit
):

    rows.append([
        name,
        category,
        value,
        unit
    ])


def fmt_ps(value):

    if np.isnan(value):
        return "N/A"

    return (
        f"{value * 1e12:.3f} ps"
    )


# ============================================================
# REPORTS
# ============================================================

def write_reports(
    timing,
    rise_fall,
    power,
    static,
    vtc
):

    # ========================================================
    # CSV
    # ========================================================

    csv_file = (
        SIM /
        "xor_characterization_summary.csv"
    )

    rows = []

    for key in (
        "TPHL_A",
        "TPLH_A",
        "TPHL_B",
        "TPLH_B"
    ):

        values = timing[key]

        add_row(
            rows,
            f"{key} average",
            "Timing",
            np.mean(values)
            if values
            else np.nan,
            "s"
        )

        add_row(
            rows,
            f"{key} worst",
            "Timing",
            max(values)
            if values
            else np.nan,
            "s"
        )

    for name, value in [

        (
            "Worst TPHL",
            timing["Worst_TPHL"]
        ),

        (
            "Worst TPLH",
            timing["Worst_TPLH"]
        ),

        (
            "Average Delay",
            timing["Average_Delay"]
        ),

        (
            "Rise Time",
            rise_fall["rise"]
        ),

        (
            "Fall Time",
            rise_fall["fall"]
        )
    ]:

        add_row(
            rows,
            name,
            "Timing",
            value,
            "s"
        )

    for i, value in enumerate(
        rise_fall["rise_values"],
        1
    ):

        add_row(
            rows,
            f"Rise Time Transition {i}",
            "Timing",
            value,
            "s"
        )

    for i, value in enumerate(
        rise_fall["fall_values"],
        1
    ):

        add_row(
            rows,
            f"Fall Time Transition {i}",
            "Timing",
            value,
            "s"
        )

    # Dynamic power

    for key, unit in [

        ("average_current", "A"),
        ("peak_current", "A"),
        ("minimum_current", "A"),
        ("average_power", "W"),
        ("peak_power", "W"),
        ("energy", "J"),
        ("energy_per_transition", "J")

    ]:

        add_row(
            rows,
            key,
            "Dynamic Power",
            power[key],
            unit
        )

    # Static power

    for name, value, unit in [

        (
            "Average Static Power",
            static["average"],
            "W"
        ),

        (
            "Maximum Static Power",
            static["maximum"],
            "W"
        )

    ]:

        add_row(
            rows,
            name,
            "Static Power",
            value,
            unit
        )

    for state_name, data in (
        static["states"].items()
    ):

        add_row(
            rows,
            f"State {state_name} Current",
            "Static Power",
            data["current"],
            "A"
        )

        add_row(
            rows,
            f"State {state_name} Power",
            "Static Power",
            data["power"],
            "W"
        )

    # VTC

    for name, curve in vtc.items():

        prefix = name.replace(
            "=",
            "_"
        )

        for key in (
            "voh",
            "vol",
            "raw_voh",
            "raw_vol",
            "vm",
            "max_gain",
            "min_gain",
            "vil",
            "vih",
            "nml",
            "nmh"
        ):

            add_row(
                rows,
                f"{prefix}_{key}",
                "VTC",
                curve[key],
                "V/V"
                if "gain" in key
                else "V"
            )

    with open(
        csv_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "Parameter",
            "Category",
            "Value",
            "Unit"
        ])

        writer.writerows(rows)

    # ========================================================
    # MARKDOWN
    # ========================================================

    md_file = (
        CALC /
        "xor_characterization.md"
    )

    with open(
        md_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "# CMOS XOR Characterization\n\n"
        )

        # Timing

        f.write(
            "## Timing\n\n"
            "| Parameter | Result |\n"
            "|---|---:|\n"
        )

        for key in (
            "TPHL_A",
            "TPLH_A",
            "TPHL_B",
            "TPLH_B"
        ):

            values = timing[key]

            f.write(
                f"| {key} average | "
                f"{fmt_ps(np.mean(values)) if values else 'N/A'} |\n"
            )

            f.write(
                f"| {key} worst | "
                f"{fmt_ps(max(values)) if values else 'N/A'} |\n"
            )

        for name, value in [

            (
                "Worst TPHL",
                timing["Worst_TPHL"]
            ),

            (
                "Worst TPLH",
                timing["Worst_TPLH"]
            ),

            (
                "Average Delay",
                timing["Average_Delay"]
            ),

            (
                "Rise Time",
                rise_fall["rise"]
            ),

            (
                "Fall Time",
                rise_fall["fall"]
            )

        ]:

            f.write(
                f"| {name} | "
                f"{fmt_ps(value)} |\n"
            )

        f.write(
            "\n### Rise-Time Transitions\n\n"
        )

        for i, value in enumerate(
            rise_fall["rise_values"],
            1
        ):

            f.write(
                f"- Transition {i}: "
                f"{value * 1e12:.3f} ps\n"
            )

        f.write(
            "\n### Fall-Time Transitions\n\n"
        )

        for i, value in enumerate(
            rise_fall["fall_values"],
            1
        ):

            f.write(
                f"- Transition {i}: "
                f"{value * 1e12:.3f} ps\n"
            )

        # Dynamic power

        f.write(
            "\n## Dynamic Power\n\n"
            "| Parameter | Result |\n"
            "|---|---:|\n"
        )

        power_rows = [

            (
                "Average Current",
                power["average_current"] * 1e6,
                "µA"
            ),

            (
                "Peak Current",
                power["peak_current"] * 1e6,
                "µA"
            ),

            (
                "Minimum Current",
                power["minimum_current"] * 1e6,
                "µA"
            ),

            (
                "Average Power",
                power["average_power"] * 1e6,
                "µW"
            ),

            (
                "Peak Power",
                power["peak_power"] * 1e6,
                "µW"
            ),

            (
                "Total Energy",
                power["energy"] * 1e15,
                "fJ"
            ),

            (
                "Energy / Transition",
                power["energy_per_transition"] * 1e15,
                "fJ"
            )
        ]

        for name, value, unit in power_rows:

            f.write(
                f"| {name} | "
                f"{value:.3f} {unit} |\n"
            )

        # Static power

        f.write(
            "\n## Static Power from DC Operating Points\n\n"
        )

        f.write(
            "| State | Current | Power |\n"
            "|---|---:|---:|\n"
        )

        for state_name in (
            "00",
            "01",
            "10",
            "11"
        ):

            if state_name not in static["states"]:
                continue

            data = static["states"][
                state_name
            ]

            f.write(
                f"| {state_name} | "
                f"{data['current'] * 1e9:.3f} nA | "
                f"{data['power'] * 1e9:.3f} nW |\n"
            )

        f.write(
            f"| **Average** | — | "
            f"**{static['average'] * 1e9:.3f} nW** |\n"
        )

        f.write(
            f"| **Maximum** | — | "
            f"**{static['maximum'] * 1e9:.3f} nW** |\n"
        )

        # VTC

        f.write(
            "\n## VTC\n\n"
        )

        for name, curve in vtc.items():

            f.write(
                f"### {name}\n\n"
            )

            f.write(
                "| Parameter | Value |\n"
                "|---|---:|\n"
            )

            for key in (
                "voh",
                "vol",
                "vm",
                "max_gain",
                "min_gain",
                "vil",
                "vih",
                "nml",
                "nmh"
            ):

                value = curve[key]

                text = (
                    "N/A"
                    if np.isnan(value)
                    else f"{value:.6f}"
                )

                f.write(
                    f"| {key} | "
                    f"{text} |\n"
                )

            f.write(
                f"| Transfer Type | "
                f"{curve['type']} |\n\n"
            )

        # Event classification

        f.write(
            "## Event Classification\n\n"
        )

        for name in (
            "valid",
            "multi",
            "unmatched",
            "no_output"
        ):

            f.write(
                f"- "
                f"{name.replace('_', ' ').title()}: "
                f"{len(timing[name])}\n"
            )

    # ========================================================
    # TXT ENGINEERING REPORT
    # ========================================================

    txt_file = (
        REPORT /
        "xor_characterization_report.txt"
    )

    with open(
        txt_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "CMOS XOR CHARACTERIZATION REPORT\n"
        )

        f.write(
            "=" * 60 +
            "\n\n"
        )

        f.write(
            "TIMING\n"
            + "-" * 60 +
            "\n"
        )

        for key in (
            "TPHL_A",
            "TPLH_A",
            "TPHL_B",
            "TPLH_B"
        ):

            values = timing[key]

            f.write(
                f"{key}: "
            )

            if values:

                f.write(
                    ", ".join(
                        f"{v * 1e12:.3f} ps"
                        for v in values
                    )
                )

            else:

                f.write(
                    "No valid transitions"
                )

            f.write("\n")

        f.write(
            f"\nWorst TPHL: "
            f"{fmt_ps(timing['Worst_TPHL'])}\n"
        )

        f.write(
            f"Worst TPLH: "
            f"{fmt_ps(timing['Worst_TPLH'])}\n"
        )

        f.write(
            f"Average Delay: "
            f"{fmt_ps(timing['Average_Delay'])}\n"
        )

        f.write(
            f"Rise Time: "
            f"{fmt_ps(rise_fall['rise'])}\n"
        )

        f.write(
            f"Fall Time: "
            f"{fmt_ps(rise_fall['fall'])}\n"
        )

        f.write(
            "\nDYNAMIC POWER\n"
            + "-" * 60 +
            "\n"
        )

        f.write(
            f"Average Current: "
            f"{power['average_current'] * 1e6:.3f} µA\n"
        )

        f.write(
            f"Peak Current: "
            f"{power['peak_current'] * 1e6:.3f} µA\n"
        )

        f.write(
            f"Average Power: "
            f"{power['average_power'] * 1e6:.3f} µW\n"
        )

        f.write(
            f"Peak Power: "
            f"{power['peak_power'] * 1e6:.3f} µW\n"
        )

        f.write(
            f"Energy: "
            f"{power['energy'] * 1e15:.3f} fJ\n"
        )

        f.write(
            f"Energy/Transition: "
            f"{power['energy_per_transition'] * 1e15:.3f} fJ\n"
        )

        f.write(
            "\nSTATIC POWER\n"
            + "-" * 60 +
            "\n"
        )

        for state_name in (
            "00",
            "01",
            "10",
            "11"
        ):

            data = static["states"].get(
                state_name
            )

            if data:

                f.write(
                    f"State {state_name}: "
                    f"{data['current'] * 1e9:.3f} nA, "
                    f"{data['power'] * 1e9:.3f} nW\n"
                )

        f.write(
            f"Average Static Power: "
            f"{static['average'] * 1e9:.3f} nW\n"
        )

        f.write(
            f"Maximum Static Power: "
            f"{static['maximum'] * 1e9:.3f} nW\n"
        )

        f.write(
            "\nVTC\n"
            + "-" * 60 +
            "\n"
        )

        for name, curve in vtc.items():

            f.write(
                f"\n{name}\n"
            )

            for key in (
                "voh",
                "vol",
                "vm",
                "max_gain",
                "min_gain",
                "vil",
                "vih",
                "nml",
                "nmh",
                "type"
            ):

                f.write(
                    f"{key}: "
                    f"{curve[key]}\n"
                )

        f.write(
            "\nEVENTS\n"
            + "-" * 60 +
            "\n"
        )

        for name in (
            "valid",
            "multi",
            "unmatched",
            "no_output"
        ):

            f.write(
                f"{name}: "
                f"{len(timing[name])}\n"
            )

    print(
        f"\nCSV report: {csv_file}"
    )

    print(
        f"Markdown report: {md_file}"
    )

    print(
        f"Engineering report: {txt_file}"
    )


# ============================================================
# CONSOLE OUTPUT
# ============================================================

def print_results(
    timing,
    rise_fall,
    power,
    static,
    vtc
):

    print()
    print("=" * 60)
    print(" XOR TIMING CHARACTERIZATION")
    print("=" * 60)

    for key in (
        "TPHL_A",
        "TPLH_A",
        "TPHL_B",
        "TPLH_B"
    ):

        values = timing[key]

        print()
        print(key)

        if not values:

            print(
                "  No valid transitions."
            )

            continue

        for i, value in enumerate(
            values,
            1
        ):

            print(
                f"  Transition {i}: "
                f"{value * 1e12:.3f} ps"
            )

        print(
            f"  Average: "
            f"{np.mean(values) * 1e12:.3f} ps"
        )

        print(
            f"  Worst case: "
            f"{max(values) * 1e12:.3f} ps"
        )

    print()

    for name, value in [

        (
            "Worst-case TPHL",
            timing["Worst_TPHL"]
        ),

        (
            "Worst-case TPLH",
            timing["Worst_TPLH"]
        ),

        (
            "Average Delay",
            timing["Average_Delay"]
        ),

        (
            "Rise Time",
            rise_fall["rise"]
        ),

        (
            "Fall Time",
            rise_fall["fall"]
        )

    ]:

        print(
            f"{name:20}: "
            f"{value * 1e12:.3f} ps"
            if not np.isnan(value)
            else
            f"{name:20}: N/A"
        )

    print()
    print(
        "RISE/FALL TRANSITIONS"
    )
    print("-" * 60)

    print(
        "Rise: "
        +
        (
            ", ".join(
                f"{v * 1e12:.3f} ps"
                for v in rise_fall["rise_values"]
            )
            or
            "None"
        )
    )

    print(
        "Fall: "
        +
        (
            ", ".join(
                f"{v * 1e12:.3f} ps"
                for v in rise_fall["fall_values"]
            )
            or
            "None"
        )
    )

    print()
    print("=" * 60)
    print(" XOR DYNAMIC POWER CHARACTERIZATION")
    print("=" * 60)

    for name, value, scale, unit in [

        (
            "Average Current",
            power["average_current"],
            1e6,
            "µA"
        ),

        (
            "Peak Current",
            power["peak_current"],
            1e6,
            "µA"
        ),

        (
            "Minimum Current",
            power["minimum_current"],
            1e6,
            "µA"
        ),

        (
            "Average Power",
            power["average_power"],
            1e6,
            "µW"
        ),

        (
            "Peak Power",
            power["peak_power"],
            1e6,
            "µW"
        ),

        (
            "Energy",
            power["energy"],
            1e15,
            "fJ"
        ),

        (
            "Energy/Transition",
            power["energy_per_transition"],
            1e15,
            "fJ"
        )

    ]:

        if np.isnan(value):

            text = "N/A"

        else:

            text = (
                f"{value * scale:.3f} "
                f"{unit}"
            )

        print(
            f"{name:20}: {text}"
        )

    print()
    print("=" * 60)
    print(" XOR STATIC POWER FROM DC DATASET")
    print("=" * 60)

    for state_name in (
        "00",
        "01",
        "10",
        "11"
    ):

        if state_name not in static["states"]:
            continue

        data = static["states"][
            state_name
        ]

        print(
            f"State {state_name}: "
            f"{data['current'] * 1e9:.3f} nA"
            f" | "
            f"{data['power'] * 1e9:.3f} nW"
        )

    print()

    print(
        f"Average Static Power : "
        f"{static['average'] * 1e9:.3f} nW"
    )

    print(
        f"Maximum Static Power : "
        f"{static['maximum'] * 1e9:.3f} nW"
    )

    print()
    print("=" * 60)
    print(" CONDITIONAL XOR VTC")
    print("=" * 60)

    for name, curve in vtc.items():

        print()
        print(name)

        print(
            f"  VOH       : "
            f"{curve['voh']:.6f} V"
        )

        print(
            f"  VOL       : "
            f"{curve['vol']:.6f} V"
        )

        print(
            f"  VM        : "
            f"{curve['vm']:.6f} V"
        )

        print(
            f"  Max Gain  : "
            f"{curve['max_gain']:.6f}"
        )

        print(
            f"  Min Gain  : "
            f"{curve['min_gain']:.6f}"
        )

        print(
            f"  Type      : "
            f"{curve['type']}"
        )

        for key in (
            "vil",
            "vih",
            "nml",
            "nmh"
        ):

            value = curve[key]

            print(
                f"  {key.upper():9}: "
                f"{value:.6f} V"
                if not np.isnan(value)
                else
                f"  {key.upper():9}: N/A"
            )

    print()
    print("EVENT SUMMARY")
    print("-" * 60)

    print(
        f"Valid single-input events : "
        f"{len(timing['valid'])}"
    )

    print(
        f"Multi-input events        : "
        f"{len(timing['multi'])}"
    )

    print(
        f"Unmatched events          : "
        f"{len(timing['unmatched'])}"
    )

    print(
        f"No-output events          : "
        f"{len(timing['no_output'])}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print(" CMOS XOR CHARACTERIZATION TOOL")
    print("=" * 60)

    # ========================================================
    # 1. TRANSIENT DATASET
    # ========================================================

    transient_file = select_file(
        "Select XOR transient data"
    )

    t, a, b, out, current = (
        load_transient(
            transient_file
        )
    )

    print()
    print("TRANSIENT DATA")
    print("-" * 60)

    print(
        f"File       : "
        f"{transient_file}"
    )

    print(
        f"Time       : "
        f"{t[0] * 1e9:.3f} "
        f"to "
        f"{t[-1] * 1e9:.3f} ns"
    )

    print(
        f"Samples    : "
        f"{len(t)}"
    )

    print(
        f"A range    : "
        f"{a.min():.3f} "
        f"to "
        f"{a.max():.3f} V"
    )

    print(
        f"B range    : "
        f"{b.min():.3f} "
        f"to "
        f"{b.max():.3f} V"
    )

    print(
        f"OUT range  : "
        f"{out.min():.6f} "
        f"to "
        f"{out.max():.6f} V"
    )

    print(
        f"Current    : "
        f"{current.min():.6e} "
        f"to "
        f"{current.max():.6e} A"
    )

    timing = timing_analysis(
        t,
        a,
        b,
        out
    )

    rise_fall = rise_fall_time(
        t,
        out
    )

    power = power_analysis(
        t,
        current,
        timing
    )

    # ========================================================
    # 2. VTC DATASET
    # ========================================================

    print()
    print(
        "Select the XOR VTC/DC-sweep data."
    )

    vtc_file = select_file(
        "Select XOR VTC data"
    )

    raw_vtc = load_vtc(
        vtc_file
    )

    vtc = {
        name:
            characterize_vtc(data)
        for name, data
        in raw_vtc.items()
    }

    # ========================================================
    # 3. STATIC DC DATASET
    # ========================================================

    print()
    print(
        "Select the XOR DC "
        "operating-point data."
    )

    dc_file = select_file(
        "Select XOR DC operating-point data"
    )

    dc_data = load_static_dc(
        dc_file
    )

    static = static_power(
        t,
        a,
        b,
        current,
        dc_data=dc_data
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print_results(
        timing,
        rise_fall,
        power,
        static,
        vtc
    )

    make_plots(
        t,
        a,
        b,
        out,
        power,
        timing,
        vtc
    )

    write_reports(
        timing,
        rise_fall,
        power,
        static,
        vtc
    )

    print()
    print("=" * 60)
    print(" CHARACTERIZATION COMPLETE")
    print("=" * 60)

    print()
    print("Generated:")

    print(
        "  ✓ Transient characterization plot"
    )

    print(
        "  ✓ VTC characterization plot"
    )

    print(
        "  ✓ Power characterization plot"
    )

    print(
        "  ✓ CSV summary"
    )

    print(
        "  ✓ Markdown engineering report"
    )

    print(
        "  ✓ TXT engineering report"
    )


if __name__ == "__main__":
    main()