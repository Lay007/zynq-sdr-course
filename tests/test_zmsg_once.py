"""The one-shot message buffer (zmsg send --once, Lab 11.48) decodes back to the frame, and zmsg.c builds it
exactly like the Python model two_board_message.once_iq."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
sys.path.insert(0, str(PY))

import lab_11_30_two_board_cfo_validation as L  # noqa: E402
import lab_11_32_two_board_fabric_coarse_cfo as B  # noqa: E402
import two_board_message as M  # noqa: E402
from qpsk_packet_v1 import encode_packet  # noqa: E402

TEXT, SEQ, LEAD, HEAD = b"Hello from board A", 17, 32, 8


def _states(iq: np.ndarray) -> np.ndarray:
    """Phase state (0..3) of every symbol, from the matched filter at the symbol instants."""
    z = iq[0::2] + 1j * iq[1::2]
    taps = L.load_rrc_taps()
    mf = np.convolve(z, taps)
    delay = len(taps) - 1
    sym = mf[delay::L.SPS][: len(z) // L.SPS]
    e0 = (sym.real < 0).astype(int)
    e1 = (sym.imag < 0).astype(int)
    p1 = e1
    p0 = e0 ^ e1
    return (p1 << 1) | p0


def test_once_buffer_decodes_to_the_frame():
    iq = M.once_iq(encode_packet(TEXT, SEQ), whiten=True, lead=LEAD)
    st = _states(iq)
    lead = st[HEAD:HEAD + LEAD]
    assert list(lead) == [0 if (LEAD - k) % 2 == 0 else 2 for k in range(LEAD)]   # 0, 2, 0, ..., 2
    assert st[HEAD + LEAD] == 0                                                   # the reference
    frame = st[HEAD + LEAD: HEAD + LEAD + 1 + M.SYMS]                             # reference + frame
    inc = np.diff(frame) % 4                                                      # differential decoding
    d1 = (inc >> 1) & 1
    d0 = (inc & 1) ^ d1
    bits = np.column_stack([d0, d1]).ravel()
    payload = np.unpackbits(np.frombuffer(encode_packet(TEXT, SEQ), np.uint8), bitorder="little") ^ M.WHITEN
    assert np.array_equal(bits[: M.PRE], np.array(B.long_frame_bits()[: M.PRE]))
    assert np.array_equal(bits[M.PRE:], payload)


@pytest.mark.skipif(shutil.which("cc") is None or os.name == "nt", reason="needs a host C compiler (Linux CI)")
def test_zmsg_builds_the_same_buffer(tmp_path):
    exe = tmp_path / "zmsg"
    src = ROOT / "blocks" / "block_11_integrated_sdr_project" / "sw" / "zmsg.c"
    subprocess.run(["cc", "-O2", "-o", str(exe), str(src), "-lm"], check=True)
    env = dict(os.environ, ZMSG_DRY_RUN="1")
    subprocess.run([str(exe), "send", TEXT.decode(), "--seq", str(SEQ), "--once", "--lead", str(LEAD)],
                   check=True, env=env, capture_output=True)
    got = np.fromfile("/tmp/zmsg.bin", dtype=np.int16)
    want = M.once_iq(encode_packet(TEXT, SEQ), whiten=True, lead=LEAD)
    assert got.size == want.size
    assert np.abs(got.astype(int) - want.astype(int)).max() <= 1   # lround vs numpy round on exact halves
