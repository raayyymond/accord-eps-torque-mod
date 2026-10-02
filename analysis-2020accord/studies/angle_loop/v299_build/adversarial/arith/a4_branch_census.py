"""ADV-arithmetic V299, step 4: whole-image census of Format-V jr/jarl targets into the cave [0xC4C00, 0xC4D04) and of short
bcond targets into the re-laid span [0xC4C6A, 0xC4CAC) from outside it. Positive control: the hook jarl @0x29D76 -> 0xC4C00."""
import numpy as np, glob, time
t0 = time.time()
img = open(glob.glob(r'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v299_*A16B_plain_image.bin')[0], 'rb').read()
for base in (0, 1):   # instructions are halfword aligned; scan the even alignment (base 0) - odd is not a valid pc
    pass
h = np.frombuffer(img, dtype='<u2').astype(np.int64)
hw1 = h[:-1]; hw2 = h[1:]; pc = np.arange(len(hw1)) * 2
op = (hw1 >> 5) & 0x3F
isV = ((op == 0x3C) | (op == 0x3D)) & ((hw2 & 1) == 0)
d = ((hw1 & 0x3F) << 16) | hw2; d = np.where(d & 0x200000, d - 0x400000, d)
tgt = pc + d
hit = isV & (tgt >= 0xC4C00) & (tgt < 0xC4D04)
print('Format-V targets into the cave:', [(hex(p), hex(t), 'jarl' if (h1 >> 11) else 'jr') for p, t, h1 in zip(pc[hit], tgt[hit], hw1[hit])])
# bcond (Format III) from anywhere into the span, from outside the span
isB = (hw1 & 0x0780) == 0x0580
db = (((hw1 >> 11) << 4) | (((hw1 >> 4) & 7) << 1)); db = np.where(db & 0x100, db - 0x200, db)
tb = pc + db
hitB = isB & (tb >= 0xC4C6A) & (tb < 0xC4CAC)
print('bcond into span:', [(hex(p), hex(t)) for p, t in zip(pc[hitB], tb[hitB])])
print('  of which from OUTSIDE the span:', [(hex(p), hex(t)) for p, t in zip(pc[hitB], tb[hitB]) if not (0xC4C6A <= p < 0xC4CAC)])
print('wall %.2f s' % (time.time() - t0))
