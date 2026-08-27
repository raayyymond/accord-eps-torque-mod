"""extract_eps_bounds.py — decode every Honda EPS (39990-*) .rwd in the
configured calibration directory,
extract the firmware payload .bin, and tabulate the payload start/end so we can
find the V850 EPS begin/end pattern and apply it to code.bin.

Reuses the proven parser/cipher in lib/encode_eps.py (round-trip byte-equal on
T2F/T3L/TV9 x31 and TG7/T5N x5a).

Usage:
    python extract_eps_bounds.py            # metadata table only (no files written)
    python extract_eps_bounds.py --write    # also write extracted .bin payloads
"""
import gzip, os, re, sys, glob, struct
ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES, OTHER_BINS
import encode_eps as E

RWD_DIR = CALIB_FILES
OUT_DIR = OTHER_BINS

def part_from_name(name):
    m = re.search(r'39990[-_]?([A-Za-z0-9]{3})[-_]?([A-Za-z0-9]{4})', name)
    if not m: return None
    return f"39990-{m.group(1).upper()}-{m.group(2).upper()}".encode('ascii')

def isa_signature(img):
    """Return (jr0780_per_kb, sh2a_4F22, sh2a_000B) over programmed bytes — cheap
    V850-vs-SH2A discriminator (see reference_pilot_tg7_is_v850)."""
    n = len(img)
    jr = sum(1 for i in range(0, n-1, 2) if img[i]==0x80 and img[i+1]==0x07)
    f22 = sum(1 for i in range(0, n-1, 2) if img[i]==0x4F and img[i+1]==0x22)  # BE sts.l pr,@-r15
    rts = sum(1 for i in range(0, n-1, 2) if img[i]==0x00 and img[i+1]==0x0B)  # BE rts
    prog = sum(1 for b in img if b != 0xFF) or 1
    return (prog/ max(jr,1)), f22, rts, prog

def decode_file(path):
    raw = open(path,'rb').read()
    if path.endswith('.gz'): raw = gzip.decompress(raw)
    fmt = raw[0:1]
    name = os.path.basename(path)
    exp = part_from_name(name)
    rec = {'name': name, 'fmt': fmt.decode('latin1'), 'rwd_len': len(raw)}
    if fmt == b'1':  # x31, V850 family
        info = E.parse_x31(raw)
        dec, sym = E.crack_cipher(info['encs'], info['key'], exp)
        if dec is None:
            rec['error'] = f'cipher-crack-failed key={info["key"]} exp={exp}'; return rec, None
        plain_blocks = [b.translate(dec) for b in info['encs']]
        blocks = info['blocks']
        parts = [v for hid,vals in info['headers'] if hid==b'/' for v in vals]
        rec['cipher'] = sym
        rec['parts'] = [p.decode('latin1') for p in parts]
        rec['blocks'] = [(b['start'], b['length']) for b in blocks]
    elif fmt == b'Z':  # x5a — usually SH-2A, but TG7 is V850 (see memory)
        info = E.parse_x5a(raw)
        keyvals = list(info['headers'][5][0])
        dec, sym = E.crack_cipher([info['payload']], keyvals, exp)
        if dec is None:
            rec['error'] = f'cipher-crack-failed exp={exp}'; return rec, None
        plain = info['payload'].translate(dec)
        plain_blocks = [plain]
        blocks = [{'start': info['start'], 'length': info['length']}]
        ver = [v.rstrip(b'\x00').decode('latin1') for v in info['headers'][3]]
        rec['cipher'] = sym
        rec['parts'] = ver
        rec['blocks'] = [(info['start'], info['length'])]
    else:
        rec['error'] = f'unknown-fmt {fmt!r}'; return rec, None

    # reconstruct a flat image over [min_start, max_end) filled with 0xFF
    starts = [b['start'] for b in blocks]; ends = [b['start']+b['length'] for b in blocks]
    lo, hi = min(starts), max(ends)
    img = bytearray(b'\xFF' * (hi - lo))
    for b, pb in zip(blocks, plain_blocks):
        img[b['start']-lo : b['start']-lo+len(pb)] = pb
    rec['start'] = lo; rec['end'] = hi; rec['span'] = hi-lo
    rec['payload_bytes'] = sum(b['length'] for b in blocks)
    rec['nblocks'] = len(blocks)
    # peek first 16 bytes of programmed payload for a start-signature
    rec['head16'] = img[:16].hex()
    sig = isa_signature(bytes(img))
    rec['isa'] = 'V850' if (sig[1]==0 and sig[2]<=2) else 'SH2A?'
    rec['jr_per'] = round(sig[0],1); rec['sh2a_4F22'] = sig[1]; rec['sh2a_000B'] = sig[2]
    return rec, bytes(img), lo

def main():
    write = '--write' in sys.argv
    files = sorted(str(p) for p in RWD_DIR.glob('39990*.rwd*'))
    if write: os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for f in files:
        try:
            res = decode_file(f)
        except Exception as e:
            print(f"ERR {os.path.basename(f)}: {e}"); continue
        rec = res[0]
        if 'error' in rec:
            print(f"SKIP {rec['name']}: {rec['error']}"); continue
        rows.append(rec)
        if write and len(res) == 3:
            _, img, lo = res
            out = os.path.join(OUT_DIR, rec['name'].split('.rwd')[0] + f'.payload_0x{lo:X}.bin')
            open(out,'wb').write(img)
    # table sorted by start
    rows.sort(key=lambda r:(r['fmt'], r['start']))
    print(f"\n{'name':28} fmt {'start':>8} {'end':>8} {'span':>8} {'pay':>8} blk isa  head16")
    for r in rows:
        print(f"{r['name'][:28]:28} {r['fmt']:>3} 0x{r['start']:06X} 0x{r['end']:06X} "
              f"0x{r['span']:06X} 0x{r['payload_bytes']:06X} {r['nblocks']:>3} {r['isa']:5} {r['head16']}")
    # start-address histogram
    from collections import Counter
    print("\nstart-address histogram:", dict(Counter(r['start'] for r in rows)))
    print("end-address histogram:   ", dict(Counter(r['end'] for r in rows)))
    print(f"\n{len(rows)} files decoded OK; written={'yes->'+OUT_DIR if write else 'no'}")

if __name__ == '__main__':
    main()
