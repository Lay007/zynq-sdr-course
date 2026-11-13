"""Instructor reference for the independent learner exercise."""


def fir_float(samples: list[float], taps: list[float]) -> list[float]:
    return [
        sum(taps[k] * samples[n - k] for k in range(min(n + 1, len(taps))))
        for n in range(len(samples))
    ]


def quantize_q15(values: list[float]) -> list[int]:
    return [max(-32768, min(32767, round(v * 32768))) for v in values]


def _round_div_ties_even(value: int, divisor: int) -> int:
    magnitude, remainder = divmod(abs(value), divisor)
    if remainder * 2 > divisor or (
        remainder * 2 == divisor and magnitude % 2
    ):
        magnitude += 1
    return magnitude if value >= 0 else -magnitude


def fir_q15(samples_q15: list[int], taps_q15: list[int]) -> list[int]:
    results = []
    for n in range(len(samples_q15)):
        accumulator = sum(
            taps_q15[k] * samples_q15[n - k]
            for k in range(min(n + 1, len(taps_q15)))
        )
        value = _round_div_ties_even(accumulator, 32768)
        results.append(max(-32768, min(32767, value)))
    return results
