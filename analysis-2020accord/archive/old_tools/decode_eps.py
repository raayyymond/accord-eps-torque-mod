import gzip, struct, itertools, operator, re, glob, os, sys
from binascii import a2b_hex

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import ARCHIVE_DIR, CALIB_FILES

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
    return list(key),[{'start':start,'length':length}],[data[i:i+length]]

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
    return list(key),blocks,encs

def crack(enc_blocks, keyvals, expected):
    """Strict oracle: decoded firmware must contain the exact dashed part number.
    Uses bytes.translate (C-fast) so we can scan whole blocks."""
    matches=[]
    for keys in set(itertools.permutations(keyvals)):
        for ops_idx in itertools.product(range(8),repeat=3):
            dec=get_decoder(keys,[OPS[x] for x in ops_idx])
            if dec is None: continue
            table=bytes(dec)
            hit=any(expected in blk.translate(table) for blk in enc_blocks)
            if hit:
                symstr=f"((i {SYM[ops_idx[0]]} {keys[0]:#x}) {SYM[ops_idx[1]]} {keys[1]:#x}) {SYM[ops_idx[2]]} {keys[2]:#x}"
                matches.append((table,symstr))
    if not matches: return None,None,None,0
    table,sym=matches[0]
    decoded=[blk.translate(table) for blk in enc_blocks]
    return table,sym,decoded,len(matches)

def expected_part(path):
    base=os.path.basename(path)
    m=re.search(r'39990[-]?([A-Za-z0-9]{3})[-_]?([A-Za-z0-9]{4})', base)
    if not m: return None
    return f"39990-{m.group(1).upper()}-{m.group(2).upper()}".encode('ascii')

def v850_score(decoded_blocks, blocks):
    idx=max(range(len(decoded_blocks)), key=lambda k:len(decoded_blocks[k]))
    d=decoded_blocks[idx]; start=blocks[idx]['start']
    cnt=0
    for j in range(0,len(d)-1,2):
        if d[j]==0x80 and d[j+1]==0x07: cnt+=1
    perkb=cnt/(len(d)/1024) if d else 0
    return cnt,perkb,start,len(d),idx

def partstr(decoded_blocks):
    for d in decoded_blocks:
        m=re.search(rb'39990[\x20-\x7e]{0,12}', d)
        if m:
            return m.group().decode('ascii','replace')
    return "?"

FILES=[
 (str(CALIB_FILES / "39990-TG7-A030-M1.rwd.gz"),"TG7 Pilot"),
 (str(CALIB_FILES / "39990-T9A-P040-M1.rwd.gz"),"T9A City"),
 (str(CALIB_FILES / "39990-T9A-T030-M1.rwd.gz"),"T9A City"),
 (str(CALIB_FILES / "39990-T9L-M030-M1.rwd.gz"),"T9L"),
 (str(CALIB_FILES / "39990TY2_A050M1__A1705631.rwd.gz"),"TY2"),
 (str(CALIB_FILES / "39990-T5N-M020-M1.rwd.gz"),"T5N"),
 (str(CALIB_FILES / "39990-T5R-A030-M1.rwd.gz"),"T5R"),
 (str(CALIB_FILES / "39990-TAR-U020-M1.rwd.gz"),"TAR"),
 (str(CALIB_FILES / "39990-T7T-M020-M1.rwd.gz"),"T7T"),
 (str(CALIB_FILES / "39990-T7W-A020-M1.rwd.gz"),"T7W"),
 (str(CALIB_FILES / "39990-T3Z-A010.rwd.gz"),"T3Z"),
 (str(CALIB_FILES / "39990THX_A130M1__A1807204.rwd.gz"),"THX"),
 (str(CALIB_FILES / "39990T38_A050M1__A2303876.rwd.gz"),"T38 (2023)"),
 (str(CALIB_FILES / "39990T39_A140M1__A2303858.rwd.gz"),"T39 (2023)"),
 (str(CALIB_FILES / "39990T43_J030M1__A2303874.rwd.gz"),"T43 (2023)"),
 (str(CALIB_FILES / "39990T60_J040M1__A2303869.rwd.gz"),"T60 (2023)"),
 (str(CALIB_FILES / "39990-TX4-A010.rwd.gz"),"TX4"),
 (str(CALIB_FILES / "39990-TZ5-A010.rwd.gz"),"TZ5"),
 (str(CALIB_FILES / "39990-TT1-A310.rwd.gz"),"TT1"),
 (str(CALIB_FILES / "39990-TS8-A310.rwd.gz"),"TS8"),
 (str(ARCHIVE_DIR / "39990-TBA-C120-stock.rwd"),"TBA Civic C120 (SH2A ctrl)"),
 (str(CALIB_FILES / "39990-TV9-A910.rwd.gz"),"TV9 ILX (SH2A ctrl)"),
 (str(CALIB_FILES / "39990-T2F-A210.rwd.gz"),"T2F 9thgen Accord"),
 (str(CALIB_FILES / "39990-T3L-A210.rwd.gz"),"T3L 9thgen Accord"),
]

print(f"{'label':28} {'fmt':4} {'key':10} {'blkstart':>9} {'blklen':>9} {'end':>9} {'80_07':>6} {'/KB':>7}  part")
print("-"*112)
rows=[]
for path,label in FILES:
    if not os.path.exists(path):
        print(f"{label:28} MISSING {path}"); continue
    raw=open(path,'rb').read()
    if path.endswith('.gz'): raw=gzip.decompress(raw)
    fmt=raw[0:1]
    try:
        if fmt==b'Z': key,blocks,encs=parse_x5a(raw); fmtn='x5a'
        elif fmt==b'1': key,blocks,encs=parse_x31(raw); fmtn='x31'
        else:
            print(f"{label:28} fmt={fmt} UNSUPPORTED"); continue
    except Exception as e:
        print(f"{label:28} PARSE-ERR {e}"); continue
    exp=expected_part(path)
    dec,sym,decoded,nmatch=crack(encs,key,exp)
    keyhex=''.join(f'{k:02x}' for k in key)
    if dec is None:
        print(f"{label:28} {fmtn:4} {keyhex:10} -- NOT cracked (expected {exp})"); continue
    cnt,perkb,bstart,blen,bi=v850_score(decoded,blocks)
    end=bstart+blen
    part=partstr(decoded)
    nblk=len(blocks)
    amb="" if nmatch==1 else f" [!{nmatch} decoders match]"
    print(f"{label:28} {fmtn:4} {keyhex:10} {bstart:9X} {blen:9X} {end:9X} {cnt:6} {perkb:7.2f}  {part}  (blk={nblk}){amb}")
    rows.append((label,fmtn,keyhex,bstart,blen,end,cnt,perkb,part,sym,nblk))
print()
print("Cipher (sym) per cracked file:")
for r in rows:
    print(f"  {r[0]:28} key={r[2]}  {r[9]}")
