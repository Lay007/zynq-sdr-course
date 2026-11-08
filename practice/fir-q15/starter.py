"""Student-owned exercise copy. Implement each function in your workspace."""


def fir_float(samples: list[float], taps: list[float]) -> list[float]:
    """Return causal FIR outputs for every input sample."""
    raise NotImplementedError("Stage 1: implement the causal FIR")


def quantize_q15(values: list[float]) -> list[int]:
    """Round and saturate finite real values to signed Q1.15."""
    raise NotImplementedError("Stage 2: implement Q1.15 conversion")


def fir_q15(samples_q15: list[int], taps_q15: list[int]) -> list[int]:
    """Causal integer FIR, nearest-even rescaling, signed int16 saturation."""
    raise NotImplementedError("Stage 3: implement the integer FIR")
