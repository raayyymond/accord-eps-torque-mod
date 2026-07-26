"""tva_sa_key.py - Verified Honda EPS SecurityAccess seed->key for 2020 Accord (TVA chassis).

Status: VERIFIED via datasheet-backed disassembly of the V850E2 firmware
SA-key computation routine at 0x00AAB4. The full bit-level audit trail
is in V850_ALGORITHM_VERIFIED.md (Wave 3, 2026-05-23).

Algorithm:

    seed16 = received_seed & 0xFFFF
    key16  = ((seed16 + 0x0211) & 0xFFFF) XOR ((seed16 * 0x0212) mod 0x1220)

Constants source: read from firmware code flash at 0x92C0..0x92C5 via
`sld.hu 0[ep]`, `sld.hu 2[ep]`, `sld.hu 4[ep]` (where ep=0x92C0). The three
halfwords 0x0211, 0x0212, 0x1220 exactly match the iHDS catalog "Group C"
secret `021102121220` (RWDXRAY_IHDS_SAKEY_REPORT.md), with the firmware
storing them per-halfword little-endian as `11 02 12 02 20 12`.

The "Group A" bytes `001100121020` that appear in the `!` header of all
52 V850 EPS .rwd files in the iHDS dump are NOT the SA secret on V850 -
the V850 ECU uses firmware-embedded constants at 0x92C0 and the previously
inferred Group-A derivation was wrong. See SA_KEY_PYTHON_PREP.md for the
full reasoning chain.

Wire format (verified via disasm of 0xB30C byte-build loop and 0xAAEA seed
load):

    Request 0x27 0x01 (RequestSeed)   -> ECU responds with 2-byte seed
        Response payload: 0x67 0x01 SEED_HI SEED_LO
    Request 0x27 0x02 (SendKey)       -> Tester sends 2-byte key
        Request payload:  0x27 0x02 KEY_HI  KEY_LO

The seed and key are 2-byte big-endian on the UDS wire. Internally the
ECU stores both as 32-bit words in RAM, but the algorithm only operates
on the low 16 bits of the seed and the algorithm output's upper 16 bits
are always zero by construction (both XOR operands are < 0x10000). The
32-bit compare at 0xAAFA therefore reduces to a 16-bit compare in
practice. See V850_ALGORITHM_VERIFIED.md sections "Caller side" and
SA_KEY_PYTHON_PREP.md for the wire-format walkthrough.

Run `python flashing-2020accord/tva_sa_key.py` to execute _selfcheck().
"""

import struct

# ---- Verified V850 SA-key constants (firmware 0x92C0..0x92C5) ----

TVA_K0 = 0x0211   # addend     (firmware halfword at 0x92C0)
TVA_K1 = 0x0212   # multiplier (firmware halfword at 0x92C2)
TVA_K2 = 0x1220   # modulus    (firmware halfword at 0x92C4)

# Compact form of the three constants, big-endian, matching the iHDS
# catalog Group C secret string `021102121220`.
TVA_V850_SECRET = b'\x02\x11\x02\x12\x12\x20'

# Group A bytes that appear in the `!` header of all 52 V850 EPS .rwd
# files. NOT used as the SA secret on V850 - kept here only as a guard
# against re-introducing the prior (incorrect) inference that the header
# bytes drove the SA computation.
GROUP_A_HEADER_BYTES = b'\x00\x11\x00\x12\x10\x20'

# SH-2A family secret, kept for cross-family contrast in _selfcheck().
SH2A_SECRET = b'\x01\x11\x01\x12\x11\x20'


# ---- Core computation ----

def _compute_key16(seed16: int, k0: int = TVA_K0, k1: int = TVA_K1,
                   k2: int = TVA_K2) -> int:
    """Integer-domain implementation of the verified V850 algorithm.

    key16 = ((seed16 + k0) & 0xFFFF) XOR ((seed16 * k1) mod k2)

    Both XOR operands are guaranteed < 0x10000, so the result fits in
    16 bits and is correctly represented as a 32-bit word with the
    upper 16 bits zero (matching the firmware's `st.w r6, 0[r9]` write).
    """
    s = seed16 & 0xFFFF
    if k2 == 0:
        # Defensive: real firmware k2=0x1220, never zero. Mirror the
        # eps-update.py convention of treating 0 as a 16-bit modulus
        # to avoid a DivisionByZero on caller mistakes.
        k2 = 0x10000
    return ((s + k0) & 0xFFFF) ^ ((s * k1) % k2)


