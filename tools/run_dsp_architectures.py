#!/usr/bin/env python3
"""Compare NCO and FFT schedules with Icarus and produce simulation metrics."""

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

from ofdm_fft_fixed import fft64_q15


ROOT = Path(__file__).resolve().parents[1]
BLOCK5 = ROOT / "blocks/block_05_fpga_hdl_flow"
BLOCK8 = ROOT / "blocks/block_08_modulation_and_synchronization"
FFT_MODES = {"fft_base": (0, 0), "fft_fabric": (1, 0), "fft_bram": (1, 1)}
TURN = 1 << 32
AMPLITUDE = 7 / 8
TONE_LENGTH = 4096
TONE_BIN = 197
START_PHASE = 0x13579BDF
CORDIC_STEPS = 16


def simulate(
    work: Path, cwd: Path, bench: Path, rtl: list[Path],
    defines: list[str], args: list[str], label: str,
) -> str:
    image = work / f"{label}.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", bench.stem, "-o", str(image),
                    *defines, *map(str, rtl), str(bench)], cwd=cwd, check=True, timeout=60)
    process = subprocess.run(["vvp", str(image), *args], cwd=cwd, capture_output=True,
                             text=True, timeout=60)
    log = process.stdout + process.stderr
    (work / f"{label}.log").write_text(log, encoding="utf-8", newline="\n")
    if process.returncode or not re.search(r"^PASS ", log, re.MULTILINE):
        raise RuntimeError(f"{label}:\n{log}")
    print(label, next(line for line in log.splitlines() if line.startswith("PASS ")))
    return log


