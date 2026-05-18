#!/usr/bin/env python3
"""Lab 8.6 - Channel coding and interleaving BER comparison."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class CodingConfig:
    snr_db_points: tuple[float, ...] = (0.0, 2.0, 4.0, 6.0, 8.0)
    frames: int = 80
    info_bits_per_frame: int = 240
    burst_probability: float = 0.012
    burst_length: int = 10
    burst_gain: float = 6.0
    ldpc_k: int = 24
    ldpc_m: int = 12
    ldpc_max_iter: int = 14
    seed: int = 86


def conv_encode(bits: np.ndarray) -> np.ndarray:
    s1 = 0
    s2 = 0
    out: list[int] = []
    terminated = np.concatenate([bits.astype(np.uint8), np.zeros(2, dtype=np.uint8)])
    for b in terminated:
        b = int(b)
        o1 = b ^ s1 ^ s2  # 111
        o2 = b ^ s2       # 101
        out.extend((o1, o2))
        s2 = s1
        s1 = b
    return np.array(out, dtype=np.uint8)


def viterbi_decode_hard(coded: np.ndarray) -> np.ndarray:
    if len(coded) % 2 != 0:
        raise ValueError("Convolutional coded length must be even.")
    steps = len(coded) // 2
    states = 4
    inf = 10**9

    next_state = np.zeros((states, 2), dtype=np.int64)
    out_pair = np.zeros((states, 2, 2), dtype=np.uint8)
    for st in range(states):
        s1 = (st >> 1) & 1
        s2 = st & 1
        for b in (0, 1):
            o1 = b ^ s1 ^ s2
            o2 = b ^ s2
            ns = ((b << 1) | s1) & 0b11
            next_state[st, b] = ns
            out_pair[st, b] = np.array([o1, o2], dtype=np.uint8)

    metric = np.full(states, inf, dtype=np.int64)
    metric[0] = 0
    prev_state = np.zeros((steps, states), dtype=np.int64)
    prev_bit = np.zeros((steps, states), dtype=np.uint8)

    for t in range(steps):
        rx = coded[2 * t : 2 * t + 2]
        new_metric = np.full(states, inf, dtype=np.int64)
        for st in range(states):
            m = metric[st]
            if m >= inf:
                continue
            for b in (0, 1):
                ns = next_state[st, b]
                dist = int(np.sum(rx != out_pair[st, b]))
                cand = m + dist
                if cand < new_metric[ns]:
                    new_metric[ns] = cand
                    prev_state[t, ns] = st
                    prev_bit[t, ns] = b
        metric = new_metric

    st = 0  # terminated encoder
    decoded = np.zeros(steps, dtype=np.uint8)
    for t in range(steps - 1, -1, -1):
        b = prev_bit[t, st]
        decoded[t] = b
        st = prev_state[t, st]
    return decoded[:-2]


def ldpc_matrices(k: int, m: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    a = np.zeros((m, k), dtype=np.uint8)
    for r in range(m):
        idx = rng.choice(k, size=4, replace=False)
        a[r, idx] = 1
    # Ensure every information bit participates in at least one check.
    for c in range(k):
        if np.sum(a[:, c]) == 0:
            a[c % m, c] = 1
    h = np.concatenate([a, np.eye(m, dtype=np.uint8)], axis=1)
    return a, h


def ldpc_encode_block(info: np.ndarray, a: np.ndarray) -> np.ndarray:
    p = (a @ info) % 2
    return np.concatenate([info, p.astype(np.uint8)])


def ldpc_decode_block_hard(bits: np.ndarray, h: np.ndarray, max_iter: int, llr: np.ndarray | None = None) -> np.ndarray:
    b = bits.astype(np.uint8).copy()
    deg = np.sum(h, axis=0).astype(np.float64)
    deg = np.maximum(deg, 1.0)
    for _ in range(max_iter):
        syn = (h @ b) % 2
        if np.all(syn == 0):
            break
        unsat = (h.T @ syn).astype(np.float64)
        score = unsat / deg
        cand = np.where(score > 0.5)[0]
        if len(cand) == 0:
            cand = np.array([int(np.argmax(score))], dtype=np.int64)
        if llr is not None and len(cand) > 1:
            rel = np.abs(llr[cand])
            take = max(1, len(cand) // 3)
            cand = cand[np.argsort(rel)[:take]]
        b[cand] ^= 1
    return b


def bpsk_mod(bits: np.ndarray) -> np.ndarray:
    return (1.0 - 2.0 * bits.astype(np.float64)).astype(np.float64)


def add_awgn_burst(
    x: np.ndarray,
    snr_db: float,
    burst_prob: float,
    burst_len: int,
    burst_gain: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    sig_pow = np.mean(np.abs(x) ** 2)
    noise_pow = sig_pow / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_pow) * rng.standard_normal(len(x))

    mask = np.zeros(len(x), dtype=bool)
    for i in range(len(x)):
        if rng.random() < burst_prob:
            end = min(len(x), i + burst_len)
            mask[i:end] = True
    burst_noise = np.zeros(len(x), dtype=np.float64)
    burst_noise[mask] = burst_gain * np.sqrt(noise_pow) * rng.standard_normal(np.sum(mask))
    y = x + noise + burst_noise
    llr = 2.0 * y / max(noise_pow, 1e-12)
    return y, llr


def interleave(bits: np.ndarray, perm: np.ndarray) -> np.ndarray:
    return bits[perm]


def deinterleave(bits: np.ndarray, perm: np.ndarray) -> np.ndarray:
    out = np.empty_like(bits)
    out[perm] = bits
    return out


def main() -> None:
    cfg = CodingConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    a, h = ldpc_matrices(cfg.ldpc_k, cfg.ldpc_m, cfg.seed + 101)
    ldpc_n = cfg.ldpc_k + cfg.ldpc_m
    if cfg.info_bits_per_frame % cfg.ldpc_k != 0:
        raise ValueError("info_bits_per_frame must be multiple of ldpc_k.")
    blocks_per_frame = cfg.info_bits_per_frame // cfg.ldpc_k

    curves = {
        "uncoded": [],
        "conv_no_interleaver": [],
        "conv_with_interleaver": [],
        "ldpc_no_interleaver": [],
        "ldpc_with_interleaver": [],
    }

    for snr_db in cfg.snr_db_points:
        err = {name: 0 for name in curves}
        total = {name: 0 for name in curves}

        for _ in range(cfg.frames):
            info = rng.integers(0, 2, size=cfg.info_bits_per_frame, dtype=np.uint8)

            # Uncoded baseline.
            x_u = bpsk_mod(info)
            y_u, _ = add_awgn_burst(
                x_u,
                snr_db,
                cfg.burst_probability,
                cfg.burst_length,
                cfg.burst_gain,
                rng,
            )
            dec_u = (y_u < 0).astype(np.uint8)
            err["uncoded"] += int(np.sum(dec_u != info))
            total["uncoded"] += len(info)

            # Convolutional coding.
            c_conv = conv_encode(info)
            p_conv = rng.permutation(len(c_conv))
            x_conv = bpsk_mod(c_conv)
            y_conv, _ = add_awgn_burst(
                x_conv,
                snr_db,
                cfg.burst_probability,
                cfg.burst_length,
                cfg.burst_gain,
                rng,
            )
            hard_conv = (y_conv < 0).astype(np.uint8)
            dec_conv = viterbi_decode_hard(hard_conv)
            n_cmp = min(len(dec_conv), len(info))
            err["conv_no_interleaver"] += int(np.sum(dec_conv[:n_cmp] != info[:n_cmp]))
            total["conv_no_interleaver"] += n_cmp

            c_conv_i = interleave(c_conv, p_conv)
            x_conv_i = bpsk_mod(c_conv_i)
            y_conv_i, _ = add_awgn_burst(
                x_conv_i,
                snr_db,
                cfg.burst_probability,
                cfg.burst_length,
                cfg.burst_gain,
                rng,
            )
            hard_conv_i = (y_conv_i < 0).astype(np.uint8)
            hard_conv_i = deinterleave(hard_conv_i, p_conv)
            dec_conv_i = viterbi_decode_hard(hard_conv_i)
            n_cmp = min(len(dec_conv_i), len(info))
            err["conv_with_interleaver"] += int(np.sum(dec_conv_i[:n_cmp] != info[:n_cmp]))
            total["conv_with_interleaver"] += n_cmp

            # LDPC-like sparse parity-check coding.
            blocks = info.reshape(blocks_per_frame, cfg.ldpc_k)
            c_ldpc = np.concatenate([ldpc_encode_block(b, a) for b in blocks])
            p_ldpc = rng.permutation(len(c_ldpc))
            x_ldpc = bpsk_mod(c_ldpc)
            y_ldpc, llr_ldpc = add_awgn_burst(
                x_ldpc,
                snr_db,
                cfg.burst_probability,
                cfg.burst_length,
                cfg.burst_gain,
                rng,
            )
            hard_ldpc = (y_ldpc < 0).astype(np.uint8)
            dec_info_blocks = []
            for bi in range(blocks_per_frame):
                st = bi * ldpc_n
                en = st + ldpc_n
                dec_block = ldpc_decode_block_hard(
                    hard_ldpc[st:en],
                    h,
                    cfg.ldpc_max_iter,
                    llr=llr_ldpc[st:en],
                )
                dec_info_blocks.append(dec_block[: cfg.ldpc_k])
            dec_ldpc = np.concatenate(dec_info_blocks)
            err["ldpc_no_interleaver"] += int(np.sum(dec_ldpc != info))
            total["ldpc_no_interleaver"] += len(info)

            c_ldpc_i = interleave(c_ldpc, p_ldpc)
            x_ldpc_i = bpsk_mod(c_ldpc_i)
            y_ldpc_i, llr_ldpc_i = add_awgn_burst(
                x_ldpc_i,
                snr_db,
                cfg.burst_probability,
                cfg.burst_length,
                cfg.burst_gain,
                rng,
            )
            hard_ldpc_i = (y_ldpc_i < 0).astype(np.uint8)
            hard_ldpc_i = deinterleave(hard_ldpc_i, p_ldpc)
            llr_ldpc_i = deinterleave(llr_ldpc_i, p_ldpc)
            dec_info_blocks_i = []
            for bi in range(blocks_per_frame):
                st = bi * ldpc_n
                en = st + ldpc_n
                dec_block = ldpc_decode_block_hard(
                    hard_ldpc_i[st:en],
                    h,
                    cfg.ldpc_max_iter,
                    llr=llr_ldpc_i[st:en],
                )
                dec_info_blocks_i.append(dec_block[: cfg.ldpc_k])
            dec_ldpc_i = np.concatenate(dec_info_blocks_i)
            err["ldpc_with_interleaver"] += int(np.sum(dec_ldpc_i != info))
            total["ldpc_with_interleaver"] += len(info)

        for name in curves:
            curves[name].append(float(err[name] / max(total[name], 1)))

    fig_path = ASSET_DIR / "lab86_channel_coding_ber.png"
    metrics_path = ASSET_DIR / "lab86_channel_coding_metrics.json"

    plt.figure(figsize=(7.8, 4.5))
    for name, vals in curves.items():
        plt.semilogy(cfg.snr_db_points, vals, marker="o", label=name.replace("_", " "))
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("SNR, dB")
    plt.ylabel("BER")
    plt.title("Lab 8.6 - Coding and interleaving BER comparison")
    plt.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()

    metrics_path.write_text(
        json.dumps(
            {
                "config": asdict(cfg),
                "snr_db_points": list(cfg.snr_db_points),
                "ber_curves": curves,
                "notes": {
                    "channel_model": "AWGN plus random burst noise with fixed average SNR",
                    "convolutional_code": "rate 1/2, K=3, generators (7,5) octal, hard Viterbi",
                    "ldpc_like_code": "systematic sparse parity-check block code with hard bit-flip decoder",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Lab 8.6 - Channel coding BER comparison")
    for i, snr in enumerate(cfg.snr_db_points):
        print(
            f"SNR {snr:>4.1f} dB | "
            f"uncoded={curves['uncoded'][i]:.4e}, "
            f"conv={curves['conv_no_interleaver'][i]:.4e}, "
            f"conv+interleaver={curves['conv_with_interleaver'][i]:.4e}, "
            f"ldpc={curves['ldpc_no_interleaver'][i]:.4e}, "
            f"ldpc+interleaver={curves['ldpc_with_interleaver'][i]:.4e}"
        )
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