def calculate_tva_session_key(seed_bytes: bytes) -> bytes:
    """Compute the expected SA-key for a TVA EPS, given a 2-byte UDS seed.

    Input  : exactly 2 bytes, big-endian seed as received from the ECU
             (the payload following `0x67 0x01` in the SA response).
    Output : exactly 2 bytes, big-endian key to send as the payload
             following `0x27 0x02` in the SendKey request.

    Internally, the algorithm operates on a 16-bit seed and produces a
    16-bit key; this function deals exclusively in the wire format
    (2-byte BE). A 4-byte variant is available as
    `calculate_tva_session_key_4byte` for any caller that prefers the
    32-bit RAM-storage representation.
    """
    if len(seed_bytes) != 2:
        raise ValueError(
            f"TVA SA seed must be exactly 2 bytes on the UDS wire; "
            f"got {len(seed_bytes)} bytes ({seed_bytes!r})"
        )
    seed16 = struct.unpack('!H', seed_bytes)[0]
    key16 = _compute_key16(seed16)
    return struct.pack('!H', key16)


def calculate_tva_session_key_4byte(seed_bytes: bytes) -> bytes:
    """4-byte variant: accept/return 4-byte big-endian seed/key.

    Mirrors the RAM-storage representation the firmware uses internally
    (the seed slot at 0xFEDF40F8 is 4 bytes wide; the algorithm output
    is stored via `st.w` as 4 bytes). The upper 2 bytes of the seed are
    IGNORED by the algorithm (only the low 16 bits feed `zxh r6`), and
    the upper 2 bytes of the key are ALWAYS zero by construction.

    Provided for callers that want to match the RAM/comparison width
    even though the on-wire UDS payload is 2-byte. The 32-bit compare
    at 0xAAFA succeeds when the tester sends `00 00 KEY_HI KEY_LO`, but
    the byte-build loop at 0xB30C only reads 2 bytes (msg[2..3]) from
    the request, so the 4-byte case here is provided for parity with
    internal data structures rather than as the on-wire format.
    """
    if len(seed_bytes) != 4:
        raise ValueError(
            f"4-byte variant requires exactly 4 bytes; got {len(seed_bytes)}"
        )
    seed32 = struct.unpack('!I', seed_bytes)[0]
    key16 = _compute_key16(seed32 & 0xFFFF)
    # Upper 16 bits are always zero by algorithm construction.
    return struct.pack('!I', key16 & 0xFFFFFFFF)


# ---- Cross-family reference (for _selfcheck contrast) ----

def _calculate_sh2a_key(seed_bytes: bytes) -> bytes:
    """SH-2A universal algorithm, kept for cross-family validation only.

    Matches eps-update.py:45 for the SH-2A Civic/Clarity/CR-V/Insight
    family. NOT used for TVA - kept to demonstrate that the V850 result
    differs from the prior SH-2A-with-Group-A inference.
    """
    k0, k1, k2 = struct.unpack('!HHH', SH2A_SECRET)
    seed = struct.unpack('!H', seed_bytes)[0]
    if k2 == 0:
        k2 = 0x10000
    key = (seed + k0) ^ ((seed * k1) % k2)
    return struct.pack('!H', key & 0xFFFF)


def _calculate_group_a_inference(seed_bytes: bytes) -> bytes:
    """Prior (incorrect) inference: SH-2A-shape algorithm with the Group A
    bytes from the V850 `!` header. Kept ONLY to demonstrate that the
    verified algorithm produces a different key, so future agents do
    not silently regress to the Group-A path.
    """
    k0, k1, k2 = struct.unpack('!HHH', GROUP_A_HEADER_BYTES)
    seed = struct.unpack('!H', seed_bytes)[0]
    if k2 == 0:
        k2 = 0x10000
    key = (seed + k0) ^ ((seed * k1) % k2)
    return struct.pack('!H', key & 0xFFFF)


# ---- Self-check / test vectors ----

