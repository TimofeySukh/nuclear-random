from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VonNeumannExtractor:
    pending_bit: int | None = None
    byte_buffer: int = 0
    byte_bit_count: int = 0

    def feed_raw_bits(self, bits: list[int]) -> "ExtractionResult":
        accepted_bits: list[int] = []
        discarded_pairs = 0

        for bit in bits:
            if bit not in (0, 1):
                raise ValueError("raw bits must be 0 or 1.")

            if self.pending_bit is None:
                self.pending_bit = bit
                continue

            first = self.pending_bit
            self.pending_bit = None

            if first == 0 and bit == 1:
                accepted_bits.append(0)
            elif first == 1 and bit == 0:
                accepted_bits.append(1)
            else:
                discarded_pairs += 1

        output_bytes = bytearray()
        for bit in accepted_bits:
            self.byte_buffer = (self.byte_buffer << 1) | bit
            self.byte_bit_count += 1
            if self.byte_bit_count == 8:
                output_bytes.append(self.byte_buffer)
                self.byte_buffer = 0
                self.byte_bit_count = 0

        return ExtractionResult(
            raw_bits_seen=len(bits),
            accepted_bits=accepted_bits,
            discarded_pairs=discarded_pairs,
            output_bytes=bytes(output_bytes),
        )


@dataclass(frozen=True)
class ExtractionResult:
    raw_bits_seen: int
    accepted_bits: list[int] = field(default_factory=list)
    discarded_pairs: int = 0
    output_bytes: bytes = b""

    @property
    def accepted_bit_count(self) -> int:
        return len(self.accepted_bits)


def raw_bits_from_dt_us(dt_us: int, *, bit_count: int = 2) -> list[int]:
    if dt_us < 0:
        raise ValueError("dt_us must be greater than or equal to zero.")
    if bit_count < 1:
        raise ValueError("bit_count must be positive.")
    return [(dt_us >> offset) & 1 for offset in range(bit_count)]