def cordic_model(phase: int) -> tuple[int, int]:
    scale = math.prod(math.hypot(1, 2.0**-step) for step in range(CORDIC_STEPS))
    x, y = round(AMPLITUDE * 2**22 / scale), 0
    angle = (phase + TURN // 2) % TURN - TURN // 2
    if angle >= TURN // 4 or angle < -TURN // 4:
        x = -x
        angle += TURN // 2 if angle < 0 else -TURN // 2
    for step in range(CORDIC_STEPS):
        direction = 1 if angle >= 0 else -1
        rotation = round(math.atan(2.0**-step) * TURN / math.tau)
        x, y = x - direction * (y >> step), y + direction * (x >> step)
        angle -= direction * rotation
    return (x + 64) >> 7, (y + 64) >> 7


def lut_model(phase: int) -> tuple[int, int]:
    # An independent full-turn reference checks the ROM quadrant folding.
    angle = math.tau * (phase >> 22) / 1024
    return (round(AMPLITUDE * 32768 * math.cos(angle)),
            round(AMPLITUDE * 32768 * math.sin(angle)))


def compare_nco(work: Path, tone_bin: int) -> dict:
    rom = [round(AMPLITUDE * 32768 * math.sin(math.pi * index / 512)) for index in range(257)]
    (work / "nco_quarter_q15.mem").write_text(
        "".join(f"{word:04x}\n" for word in rom), encoding="ascii", newline="\n",
    )
    inc = tone_bin * TURN // TONE_LENGTH
    phases = [(START_PHASE + k * inc) % TURN for k in range(TONE_LENGTH)]
    phases += [(quadrant * TURN // 4 + offset) % TURN
               for quadrant in range(4) for offset in (-1, 0, 1)]
    ideal = AMPLITUDE * np.exp(1j * math.tau * np.array(phases, dtype=np.float64) / TURN)
    bench = BLOCK5 / "tb/tb_nco_phase_architectures.sv"
    variants = {}
    for mode, name, model in ((0, "nco_lut", lut_model), (1, "nco_cordic", cordic_model)):
        expected = [model(phase) for phase in phases]
        (work / "nco_vectors.txt").write_text(
            "".join(f"{p:08x} {i} {q}\n" for p, (i, q) in zip(phases, expected)),
            encoding="ascii", newline="\n",
        )
        log = simulate(work, work, bench, [BLOCK5 / "rtl/nco_phase_architectures.sv"],
                       [f"-P{bench.stem}.CORDIC={mode}"], [], name)
        match = re.search(rf"^PASS CORDIC={mode} samples=(\d+) latency=(\d+) ii=(\d+)$", log, re.MULTILINE)
        if match is None:
            raise RuntimeError(f"{name}: missing timing metrics")
        compared, latency, ii = map(int, match.groups())
        trace_path = work / f"{name}_trace.txt"
        (work / "nco_trace.txt").replace(trace_path)
        trace = np.loadtxt(trace_path, dtype=np.int64)
        np.testing.assert_array_equal(trace, expected)
        if compared != len(phases):
            raise RuntimeError(f"{name}: incomplete phase coverage")
        actual = (trace[:, 0] + 1j * trace[:, 1]) / 32768
        phase_error = np.angle(actual * ideal.conj())
        bins = np.abs(np.fft.fft(actual[:TONE_LENGTH]))
        if np.argmax(bins) != tone_bin:
            raise RuntimeError(f"{name}: expected tone is not the dominant bin")
        tone = bins[tone_bin]
        bins[tone_bin] = 0
        spur = int(np.argmax(bins))
        variants[name] = {
            "compared_phases": compared, "latency_clocks": latency, "ii_clocks": ii,
            "max_phase_error_deg": float(np.max(np.abs(phase_error)) * 180 / np.pi),
            "rms_complex_error_fs": float(np.sqrt(np.mean(np.abs(actual - ideal)**2))),
            "sfdr_dbc": float(20 * np.log10(tone / bins[spur])),
            "largest_spur_bin": spur if spur < TONE_LENGTH // 2 else spur - TONE_LENGTH,
        }
    return {
        "phase_bits": 32, "amplitude_fs": AMPLITUDE, "lut_address_bits": 10,
        "quarter_wave_entries": len(rom), "cordic_steps": CORDIC_STEPS,
        "tone_samples": TONE_LENGTH, "tone_bin": tone_bin,
        "initial_phase_code": START_PHASE, "phase_increment_code": inc,
        "variants": variants,
    }


def compare_fft(work: Path) -> dict:
    bench = BLOCK8 / "tb/tb_ofdm_fft64_sequential.sv"
    rtl = [BLOCK8 / "rtl" / f"{name}.v" for name in (
        "ofdm_fft64_sequential", "ofdm_ifft64_sequential", "ofdm_ifft_butterfly", "ofdm_iq_bank_ram",
    )]
    variants = {}
    for name, (pipelined, bram) in FFT_MODES.items():
        defines = [f"-DOFDM_IFFT_PIPELINED={pipelined}", f"-DOFDM_IFFT_BRAM={bram}"]
        log = simulate(work, ROOT, bench, rtl, defines, ["+continuous"], name)
        simulate(work, ROOT, bench, rtl, defines, [], f"{name}_stalls")
        match = re.search(r"^FFT bins=(128) latency=(\d+) last_in_to_first_out=(\d+) frame_ii=(\d+)$",
                          log, re.MULTILINE)
        if match is None:
            raise RuntimeError(f"{name}: missing FFT timing metrics")
        compared, latency, drain_delay, ii = map(int, match.groups())
        variants[name] = {
            "compared_bins_per_run": compared, "first_input_to_first_bin_clocks": latency,
            "last_input_to_first_bin_clocks": drain_delay, "frame_ii_clocks": ii,
        }
    path = ROOT / "verification/vectors/block08_ofdm_ifft_bin1_expected.mem"
    pairs = []
    for word in path.read_text(encoding="ascii").split():
        packed = int(word, 16)
        pairs.append(tuple((part ^ 32768) - 32768 for part in (packed >> 16, packed & 65535)))
    fixed = np.asarray(fft64_q15(tuple(pairs)).bins)
    x = np.asarray(pairs)
    reference = np.fft.fft(x[:, 0] + 1j * x[:, 1]) / 64
    error = fixed - np.column_stack((reference.real, reference.imag))
    return {
        "scaling": "FFT(x)/64", "sample_format": "signed Q1.15",
        "max_component_error_lsb_vs_numpy": float(np.max(np.abs(error))),
        "rms_complex_error_lsb_vs_numpy": float(np.sqrt(np.mean(np.sum(error**2, axis=1)))),
        "variants": variants,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/dsp-architecture-sim")
    parser.add_argument("--family", choices=("all", "fft", "nco"), default="all")
    parser.add_argument("--tone-bin", type=int, default=TONE_BIN,
                        help="Coherent NCO tone bin, 1..2047")
    args = parser.parse_args()
    if not 1 <= args.tone_bin < TONE_LENGTH // 2:
        parser.error("--tone-bin must be in 1..2047")
    for command in ("iverilog", "vvp"):
        if shutil.which(command) is None:
            parser.error(f"{command} is required")
    work = args.output.resolve()
    work.mkdir(parents=True, exist_ok=True)
    for family in ("nco", "fft"):
        if args.family in ("all", family):
            result = compare_nco(work, args.tone_bin) if family == "nco" else compare_fft(work)
            (work / f"{family}_simulation.json").write_text(
                json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n",
            )


if __name__ == "__main__":
    main()
