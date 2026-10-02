"""ADV interlocks-gates V298 register dataflow over FUN_00028ea6 + cave, from Ghidra's own per-instruction
register IN/OUT objects on MY fresh import of the BUILT image. Input: regs_28ea6_v298.tsv (DumpRegsIG.java).
Computes: (A) live-in of the skip epilogue 0x2A164; (B) the hook-return live set the cave must preserve;
(C) reaching defs of r25 and r14 at the hook; (D) every register the cave 0xC4C00..0xC4CDA writes."""
import collections
TSV = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/angle_loop/adv-interlocks-gates/regs_28ea6_v298.tsv"
I = collections.OrderedDict()
for line in open(TSV):
    p = line.rstrip("\n").split("\t")
    a = int(p[0], 16)
    I[a] = dict(txt=p[1], ft=p[2],
                flows=[int(x, 16) for x in p[3].split(",") if x],
                fall=int(p[4], 16) if p[4] else None,
                IN=set(x for x in p[5][3:].split(",") if x) - {"PSW"},
                OUT=set(x for x in p[6][4:].split(",") if x) - {"PSW"})
CS = {"r1"} | {f"r{i}" for i in range(6, 20)} | {"lp"}   # V850 caller-saved (conservative CALL def set)
HOOK, CAVE, JMPR6, RET = 0x29D76, 0xC4C00, 0xC4CD8, 0x29D7A
def succ(a):
    d = I[a]; t = d["txt"]
    if a == HOOK: return [CAVE]
    if a == JMPR6: return [RET]
    if t.startswith("dispose"): return []
    if d["ft"] == "UNCONDITIONAL_CALL": return [d["fall"]]
    if d["ft"] in ("UNCONDITIONAL_JUMP", "CALL_TERMINATOR"): return d["flows"]
    if d["ft"] == "CONDITIONAL_JUMP": return d["flows"] + [d["fall"]]
    return [d["fall"]] if d["fall"] is not None else []
def defs(a):
    d = I[a]
    return (d["OUT"] | CS) if (d["ft"] == "UNCONDITIONAL_CALL" and a != HOOK) else d["OUT"]
def uses(a):
    return {"sp"} if I[a]["txt"].startswith("dispose") else I[a]["IN"]
pred = collections.defaultdict(set)
for a in I:
    for s in succ(a):
        assert s in I, (hex(a), s)
        pred[s].add(a)
def liveness(nodes):
    live = {a: set() for a in nodes}
    ch = True
    while ch:
        ch = False
        for a in sorted(nodes, reverse=True):
            out = set()
            for s in succ(a):
                if s in live: out |= live[s]
            new = uses(a) | (out - defs(a))
            if new != live[a]: live[a] = new; ch = True
    return live
def subgraph(start):
    seen = set(); st = [start]
    while st:
        x = st.pop()
        if x not in seen: seen.add(x); st += succ(x)
    return seen
# (A) skip epilogue live-in
epi = subgraph(0x2A164); liveA = liveness(epi)
print("(A) skip epilogue 0x2A164 live-in :", sorted(liveA[0x2A164]))
for r in sorted(liveA[0x2A164]):
    rd = [a for a in sorted(epi) if r in uses(a)]
    print(f"    {r}: first read {hex(rd[0]) if rd else '--'}")
# (B) hook-return live set: what must survive the cave. Full-function liveness, read at RET and the freeze/cam jr 0x29D7E
full = set(I); liveB = liveness(full)
print("(B) live-in at RET 0x29D7A      :", sorted(liveB[RET]))
print("    live-in at 0x29D7E (frz/cam):", sorted(liveB[0x29D7E]))
# (C) reaching defs of a register at an address
def reach_defs(reg, target):
    OUT = {a: set() for a in I}; ENTRY = 0x28EA6; ch = True
    while ch:
        ch = False
        for a in I:
            i = set()
            if a == ENTRY: i = {"ENTRY"}
            for p in pred[a]: i |= OUT[p]
            o = {hex(a)} if reg in defs(a) else set(i)
            if o != OUT[a]: OUT[a] = o; ch = True
    i = set()
    if target == ENTRY: i = {"ENTRY"}
    for p in pred[target]: i |= OUT[p]
    return i
print("(C) r25 reaching defs at hook   :", sorted(reach_defs("r25", HOOK)))
print("    r14 reaching defs at hook   :", sorted(reach_defs("r14", HOOK)))
# (D) cave writes
caveW = collections.OrderedDict()
for a in I:
    if CAVE <= a < 0xC4CDA:
        for r in defs(a): caveW.setdefault(r, []).append(hex(a))
print("(D) cave writes (reg: sites):")
for r, s in caveW.items():
    print(f"    {r}: {s}")
# cross-check: does the cave write any reg that is live at RET or 0x29D7E but NOT written by stock hook epilogue?
live_ret = liveB[RET] | liveB[0x29D7E]
print("(D') cave-written regs that are live at a return point:",
      sorted(set(caveW) & live_ret), " -- these must be re-set on the taken path before return")

# (E) op-skip liveness: reaching defs of each epilogue live-in register at the THREE entries to 0x2A164.
# If the op-skip (0xC4C14) presents the same defs as Honda's own A2/B2 skips (0x29A5C/0x29A64), it is safe.
print()
print("(E) reaching defs of epilogue live-ins at the three 0x2A164 entries:")
entries = {"A2(0x29A5C)": 0x29A5C, "B2(0x29A64)": 0x29A64, "opskip(0xC4C14)": 0xC4C14}
for reg in ["r11", "r14", "r15", "r20"]:
    row = {}
    for nm, ad in entries.items():
        row[nm] = sorted(reach_defs(reg, ad))
    same = (row["A2(0x29A5C)"] == row["opskip(0xC4C14)"])
    print(f"    {reg}: " + " | ".join(f"{nm}={row[nm]}" for nm in entries) + f"   opskip==A2? {same}")
# (F) first writer of r26 after the hook return, and whether OPH 0x29EE0 is the consumer
print()
print("(F) r26 after hook: writers/readers between 0x29D7A and 0x29F00:")
for a in sorted(I):
    if 0x29D7A <= a <= 0x29F00:
        if "r26" in defs(a): print(f"    WRITE r26 @ {hex(a)}  {I[a]['txt']}")
        if "r26" in uses(a): print(f"    READ  r26 @ {hex(a)}  {I[a]['txt']}")
