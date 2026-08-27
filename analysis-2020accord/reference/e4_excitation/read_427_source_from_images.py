import glob,os,struct
root=r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord"
for f in sorted(glob.glob(root+"/_v*_plain_image.bin")):
    b=open(f,'rb').read()
    if len(b)<0x55E20: continue
    d=struct.unpack_from('<h',b,0x55DF2)[0]
    d2=d & ~1
    inst=struct.unpack_from('<H',b,0x55E10)[0]
    raw=b[0x55DF2:0x55DF4].hex()
    raw2=b[0x55E10:0x55E12].hex()
    name=os.path.basename(f)
    print("%-16s 0x55DF2=%s -> gp%+d (gp-0x%X)   0x55E10=%s" % (name.split('_')[1], raw, d2, -d2 if d2<0 else d2, raw2))
