"""Quick probe — for each candidate .rwd, report decoded format/cipher/headers."""
import gzip, struct, os, sys, itertools, operator, re
from binascii import a2b_hex

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES

OPS=[operator.xor,operator.and_,operator.or_,operator.add,operator.sub,operator.mul,operator.floordiv,operator.mod]
SYM=['^','&','|','+','-','*','//','%']

def get_decoder(keys, ops):
    (k1,k2,k3)=keys; (o1,o2,o3)=ops
    dec=bytearray(256); seen=set()
    for e in range(256):
        try: d=o3(o2(o1(e,k1),k2),k3)&0xFF
        except ZeroDivisionError: return None
        dec[e]=d; seen.add(d)
    return dec if len(seen)==256 else None

def parse_x5a(data):
    i=3; headers=[]
    for h in range(6):
        cnt=data[i]; i+=1; vals=[]
        for _ in range(cnt):
            ln=data[i]; i+=1; vals.append(data[i:i+ln]); i+=ln
        headers.append(vals)
    key=headers[5][0]
    start=struct.unpack('!I',data[i:i+4])[0]
    length=struct.unpack('!I',data[i+4:i+8])[0]
    i+=8
    return list(key),[{'start':start,'length':length}],[data[i:i+length]],headers,i

def parse_x31(data):
    i=3; headers=[]
    for h in range(6):
        hp=data[i:i+3]; i+=3; vals=[]
        while data[i:i+3]!=hp:
            end=data.find(b'\x0d\x0a',i); vals.append(data[i:end]); i=end+2
        i+=3; headers.append((hp[0:1],vals))
    key=None
    for hid,vals in headers:
        if hid==b'&': key=a2b_hex(vals[0])
    fw=data[i:-4]; chunk=130; ds=128
    blocks=[]; encs=[]; an=0; bs=0; bd=b''
    for j in range(0,len(fw)-chunk+1,chunk):
        addr=(fw[j]<<12)|(fw[j+1]<<4)
        if addr!=an:
            if bd: blocks.append({'start':bs,'length':len(bd)}); encs.append(bd)
            bs=addr; bd=b''
        bd+=fw[j+2:j+2+ds]; an=addr+ds
    if bd: blocks.append({'start':bs,'length':len(bd)}); encs.append(bd)
    return list(key),blocks,encs,headers,i

def crack(enc_blocks, keyvals, expected):
    if expected is None: return None,None,None,0
    for keys in set(itertools.permutations(keyvals)):
        for ops_idx in itertools.product(range(8),repeat=3):
            dec=get_decoder(keys,[OPS[x] for x in ops_idx])
            if dec is None: continue
            table=bytes(dec)
            if any(expected in blk.translate(table) for blk in enc_blocks):
                symstr=f"((i {SYM[ops_idx[0]]} {keys[0]:#x}) {SYM[ops_idx[1]]} {keys[1]:#x}) {SYM[ops_idx[2]]} {keys[2]:#x}"
                return table,symstr,[blk.translate(table) for blk in enc_blocks],1
    return None,None,None,0

def expected_part(path):
    base=os.path.basename(path)
    m=re.search(r'39990[-]?([A-Za-z0-9]{3})[-_]?([A-Za-z0-9]{4})', base)
    if not m: return None
    return f"39990-{m.group(1).upper()}-{m.group(2).upper()}".encode('ascii')


CANDS = [
    str(CALIB_FILES / "39990-T2F-A210.rwd.gz"),
    str(CALIB_FILES / "39990-T3L-A210.rwd.gz"),
    str(CALIB_FILES / "39990-TV9-A910.rwd.gz"),
    str(CALIB_FILES / "39990-TG7-A030-M1.rwd.gz"),
    str(CALIB_FILES / "39990-T5N-M020-M1.rwd.gz"),
]

def hx(b): return b.hex(' ')

def main():
    for path in CANDS:
        if not os.path.exists(path):
            print(f"MISSING: {path}"); continue
        raw = open(path,'rb').read()
        if path.endswith('.gz'): raw = gzip.decompress(raw)
        fmt = raw[0:1]
        print("="*72)
        print(f"{os.path.basename(path)}  len={len(raw)}  fmt={fmt!r}")
        if fmt == b'Z':
            key, blocks, encs, hdrs, hdr_end = parse_x5a(raw)
            exp = expected_part(path)
            dec_table, sym, decoded, n = crack(encs, key, exp)
            print(f"  cipher: {sym}  (matches={n})")
        elif fmt == b'1':
            key, blocks, encs, hdrs, hdr_end = parse_x31(raw)
            exp = expected_part(path)
            dec_table, sym, decoded, n = crack(encs, key, exp)
            print(f"  cipher: {sym}  (matches={n})  blocks={len(blocks)}")

if __name__ == "__main__":
    main()
