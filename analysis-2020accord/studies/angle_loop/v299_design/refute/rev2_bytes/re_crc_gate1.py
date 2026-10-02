"""CRC chain + bootloader replay on rebuilt rev2 image; GATE1 st.* scan of the cave; decode derivation."""
import sys, time
sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/lib')
from verify_bootloader_crc import walk, walk_all_blocks
t0=time.time()
img=open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/REFUTE_V299R2_DISASM_ONLY.bin','rb').read()
print('image len 0x%X'%len(img))
bl=walk(img,label='rev2'); full=walk_all_blocks(img,label='rev2')
print('BOOTLOADER walk fails=%d (expect 0, 49 blks)   FULL chain fails=%d (expect 0, 50 blks)'%(bl,full))

# GATE 1: scan cave [0xC4C00,0xC4D04) for any store. V850 store opcodes:
# Format VII st.b/st.h/st.w have opcode bits; simplest robust: decode via known forms.
# sb: 0b111010 (0x3A<<10)? Use the pattern: major opcode in bits 10..5 of first hw for Format VII memory ops.
# st.b opcode=0b111010, st.h=0b111011(.w via bit), ... Instead: list every 16/32-bit word and flag mnemonics starting 'st'
# We rely on Ghidra for authoritative decode; here flag candidate store encodings by the Format VII signature.
# Format VII (load/store disp16): word1 bits15-11=reg2, bits10-5=opcode, bits4-0=reg1; st forms opcode:
#  st.b=0x3A, st.h=0x3B(with bit0 of disp), st.w=0x3B, sst.* short forms differ.
# Simpler & safe: scan for opcodes in {0x3A,0x3B,0x3C,0x3D} in the op field AND reg2!=0 patterns is noisy.
# Authoritative GATE1 is Ghidra. Here just dump the words for the human/Ghidra cross-check.
cave=img[0xC4C00:0xC4D04]
print('cave bytes (260):',cave.hex())
print('wall %.2fs'%(time.time()-t0))
