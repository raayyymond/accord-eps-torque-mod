"""Independent rev-2 rebuild from DESIGN rev2 s1.1 table. Verify old bytes, hashes, CRC, diff count, GATE1 scan."""
import hashlib, zlib, glob, time
t0=time.time()
P=glob.glob('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v298_*_plain_image.bin')[0]
v298=open(P,'rb').read()
b=bytearray(v298)

# ---- OLD bytes rev2 asserts (V298). (addr, expected_hex) from s1.1 table V298 column + hard-freeze region ----
old_assert = {
 0xC4C64:'0002',          # imm 512
 0xC4C6A:'206e2c01',      # movea 0x12c,r0,r13
 0xC4C6E:'ed41',          # cmp r13,r8
 0xC4C70:'d305',          # bnh C7A
 0xC4C72:'244fa0b0',      # ld.h -0x4f60[gp],r9
 0xC4C76:'3049',          # xor r16,r9
 0xC4C78:'d625',          # blt CC2
 0xC4C7A:'244f0096',      # ld.h -0x6a00,r9
 0xC4C7E:'e049',          # cmp r0,r9
 0xC4C80:'ae05',          # bge C84
 0xC4C82:'8049',          # subr r0,r9
 0xC4C84:'e447a395',      # ld.hu -0x6a5e,r8
 0xC4C88:'206e400b',      # movea 0xb40
 0xC4C8C:'ed41',          # cmp r13,r8
 0xC4C8E:'bb05',          # bh C94
 0xC4C90:'c44a',          # shl 4
 0xC4C92:'a505',          # br C96
 0xC4C94:'c64a',          # shl 6
 0xC4C96:'094ee204',      # addi 0x4e2
 0xC4C9A:'206e6605',      # movea 0x566
 0xC4C9E:'ed41',          # cmp r13,r8
 0xC4CA0:'eb05',          # bh CAC
 0xC4CA2:'206e0010',      # movea 0x1000
 0xC4CA6:'ed49',          # cmp r13,r9
 0xC4CA8:'ed4f364b',      # cmovh
 0x1310D:'41',
}
bad=[]
for a,h in old_assert.items():
    want=bytes.fromhex(h); got=bytes(v298[a:a+len(want)])
    if got!=want: bad.append((hex(a),h,got.hex()))
print('OLD-byte assertions that MISMATCH V298:', bad if bad else 'none (all %d match)'%len(old_assert))

# ---- NEW bytes rev2 (V299) from s1.1 table V299 rev2 column ----
patch = {
 0xC4C64:'cd04',          # imm 1229
 0xC4C6A:'244f0096',      # ld.h -0x6a00,r9
 0xC4C6E:'e081',          # cmp r0,r16
 0xC4C70:'ae05',          # bge C74
 0xC4C72:'8049',          # subr r0,r9
 0xC4C74:'e049',          # cmp r0,r9
 0xC4C76:'ae05',          # bge C7A
 0xC4C78:'004a',          # mov 0,r9
 0xC4C7A:'e447a395',      # ld.hu -0x6a5e,r8
 0xC4C7E:'206e400b',      # movea 0xb40
 0xC4C82:'ed41',          # cmp r13,r8
 0xC4C84:'9b15',          # bh CA6
 0xC4C86:'c44a',          # shl 4
 0xC4C88:'094ee204',      # addi 0x4e2
 0xC4C8C:'206e6605',      # movea 0x566
 0xC4C90:'ed41',          # cmp r13,r8
 0xC4C92:'cb05',          # bh C9A
 0xC4C94:'206e0010',      # movea 0x1000
 0xC4C98:'b505',          # br C9E
 0xC4C9A:'206e0018',      # movea 0x1800
 0xC4C9E:'ed49',          # cmp r13,r9
 0xC4CA0:'ed4f364b',      # cmovh
 0xC4CA4:'c505',          # br CAC
 0xC4CA6:'c64a',          # shl 6
 0xC4CA8:'094ee204',      # addi 0x4e2
 0x1310D:'42',
}
# apply
for a,h in patch.items():
    v=bytes.fromhex(h); b[a:a+len(v)]=v

# content-byte diffs in cave region [0xC4C00,0xC4D04) + F181
cave_diff=sum(1 for i in range(0xC4C00,0xC4D04) if b[i]!=v298[i])
f181_diff=sum(1 for i in (0x1310D,) if b[i]!=v298[i])
print('cave content bytes differing [0xC4C00,0xC4D04):',cave_diff)
print('F181 byte differing:',f181_diff)

# CRC trailer
b0,b1=0x13000,0xC4FFC
newc=zlib.crc32(bytes(b[b0:b1]))&0xFFFFFFFF
oldc=int.from_bytes(bytes(v298[b1:b1+4]),'little')
b[b1:b1+4]=newc.to_bytes(4,'little')
print('V298 trailer 0x%08X (%s) -> rev2 0x%08X (%s)'%(oldc, v298[b1:b1+4].hex(' '), newc, b[b1:b1+4].hex(' ')))
print('   spec rev2 trailer = 95 3b dd 70 ->', b[b1:b1+4].hex(' ')=='95 3b dd 70')
print('   V298 trailer should be f3 d8 7c 6b ->', v298[b1:b1+4].hex(' ')=='f3 d8 7c 6b')

csha=hashlib.sha256(bytes(b[0xC4C00:0xC4D04])).hexdigest()
isha=hashlib.sha256(bytes(b)).hexdigest()
print('cave sha  ',csha); print('  spec     e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608 ->', csha=='e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608')
print('image sha ',isha); print('  spec     30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08 ->', isha=='30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08')

tot=sum(1 for i in range(len(b)) if b[i]!=v298[i])
print('TOTAL diff bytes vs V298:',tot,'(spec: 67 = cave62+F181 1+trailer4)')
# save disasm-only scratch copy for Ghidra
outp='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/REFUTE_V299R2_DISASM_ONLY.bin'
import os; os.makedirs(os.path.dirname(outp),exist_ok=True)
open(outp,'wb').write(bytes(b))
print('scratch image written',outp)
print('wall %.2fs'%(time.time()-t0))
