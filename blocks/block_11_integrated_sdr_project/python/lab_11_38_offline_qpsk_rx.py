#!/usr/bin/env python3
"""Lab 11.38 - deterministic offline QPSK receiver for saved SDR captures.

This tool is the software-visible half of the hardware-TX -> IQ-capture -> offline-RX
teaching step.  It deliberately keeps file-format conversion, sample-rate conversion,
matched filtering, timing/CFO acquisition and frame synchronization as separate stages.

Supported capture formats follow docs/iq-recording-metadata.md:

* ``ci16``: little-endian interleaved signed int16 I,Q;
* ``cu8``: interleaved unsigned 8-bit I,Q (RTL-SDR convention, 127.5 = zero);
* ``cf32``: little-endian interleaved float32 I,Q.

The first executable target is the existing course QPSK frame: 140 symbols at 480 kSym/s,
8 samples/symbol and the committed Q1.15 RRC taps.  The receiver finds that frame inside a
longer recording; it does not require the user to crop a packet by hand.  Packet/CRC decoding
is intentionally a later layer once the Lab 11.46 packet bridge exists.

Important evidence boundary: a successful ``--self-test`` proves the offline algorithm on a
synthetic/reference capture.  It is NOT evidence of a ZynqSDR or RTL-SDR hardware reception.
"""
from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
REFERENCE_DIR = (
    ROOT
    / "blocks"
    / "block_11_integrated_sdr_project"
    / "assets"
    / "end_to_end_bpsk_reference"
)
TX_BITS = REFERENCE_DIR / "tx_bits.txt"
RRC_TAPS = REFERENCE_DIR / "rrc_taps_q15.txt"

SPS = 8
SYMBOL_RATE_HZ = 480_000.0
MODEL_SAMPLE_RATE_HZ = SPS * SYMBOL_RATE_HZ
FRAME_SYMBOLS = 140
PREAMBLE_BITS = 24
PREAMBLE_SYMBOLS = PREAMBLE_BITS // 2
SUPPORTED_FORMATS = {"ci16", "cu8", "cf32"}


