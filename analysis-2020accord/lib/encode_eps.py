"""lib/encode_eps.py — Honda EPS .rwd encoder (round-trip companion to decode_eps.py).

Builds an x5a or x31 .rwd file from a payload, header set, and 3-key/3-op cipher.

Status (2026-05-23):
- x31 round-trips byte-identically on 9th-gen Accord (T2F, T3L), ILX (TV9).
  Same V850 family as the 2020 Accord TVA target.
- x5a round-trips byte-identically on SH-2A files (TG7 Pilot, T5N).
- The TVA-A160 source .rwd is not in this repo's branch; we cannot do a direct
  round-trip on it. The encoder is exercised against same-family siblings.

Usage:
    # Round-trip an existing .rwd (decode-then-encode, assert byte-equal):
    python lib/encode_eps.py --roundtrip <path.rwd[.gz]>

    # Build a new .rwd from a payload (advanced; see build_rwd_from_template):
    # see build_rwd_from_template() and the __main__ examples.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import gzip, struct, os, sys, itertools, operator, re, argparse
from binascii import a2b_hex, b2a_hex
from firmware_paths import CALIB_FILES

OPS = [operator.xor, operator.and_, operator.or_, operator.add,
       operator.sub, operator.mul, operator.floordiv, operator.mod]
SYM = ['^','&','|','+','-','*','//','%']

# ---------- cipher ----------

def build_decode_table(keys, ops):
    """Apply (((i op1 k1) op2 k2) op3 k3) & 0xFF for i in 0..255. Returns 256B
    table OR None if non-bijective / div-by-zero."""
    (k1,k2,k3) = keys
    (o1,o2,o3) = ops
    dec = bytearray(256); seen = set()
    for e in range(256):
        try: d = o3(o2(o1(e,k1),k2),k3) & 0xFF
        except ZeroDivisionError: return None
        dec[e] = d; seen.add(d)
    return bytes(dec) if len(seen) == 256 else None

def invert_table(dec):
    """Given a bijective 256B decode table, return its inverse (encode table)."""
    enc = bytearray(256)
    for plain in range(256):
        enc[dec[plain]] = plain
    return bytes(enc)

def crack_cipher(enc_blocks, keyvals, expected):
    """Same oracle as decode_eps.crack — find a (keys, ops) that decodes a block
    such that `expected` (a known plaintext substring, e.g. b'39990-TVA-A160')
    appears. Returns (decode_table, sym_str) or (None, None)."""
    if expected is None: return None, None
    for keys in set(itertools.permutations(keyvals)):
        for ops_idx in itertools.product(range(8), repeat=3):
            dec = build_decode_table(keys, [OPS[x] for x in ops_idx])
            if dec is None: continue
            if any(expected in blk.translate(dec) for blk in enc_blocks):
                sym = (f"((i {SYM[ops_idx[0]]} {keys[0]:#x}) "
                       f"{SYM[ops_idx[1]]} {keys[1]:#x}) "
                       f"{SYM[ops_idx[2]]} {keys[2]:#x}")
                return dec, sym
    return None, None

# ---------- x5a (SH-2A family) ----------
# Format: 5A 0D 0A | 6 headers in [count][len][bytes]... form | [start:u32 BE]
#         [length:u32 BE] | encrypted_payload | [file_checksum:u32 LE]
# file_checksum = sum(all_preceding_bytes) & 0xFFFFFFFF.

def parse_x5a(data):
    assert data[:3] == b'\x5A\x0D\x0A'
    i = 3; headers = []
    for h in range(6):
        cnt = data[i]; i += 1; vals = []
        for _ in range(cnt):
            ln = data[i]; i += 1; vals.append(data[i:i+ln]); i += ln
        headers.append(vals)
    start = struct.unpack('!I', data[i:i+4])[0]
    length = struct.unpack('!I', data[i+4:i+8])[0]
    i += 8
    payload = data[i:i+length]
    trailer = data[i+length:i+length+4]  # may be empty if file lacks checksum
    return {
        'headers': headers, 'start': start, 'length': length,
        'payload': payload, 'trailer': trailer,
    }

def build_x5a_header_bytes(headers):
    out = b'\x5A\x0D\x0A'
    for vals in headers:
        out += bytes([len(vals)])
        for v in vals:
            out += bytes([len(v)]) + v
    return out

def encode_x5a(headers, start, length, encrypted_payload):
    """Build a complete x5a .rwd. `encrypted_payload` MUST already be ciphered.
    The trailing 4-byte file checksum (LE sum of all preceding bytes) is appended."""
    hdr = build_x5a_header_bytes(headers)
    body = hdr + struct.pack('!I', start) + struct.pack('!I', length) + encrypted_payload
    checksum = sum(body) & 0xFFFFFFFF
    return body + struct.pack('<I', checksum)

# ---------- x31 (V850 family) ----------
# Format: 31 0D 0A | 6 headers each `[tag_byte 0D 0A] value1 0D 0A value2 0D 0A ... [tag_byte 0D 0A]`
# | payload of 130-byte chunks `[addr_hi][addr_mid][data:128B]` (addr = hi<<12 | mid<<4)
# | [file_checksum:u32 LE]
# Header tags observed (in order): # ? / ! & %
#   #: typically [\x00]
#   ?: typically [b'A1']
#   /: supported part numbers ASCII (one per supported version)
#   !: security keys ASCII (one per supported version)
#   &: encryption key ASCII hex (e.g. b'BF109E' -> cipher keyvals 0xBF, 0x10, 0x9E)
#   %: CAN address significant byte ASCII hex (e.g. b'80' -> 0x80 in 0x18DA__F1)

def parse_x31(data):
    assert data[:3] == b'\x31\x0D\x0A'
    i = 3; headers = []
    for h in range(6):
        tag = data[i:i+3]; i += 3  # `[tag_byte 0D 0A]`
        vals = []
        while data[i:i+3] != tag:
            end = data.find(b'\x0D\x0A', i); vals.append(data[i:end]); i = end + 2
        i += 3
        headers.append((tag[0:1], vals))
    payload_start = i
    payload_chunks = data[i:-4]
    trailer = data[-4:]
    # Parse 130B chunks -> blocks
    chunk_size = 130; data_size = 128
    blocks = []; encs = []
    expected_addr = None; cur_start = None; cur_data = b''
    for j in range(0, len(payload_chunks) - chunk_size + 1, chunk_size):
        addr = (payload_chunks[j] << 12) | (payload_chunks[j+1] << 4)
        if addr != expected_addr:
            if cur_data:
                blocks.append({'start': cur_start, 'length': len(cur_data)})
                encs.append(cur_data)
            cur_start = addr; cur_data = b''
        cur_data += payload_chunks[j+2:j+2+data_size]
        expected_addr = addr + data_size
    if cur_data:
        blocks.append({'start': cur_start, 'length': len(cur_data)})
        encs.append(cur_data)
    # Extract cipher key from '&' header
    key = None
    for hid, vals in headers:
        if hid == b'&': key = a2b_hex(vals[0])
    return {
        'headers': headers, 'key': list(key) if key else None,
        'blocks': blocks, 'encs': encs,
        'payload_start': payload_start, 'payload_chunks': payload_chunks,
        'trailer': trailer,
    }

def build_x31_header_bytes(headers):
    """`headers` is a list of (tag_byte, [value_bytes,...]) tuples."""
    out = b'\x31\x0D\x0A'
    for tag, vals in headers:
        out += tag + b'\x0D\x0A'
        for v in vals:
            out += v + b'\x0D\x0A'
        out += tag + b'\x0D\x0A'
    return out

def build_x31_payload_chunks(blocks, encs):
    """`blocks` is a list of {start, length} dicts; `encs` is the parallel list of
    already-ciphered block bytes. Each block is split into 128B sub-chunks; each
    sub-chunk is prefixed by `[addr_hi:u8][addr_mid:u8]` where the 20-bit address
    is `(hi<<12)|(mid<<4)`. Block length must be a multiple of 128."""
    out = bytearray()
    for blk, enc in zip(blocks, encs):
        assert blk['length'] == len(enc), f"block length mismatch: {blk['length']} vs {len(enc)}"
        assert blk['length'] % 128 == 0, f"block length 0x{blk['length']:X} not multiple of 128"
        for k in range(0, len(enc), 128):
            addr = blk['start'] + k
            hi = (addr >> 12) & 0xFF
            mid = (addr >> 4) & 0xFF
            out += bytes([hi, mid]) + enc[k:k+128]
    return bytes(out)

def encode_x31(headers, blocks, encs):
    """Build a complete x31 .rwd. `encs` MUST already be ciphered."""
    hdr = build_x31_header_bytes(headers)
    payload = build_x31_payload_chunks(blocks, encs)
    body = hdr + payload
    checksum = sum(body) & 0xFFFFFFFF
    return body + struct.pack('<I', checksum)

# ---------- round-trip ----------

def roundtrip(path, expected_part_override=None):
    """Decode then re-encode; assert byte-equal."""
    raw = open(path, 'rb').read()
    if path.endswith('.gz'): raw = gzip.decompress(raw)
    fmt = raw[0:1]
    name = os.path.basename(path)
    print(f"-> {name}  len=0x{len(raw):X}  fmt={fmt!r}")
    exp_part = expected_part_override
    if exp_part is None:
        m = re.search(r'39990[-]?([A-Za-z0-9]{3})[-_]?([A-Za-z0-9]{4})', name)
        exp_part = f"39990-{m.group(1).upper()}-{m.group(2).upper()}".encode('ascii') if m else None
    if fmt == b'Z':
        info = parse_x5a(raw)
        # Pull keyvals out of headers[5][0] (the encryption-key header)
        keyvals = list(info['headers'][5][0])
        dec_table, sym = crack_cipher([info['payload']], keyvals, exp_part)
        if dec_table is None:
            print(f"   FAILED to crack cipher (expected={exp_part!r})"); return False
        enc_table = invert_table(dec_table)
        decoded = info['payload'].translate(dec_table)
        re_encoded = decoded.translate(enc_table)
        if re_encoded != info['payload']:
            print("   FAILED: payload re-encryption is not byte-identical"); return False
        rebuilt = encode_x5a(info['headers'], info['start'], info['length'], re_encoded)
        ok = rebuilt == raw
        print(f"   cipher: {sym}")
        print(f"   round-trip byte-equal: {ok}  (rebuilt_len=0x{len(rebuilt):X}, source_len=0x{len(raw):X})")
        if not ok:
            for k in range(min(len(rebuilt), len(raw))):
                if rebuilt[k] != raw[k]:
                    print(f"   first diff at offset 0x{k:X}: src=0x{raw[k]:02X} reb=0x{rebuilt[k]:02X}")
                    break
        return ok
    elif fmt == b'1':
        info = parse_x31(raw)
        dec_table, sym = crack_cipher(info['encs'], info['key'], exp_part)
        if dec_table is None:
            print(f"   FAILED to crack cipher (key={info['key']}, expected={exp_part!r})")
            return False
        enc_table = invert_table(dec_table)
        decoded_blocks = [blk.translate(dec_table) for blk in info['encs']]
        re_encoded_blocks = [d.translate(enc_table) for d in decoded_blocks]
        for re_enc, orig in zip(re_encoded_blocks, info['encs']):
            if re_enc != orig:
                print("   FAILED: block re-encryption is not byte-identical"); return False
        rebuilt = encode_x31(info['headers'], info['blocks'], re_encoded_blocks)
        ok = rebuilt == raw
        print(f"   cipher: {sym}")
        print(f"   round-trip byte-equal: {ok}  (rebuilt_len=0x{len(rebuilt):X}, source_len=0x{len(raw):X})")
        if not ok:
            for k in range(min(len(rebuilt), len(raw))):
                if rebuilt[k] != raw[k]:
                    print(f"   first diff at offset 0x{k:X}: src=0x{raw[k]:02X} reb=0x{rebuilt[k]:02X}")
                    break
        return ok
    else:
        print(f"   UNSUPPORTED format {fmt!r}"); return False

# ---------- template-based new-build helper ----------

def build_rwd_from_template(template_path, patched_blocks, out_path=None,
                            expected_part_override=None):
    """Take an existing .rwd as template; replace its decoded blocks with
    `patched_blocks` (dict {block_index: new_plain_bytes} or list parallel to
    template blocks); re-encipher with the SAME cipher; emit a byte-faithful
    new .rwd preserving all headers, addresses, and lengths.

    This is the path you'd use to make a TVA-A160 modified build from the stock
    .rwd plus a patched code.bin slice.
    """
    raw = open(template_path, 'rb').read()
    if template_path.endswith('.gz'): raw = gzip.decompress(raw)
    fmt = raw[0:1]
    name = os.path.basename(template_path)
    exp_part = expected_part_override
    if exp_part is None:
        m = re.search(r'39990[-]?([A-Za-z0-9]{3})[-_]?([A-Za-z0-9]{4})', name)
        exp_part = f"39990-{m.group(1).upper()}-{m.group(2).upper()}".encode('ascii') if m else None
    if fmt == b'Z':
        info = parse_x5a(raw)
        keyvals = list(info['headers'][5][0])
        dec_table, sym = crack_cipher([info['payload']], keyvals, exp_part)
        if dec_table is None: raise RuntimeError("cipher crack failed")
        enc_table = invert_table(dec_table)
        plain = info['payload'].translate(dec_table)
        if isinstance(patched_blocks, dict):
            new_plain = bytearray(plain)
            for blk_idx, new_bytes in patched_blocks.items():
                assert blk_idx == 0, "x5a is single-blob"
                assert len(new_bytes) == len(plain)
                new_plain[:] = new_bytes
            plain = bytes(new_plain)
        elif isinstance(patched_blocks, list):
            assert len(patched_blocks) == 1
            plain = patched_blocks[0]
        new_payload = plain.translate(enc_table)
        rwd = encode_x5a(info['headers'], info['start'], len(new_payload), new_payload)
    elif fmt == b'1':
        info = parse_x31(raw)
        dec_table, sym = crack_cipher(info['encs'], info['key'], exp_part)
        if dec_table is None: raise RuntimeError("cipher crack failed")
        enc_table = invert_table(dec_table)
        plain_blocks = [b.translate(dec_table) for b in info['encs']]
        if isinstance(patched_blocks, dict):
            for blk_idx, new_bytes in patched_blocks.items():
                assert len(new_bytes) == len(plain_blocks[blk_idx]), \
                    f"block {blk_idx} length mismatch: {len(new_bytes)} vs {len(plain_blocks[blk_idx])}"
                plain_blocks[blk_idx] = new_bytes
        elif isinstance(patched_blocks, list):
            assert len(patched_blocks) == len(plain_blocks)
            for i, nb in enumerate(patched_blocks):
                assert len(nb) == len(plain_blocks[i])
                plain_blocks[i] = nb
        enc_blocks_new = [b.translate(enc_table) for b in plain_blocks]
        rwd = encode_x31(info['headers'], info['blocks'], enc_blocks_new)
    else:
        raise RuntimeError(f"Unsupported format {fmt!r}")
    if out_path:
        with open(out_path, 'wb') as f: f.write(rwd)
        print(f"wrote {out_path}  ({len(rwd)} bytes)  cipher={sym}")
    return rwd

# ---------- CLI ----------

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--roundtrip", action="append", default=[], help="path to .rwd[.gz] to round-trip")
    p.add_argument("--default-tests", action="store_true",
                   help=f"run round-trip on the default V850 + SH-2A test files in {CALIB_FILES}")
    args = p.parse_args()
    files = list(args.roundtrip)
    if args.default_tests or not files:
        files += [
            str(CALIB_FILES / "39990-T2F-A210.rwd.gz"),
            str(CALIB_FILES / "39990-T3L-A210.rwd.gz"),
            str(CALIB_FILES / "39990-TV9-A910.rwd.gz"),
            str(CALIB_FILES / "39990-TG7-A030-M1.rwd.gz"),
            str(CALIB_FILES / "39990-T5N-M020-M1.rwd.gz"),
        ]
    passed = failed = 0
    for f in files:
        if not os.path.exists(f):
            print(f"-> {f}  MISSING"); failed += 1; continue
        ok = roundtrip(f)
        passed += int(ok); failed += int(not ok)
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
