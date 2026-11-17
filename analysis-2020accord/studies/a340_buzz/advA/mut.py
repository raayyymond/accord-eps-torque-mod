import sys,subprocess,re,os
src=open("builds/a340/build_v300_a340.py",encoding="utf8").read()
MARK="    # ---- [9] CRC ----"
assert MARK in src
M={
"M1_dampaxis_row0_to_rev3":"    struct.pack_into('<3h', code, 0xD7A5C, -29490,-17202,-16000)\n",
"M2_alpha2_14":"    code[0xC40D4]=14\n",
"M3_baseassist_page_0xCE100":"    code[0xCE100]^=1\n",
"M4_keytable_0xCD010":"    code[0xCD010]^=1\n",
"M5_bootloader_0x100":"    code[0x100]^=1\n",
"M6_row1_one_byte_0xD7A6E":"    code[0xD7A6E]^=0x10\n",
"M7_cave_byte_0xC4C10":"    code[0xC4C10]^=1\n",
"M8_untouched_0xE0000":"    code[0xE0000]^=1\n",
"M9_mask_byte_0xC6D28_to_0":"    code[0xC6D28]=0\n",
"M10_gain_cell_0xC648A":"    code[0xC648A]^=1\n",
"M11_dampaxis_X_knot_0xD7A56":"    code[0xD7A56]^=1\n",
}
for name,ins in M.items():
    s=src.replace(MARK,ins+MARK,1)
    p=f"analysis-2020accord/_scratch/out/a340_buzz/advA/mut_{name}.py".replace("analysis-2020accord/","")
    open(p,"w",encoding="utf8").write(s)
    r=subprocess.run([sys.executable,p],capture_output=True,text=True,encoding="utf8",errors="replace",env=os.environ)
    fails=[l.strip()[:150] for l in r.stdout.splitlines() if "[FAIL]" in l]
    nonsha=[f for f in fails if "image sha frozen" not in f]
    tail=[l for l in r.stdout.splitlines() if "assertions" in l or "FAIL(S)" in l]
    print(name,"rc",r.returncode,"nfail",len(fails),"caught_by_substantive",len(nonsha))
    for f in nonsha[:3]: print("    ",f)
    if r.returncode and not fails: print("   ERR",r.stderr[-300:])
