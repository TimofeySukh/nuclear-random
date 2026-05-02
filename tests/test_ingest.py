from __future__ import annotations

from nuclear_random_api.extractor import VonNeumannExtractor, raw_bits_from_dt_us


def test_raw_bits_from_dt_us_reads_low_bits() -> None:
    assert raw_bits_from_dt_us(0b101101, bit_count=4) == [1, 0, 1, 1]


def test_von_neumann_extractor_accepts_only_mixed_pairs() -> None:
    extractor = VonNeumannExtractor()

    result = extractor.feed_raw_bits([0, 1, 1, 0, 0, 0, 1, 1])

    assert result.accepted_bits == [0, 1]
    assert result.accepted_bit_count == 2
    assert result.discarded_pairs == 2
    assert result.output_bytes == b""


def test_von_neumann_extractor_emits_full_bytes() -> None:
    extractor = VonNeumannExtractor()

    result = extractor.feed_raw_bits([0, 1] * 8)

    assert result.accepted_bits == [0] * 8
    assert result.output_bytes == b"\x00"