def _selfcheck():
    """Validate the implementation against hand-computed test vectors.

    All four primary vectors below are derived directly from the
    verified algorithm (V850_ALGORITHM_VERIFIED.md Table "Sample
    values"). Boundary cases 0x7FFF/0x8000 verify that no signed-vs-
    unsigned overflow creeps in (relevant because the underlying V850
    `divq` is signed, but the input range here is small enough that
    signed and unsigned mod give identical results).
    """
    # Primary vectors from V850_ALGORITHM_VERIFIED.md
    vectors = [
        (b'\x00\x00', b'\x02\x11'),  # seed=0 -> key=k0 (regression check)
        (b'\x12\x34', b'\x11\x6D'),
        (b'\xAB\xCD', b'\xA1\x54'),
        (b'\xFF\xFF', b'\x0E\x5E'),
    ]
    for seed, expected in vectors:
        got = calculate_tva_session_key(seed)
        assert got == expected, (
            f"TVA vector failed: seed=0x{seed.hex().upper()} "
            f"expected 0x{expected.hex().upper()} got 0x{got.hex().upper()}"
        )

    # Boundary cases - signed/unsigned safety
    k_7fff = calculate_tva_session_key(b'\x7F\xFF')
    k_8000 = calculate_tva_session_key(b'\x80\x00')
    assert k_7fff == b'\x8C\x3E', (
        f"boundary 0x7FFF failed: got 0x{k_7fff.hex().upper()}"
    )
    assert k_8000 == b'\x92\x51', (
        f"boundary 0x8000 failed: got 0x{k_8000.hex().upper()}"
    )

    # 4-byte variant parity
    k4 = calculate_tva_session_key_4byte(b'\x00\x00\x12\x34')
    assert k4 == b'\x00\x00\x11\x6D', (
        f"4-byte parity failed for seed 0x00001234: got 0x{k4.hex().upper()}"
    )
    # Upper bytes of 4-byte seed are ignored per algorithm
    k4_ignored = calculate_tva_session_key_4byte(b'\xDE\xAD\x12\x34')
    assert k4_ignored == b'\x00\x00\x11\x6D', (
        f"4-byte upper-bytes-ignored failed: got 0x{k4_ignored.hex().upper()}"
    )

    # Demonstrate the verified algorithm differs from the prior Group-A
    # inference at the same seed. If this assertion ever fires equal, a
    # regression has silently swapped constants.
    tva_1234 = calculate_tva_session_key(b'\x12\x34')
    group_a_1234 = _calculate_group_a_inference(b'\x12\x34')
    assert tva_1234 != group_a_1234, (
        "Verified V850 (Group C) key matches prior Group-A inference - "
        "constants regression suspected"
    )

    # And that it differs from the SH-2A family at the same seed.
    sh2a_1234 = _calculate_sh2a_key(b'\x12\x34')
    assert tva_1234 != sh2a_1234, (
        "Verified V850 (Group C) key matches SH-2A key - "
        "secret distinction lost"
    )

    zero_seed = b'\x00\x00'
    abcd_seed = b'\xAB\xCD'
    ffff_seed = b'\xFF\xFF'
    k_zero = calculate_tva_session_key(zero_seed).hex().upper()
    k_abcd = calculate_tva_session_key(abcd_seed).hex().upper()
    k_ffff = calculate_tva_session_key(ffff_seed).hex().upper()
    print(f"OK: TVA(0x0000) = 0x{k_zero}  (= k0)")
    print(f"OK: TVA(0x1234) = 0x{tva_1234.hex().upper()}")
    print(f"OK: TVA(0x7FFF) = 0x{k_7fff.hex().upper()}")
    print(f"OK: TVA(0x8000) = 0x{k_8000.hex().upper()}")
    print(f"OK: TVA(0xABCD) = 0x{k_abcd}")
    print(f"OK: TVA(0xFFFF) = 0x{k_ffff}")
    print(f"OK: 4-byte variant produces 0x{k4.hex().upper()} for seed 0x00001234")
    print(f"OK: Group-A inference (0x{group_a_1234.hex().upper()}) "
          f"differs from verified Group-C (0x{tva_1234.hex().upper()})")
    print(f"OK: SH-2A     (0x{sh2a_1234.hex().upper()}) "
          f"differs from verified Group-C (0x{tva_1234.hex().upper()})")
    print("OK: all V850 SA-key self-checks pass")


if __name__ == '__main__':
    _selfcheck()