def load_course_reference() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (frame bits, QPSK symbols, float RRC taps) from committed handoff assets."""
    bits = np.loadtxt(TX_BITS, dtype=np.int8).reshape(-1)
    need_bits = 2 * FRAME_SYMBOLS
    if bits.size < need_bits:
        raise RuntimeError(f"{TX_BITS} has {bits.size} bits; need at least {need_bits}")
    bits = bits[:need_bits]

    i = 1.0 - 2.0 * bits[0::2]
    q = 1.0 - 2.0 * bits[1::2]
    symbols = (i + 1j * q) / np.sqrt(2.0)

    taps_q15 = np.loadtxt(RRC_TAPS, dtype=np.int64).reshape(-1)
    taps = taps_q15.astype(float) / 32768.0
    if taps.size != 65:
        raise RuntimeError(f"{RRC_TAPS} has {taps.size} taps; the course modem expects 65")
    return bits, symbols, taps


def load_metadata(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("capture metadata root must be a JSON object")
    return data


def validate_metadata(metadata: dict) -> tuple[str, float, int | None]:
    """Validate the fields the offline receiver needs and return format/rate/count."""
    sampling = metadata.get("sampling")
    if not isinstance(sampling, dict):
        raise ValueError("metadata must contain a 'sampling' object")

    iq_format = str(sampling.get("iq_format", "")).lower()
    if iq_format not in SUPPORTED_FORMATS:
        raise ValueError(
            f"unsupported sampling.iq_format={iq_format!r}; expected one of {sorted(SUPPORTED_FORMATS)}"
        )

    try:
        sample_rate_hz = float(sampling["sample_rate_hz"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("metadata sampling.sample_rate_hz must be a positive number") from exc
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("metadata sampling.sample_rate_hz must be a positive number")

    endianness = str(sampling.get("endianness", "little")).lower()
    if endianness not in {"little", "le"}:
        raise ValueError("the current offline receiver supports little-endian raw IQ only")
    if sampling.get("i_first", True) is not True:
        raise ValueError("the current offline receiver expects interleaved I,Q ordering")

    raw_count = sampling.get("sample_count")
    sample_count = None if raw_count is None else int(raw_count)
    if sample_count is not None and sample_count < 0:
        raise ValueError("metadata sampling.sample_count must be non-negative")
    return iq_format, sample_rate_hz, sample_count


def read_iq(path: Path, iq_format: str) -> np.ndarray:
    """Read one raw capture into complex128 reference samples without hiding its encoding."""
    if iq_format == "ci16":
        raw = np.fromfile(path, dtype="<i2")
        scale = 32768.0
        zero = 0.0
    elif iq_format == "cu8":
        raw = np.fromfile(path, dtype=np.uint8)
        scale = 127.5
        zero = 127.5
    elif iq_format == "cf32":
        raw = np.fromfile(path, dtype="<f4")
        scale = 1.0
        zero = 0.0
    else:
        raise ValueError(f"unsupported IQ format {iq_format!r}")

    if raw.size == 0:
        raise ValueError(f"capture is empty: {path}")
    if raw.size % 2:
        raise ValueError(f"capture has an odd number of scalar values: {raw.size}")

    values = raw.astype(np.float64)
    i = (values[0::2] - zero) / scale
    q = (values[1::2] - zero) / scale
    return i + 1j * q


def remove_dc_and_normalize(samples: np.ndarray) -> tuple[np.ndarray, complex, float]:
    """Expose DC removal and RMS normalization as a named numerical boundary."""
    x = np.asarray(samples, dtype=np.complex128)
    dc = complex(np.mean(x))
    centered = x - dc
    rms = float(np.sqrt(np.mean(np.abs(centered) ** 2)))
    if not np.isfinite(rms) or rms <= 1e-12:
        raise ValueError("capture has no usable AC signal energy after DC removal")
    return centered / rms, dc, rms


def rational_ratio(source_rate_hz: float, target_rate_hz: float, max_denominator: int = 4096) -> tuple[int, int]:
    """Return the explicit integer up/down ratio used by the resampler."""
    source_i = int(round(source_rate_hz))
    target_i = int(round(target_rate_hz))
    if source_i <= 0 or target_i <= 0:
        raise ValueError("sample rates must be positive")
    ratio = Fraction(target_i, source_i).limit_denominator(max_denominator)
    approximate = source_rate_hz * ratio.numerator / ratio.denominator
    tolerance_hz = max(1e-6, target_rate_hz * 1e-9)
    if abs(approximate - target_rate_hz) > tolerance_hz:
        raise ValueError(
            "sample-rate ratio cannot be represented closely enough with "
            f"max_denominator={max_denominator}: {source_rate_hz} -> {target_rate_hz} Hz"
        )
    return ratio.numerator, ratio.denominator


def rational_resample(
    samples: np.ndarray,
    up: int,
    down: int,
    *,
    half_taps: int = 12,
    chunk_outputs: int = 8192,
) -> np.ndarray:
    """Band-limited rational resampling without a SciPy dependency.

    Output instants are exactly ``m * down / up`` in source-sample units.  A short
    windowed-sinc interpolator supplies the anti-alias filtering; when downsampling its
    normalized cutoff is reduced by ``up/down``.  The direct implementation is slower than
    scipy.signal.resample_poly but keeps the course runtime dependency set small and makes the
    p/q relationship explicit for learners.
    """
    if up <= 0 or down <= 0:
        raise ValueError("resampling factors must be positive")
    if half_taps < 2:
        raise ValueError("half_taps must be at least 2")

    x = np.asarray(samples, dtype=np.complex128)
    if x.size == 0:
        return x.copy()
    if up == down:
        return x.copy()

    output_count = int(np.floor((x.size - 1) * up / down)) + 1
    result = np.empty(output_count, dtype=np.complex128)
    offsets = np.arange(-half_taps + 1, half_taps + 1, dtype=np.int64)
    cutoff = min(1.0, up / down)

    for first in range(0, output_count, chunk_outputs):
        last = min(first + chunk_outputs, output_count)
        out_index = np.arange(first, last, dtype=np.float64)
        position = out_index * down / up
        center = np.floor(position).astype(np.int64)
        source_index = center[:, None] + offsets[None, :]
        delta = position[:, None] - source_index
        valid = (source_index >= 0) & (source_index < x.size)
        clipped = np.clip(source_index, 0, x.size - 1)

        window = np.zeros_like(delta)
        inside = np.abs(delta) < half_taps
        window[inside] = 0.5 + 0.5 * np.cos(np.pi * delta[inside] / half_taps)
        kernel = cutoff * np.sinc(cutoff * delta) * window * valid
        norm = np.sum(kernel, axis=1)
        if np.any(np.abs(norm) < 1e-12):
            raise RuntimeError("resampler produced an empty interpolation kernel")
        result[first:last] = np.sum(x[clipped] * kernel, axis=1) / norm
    return result


def _symbol_cfo_rad_per_symbol(symbols: np.ndarray) -> float:
    """Fourth-power QPSK CFO estimator; acquisition range is +/- symbol_rate/8."""
    s = np.asarray(symbols, dtype=np.complex128)
    if s.size < 16:
        raise ValueError("too few symbols for CFO estimation")
    magnitude = np.abs(s)
    threshold = 0.20 * float(np.sqrt(np.mean(magnitude**2)))
    active = (magnitude[:-1] > threshold) & (magnitude[1:] > threshold)
    z = s**4
    cross = z[1:] * np.conj(z[:-1])
    cross = cross[active]
    if cross.size < 8 or abs(np.sum(cross)) < 1e-12:
        raise ValueError("not enough active QPSK energy for CFO estimation")
    return float(np.angle(np.sum(cross)) / 4.0)


def _normalized_preamble_metric(symbols: np.ndarray, preamble: np.ndarray, frame_symbols: int) -> np.ndarray:
    """Normalized complex correlation, restricted to starts that contain a complete frame."""
    max_start = len(symbols) - frame_symbols
    if max_start < 0:
        return np.empty(0, dtype=float)
    count = max_start + 1
    p = len(preamble)
    if len(symbols) < p:
        return np.empty(0, dtype=float)

    corr = np.correlate(symbols, preamble, mode="valid")[:count]
    energy = np.convolve(np.abs(symbols) ** 2, np.ones(p), mode="valid")[:count]
    reference_energy = float(np.sum(np.abs(preamble) ** 2))
    denominator = np.sqrt(np.maximum(energy * reference_energy, 1e-24))
    return np.abs(corr) / denominator


def acquire_frame(
    matched: np.ndarray,
    reference_symbols: np.ndarray,
    *,
    sps: int = SPS,
    symbol_rate_hz: float = SYMBOL_RATE_HZ,
) -> dict:
    """Jointly select sample phase, QPSK CFO branch and automatic frame start."""
    reference = np.asarray(reference_symbols, dtype=np.complex128)
    preamble = reference[:PREAMBLE_SYMBOLS]
    best: dict | None = None

    for sample_phase in range(sps):
        symbol_stream = np.asarray(matched[sample_phase::sps], dtype=np.complex128)
        if symbol_stream.size < reference.size + PREAMBLE_SYMBOLS:
            continue
        try:
            omega = _symbol_cfo_rad_per_symbol(symbol_stream)
        except ValueError:
            continue
        n = np.arange(symbol_stream.size, dtype=float)
        derotated = symbol_stream * np.exp(-1j * omega * n)
        metric = _normalized_preamble_metric(derotated, preamble, reference.size)
        if metric.size == 0:
            continue
        frame_index = int(np.argmax(metric))
        score = float(metric[frame_index])
        candidate = {
            "sample_phase": sample_phase,
            "frame_symbol_index": frame_index,
            "sync_metric": score,
            "coarse_omega": omega,
            "symbol_stream": derotated,
            "sync_metric_trace": metric,
        }
        if best is None or score > float(best["sync_metric"]):
            best = candidate

    if best is None:
        raise RuntimeError("no timing/CFO branch contained enough signal for frame acquisition")

    start = int(best["frame_symbol_index"])
    derotated = np.asarray(best["symbol_stream"])
    frame = derotated[start : start + reference.size].copy()

    # The preamble provides a residual phase/frequency fit after coarse fourth-power CFO.
    phase_error = np.unwrap(np.angle(frame[:PREAMBLE_SYMBOLS] * np.conj(preamble)))
    index = np.arange(PREAMBLE_SYMBOLS, dtype=float)
    slope, intercept = np.polyfit(index, phase_error, 1)
    frame_index = np.arange(frame.size, dtype=float)
    corrected = frame * np.exp(-1j * (intercept + slope * frame_index))

    gain = np.vdot(reference, corrected) / np.vdot(reference, reference)
    if abs(gain) < 1e-12:
        raise RuntimeError("acquired frame has effectively zero complex gain")
    equalized = corrected / gain

    total_omega = float(best["coarse_omega"]) + float(slope)
    return {
        "sample_phase": int(best["sample_phase"]),
        "frame_symbol_index": start,
        "sync_metric": float(best["sync_metric"]),
        "cfo_hz": total_omega / (2.0 * np.pi) * symbol_rate_hz,
        "coarse_cfo_hz": float(best["coarse_omega"]) / (2.0 * np.pi) * symbol_rate_hz,
        "residual_cfo_hz": float(slope) / (2.0 * np.pi) * symbol_rate_hz,
        "equalized_symbols": equalized,
        "sync_metric_trace": np.asarray(best["sync_metric_trace"], dtype=float),
    }


def hard_bits(symbols: np.ndarray) -> np.ndarray:
    """Course QPSK mapper convention: bit 0 -> positive axis, bit 1 -> negative axis."""
    result = np.empty(2 * len(symbols), dtype=np.int8)
    result[0::2] = (np.real(symbols) < 0).astype(np.int8)
    result[1::2] = (np.imag(symbols) < 0).astype(np.int8)
    return result


def analyse_reference_capture(
    samples: np.ndarray,
    source_sample_rate_hz: float,
    *,
    source_format: str = "complex",
) -> dict:
    """Run the deterministic Lab 11.38 float receiver against the committed course frame."""
    expected_bits, reference_symbols, taps = load_course_reference()
    normalized, dc, source_rms = remove_dc_and_normalize(samples)

    up, down = rational_ratio(source_sample_rate_hz, MODEL_SAMPLE_RATE_HZ)
    model_samples = rational_resample(normalized, up, down)
    model_samples, residual_dc, _ = remove_dc_and_normalize(model_samples)

    matched = np.convolve(model_samples, taps, mode="full")
    acquisition = acquire_frame(matched, reference_symbols)
    equalized = np.asarray(acquisition.pop("equalized_symbols"))
    sync_trace = np.asarray(acquisition.pop("sync_metric_trace"))

    recovered_bits = hard_bits(equalized)
    bit_errors = int(np.sum(recovered_bits != expected_bits))
    compared_bits = int(expected_bits.size)
    evm = float(
        np.sqrt(np.mean(np.abs(equalized - reference_symbols) ** 2))
        / np.sqrt(np.mean(np.abs(reference_symbols) ** 2))
        * 100.0
    )

    return {
        "evidence_scope": "offline-reference-rx-only",
        "hardware_rx_claimed": False,
        "source_format": source_format,
        "source_sample_rate_hz": float(source_sample_rate_hz),
        "model_sample_rate_hz": MODEL_SAMPLE_RATE_HZ,
        "resample_up": up,
        "resample_down": down,
        "source_samples": int(len(samples)),
        "model_samples": int(len(model_samples)),
        "removed_dc_i": float(dc.real),
        "removed_dc_q": float(dc.imag),
        "source_rms_before_normalization": source_rms,
        "residual_dc_after_resample": float(abs(residual_dc)),
        **acquisition,
        "sync_metric_peak": float(np.max(sync_trace)) if sync_trace.size else 0.0,
        "evm_percent": evm,
        "bit_errors": bit_errors,
        "compared_bits": compared_bits,
        "ber": bit_errors / compared_bits,
    }


def analyse_capture_file(capture_path: Path, metadata_path: Path) -> dict:
    metadata = load_metadata(metadata_path)
    iq_format, sample_rate_hz, declared_count = validate_metadata(metadata)
    samples = read_iq(capture_path, iq_format)
    if declared_count is not None and declared_count != samples.size:
        raise ValueError(
            f"metadata sample_count={declared_count}, but capture contains {samples.size} complex samples"
        )
    result = analyse_reference_capture(samples, sample_rate_hz, source_format=iq_format)
    result["capture"] = str(capture_path)
    result["metadata"] = str(metadata_path)
    result["recording_id"] = metadata.get("recording_id")
    return result


def synthetic_reference_capture(
    *,
    cfo_hz: float = 18_000.0,
    phase_rad: float = 0.73,
    prefix_samples: int = 503,
    suffix_samples: int = 700,
    snr_db: float = 34.0,
    seed: int = 1138,
) -> np.ndarray:
    """Create a longer-than-one-frame reference recording for ``--self-test``."""
    _, symbols, taps = load_course_reference()
    upsampled = np.zeros(symbols.size * SPS, dtype=np.complex128)
    upsampled[::SPS] = symbols
    tx = np.convolve(upsampled, taps, mode="full")
    recording = np.concatenate(
        [
            np.zeros(prefix_samples, dtype=np.complex128),
            tx,
            np.zeros(suffix_samples, dtype=np.complex128),
        ]
    )
    n = np.arange(recording.size, dtype=float)
    recording *= np.exp(1j * (phase_rad + 2.0 * np.pi * cfo_hz * n / MODEL_SAMPLE_RATE_HZ))
    recording += 0.08 - 0.05j

    signal_power = float(np.mean(np.abs(tx) ** 2))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    rng = np.random.default_rng(seed)
    noise = np.sqrt(noise_power / 2.0) * (
        rng.normal(size=recording.size) + 1j * rng.normal(size=recording.size)
    )
    return recording + noise


def run_self_test() -> dict:
    injected_cfo_hz = 18_000.0
    result = analyse_reference_capture(
        synthetic_reference_capture(cfo_hz=injected_cfo_hz),
        MODEL_SAMPLE_RATE_HZ,
        source_format="synthetic-complex",
    )
    cfo_error_hz = abs(float(result["cfo_hz"]) - injected_cfo_hz)
    result["self_test_injected_cfo_hz"] = injected_cfo_hz
    result["self_test_cfo_error_hz"] = cfo_error_hz
    passed = (
        int(result["bit_errors"]) == 0
        and float(result["sync_metric"]) >= 0.80
        and cfo_error_hz <= 500.0
        and float(result["evm_percent"]) <= 15.0
    )
    result["self_test_pass"] = passed
    return result


def default_metadata_path(capture_path: Path) -> Path:
    return capture_path.with_suffix(".json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", nargs="?", type=Path, help="raw .ci16/.cu8/.cf32 capture")
    parser.add_argument("--metadata", type=Path, help="JSON sidecar; defaults to capture basename + .json")
    parser.add_argument("--output", type=Path, help="optional JSON analysis report")
    parser.add_argument("--self-test", action="store_true", help="run a no-hardware deterministic acquisition test")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        result = run_self_test()
        rc = 0 if result["self_test_pass"] else 1
    else:
        if args.capture is None:
            raise SystemExit("capture path is required unless --self-test is used")
        metadata_path = args.metadata or default_metadata_path(args.capture)
        result = analyse_capture_file(args.capture, metadata_path)
        rc = 0

    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
