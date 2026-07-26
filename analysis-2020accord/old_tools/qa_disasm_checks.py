"""Disassembly-based QA for boot path and 0x8000 routine reach claims.

Verifies:
  - Claim 2: 0x8000 routine reads from 0x13010, 0x9060, 0xA6000 (W1 extension)
            AND the known 0x14000 (verified).
  - Claim 3: Only one xref to 0x14000, from 0x801c, READ (not call/jmp).
  - Claim 6: Boot path 0x24 -> 0x80 -> conditional 0x8000 -> (*0x238)()
"""
import sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from disasm_v850 import rz_disasm, rz_disasm_range, resolve_imm_pairs, format_lines

print("=" * 78)
print("CLAIM 2: 0x8000 routine reaches 0x13010, 0x9060, 0xA6000, 0x14000")
print("=" * 78)

# Disassemble 0x8000 to 0x8400 (1 KB)
insns = rz_disasm_range(0x8000, 0x8400)
resolve_imm_pairs(insns)

# Find all resolved addresses
resolved = {}
for ins in insns:
    if 'resolved_addr' in ins:
        ra = ins['resolved_addr']
        resolved.setdefault(ra, []).append((ins['offset'], ins['opcode']))

print(f"\n  resolved address-pair targets found in 0x8000..0x8400:")
for addr in sorted(resolved.keys()):
    sites = resolved[addr]
    print(f"    0x{addr:08X}  ({len(sites)} sites)")
    for off, op in sites[:3]:
        print(f"      0x{off:06X}: {op}")

# Specifically check the four target addresses
targets = [0x13010, 0x9060, 0xA6000, 0x14000]
print(f"\n  Target check:")
for t in targets:
    found = t in resolved
    print(f"    0x{t:06X}: {'FOUND' if found else 'NOT FOUND'}", end='')
    if found:
        sites = resolved[t]
        print(f"  (at {[f'0x{s[0]:06X}' for s in sites]})")
    else:
        print()


print("\n" + "=" * 78)
print("CLAIM 3: Only one xref to 0x14000, from 0x801c, READ")
print("=" * 78)

# We need to scan the ENTIRE image for any movhi+load/store/movea pair that
# resolves to 0x14000. The disasm_v850.resolve_imm_pairs is local-window only.
# Let's do a full-image scan in chunks of 0x4000 and aggregate.

print("\n  Scanning entire 1MB image for movhi-pair targets == 0x14000 ...")

# Disassemble in chunks
CHUNK = 0x4000
xref_sites = []  # list of (offset, opcode, resolved_addr, partner_off)

for start in range(0, 0x100000, CHUNK):
    end = min(start + CHUNK + 0x40, 0x100000)  # small overlap for split pairs
    try:
        insns = rz_disasm_range(start, end)
        resolve_imm_pairs(insns)
        for ins in insns:
            if ins.get('resolved_addr') == 0x14000:
                # Only count instructions actually inside [start, start+CHUNK) to avoid double-count
                if start <= ins['offset'] < start + CHUNK:
                    xref_sites.append((ins['offset'], ins['opcode'], ins.get('resolved_partner')))
    except Exception as e:
        print(f"    [chunk 0x{start:X} error: {e}]")

print(f"  Found {len(xref_sites)} instructions referencing 0x14000:")
for off, op, partner in xref_sites:
    print(f"    0x{off:06X}: {op}  (partner @ 0x{partner:06X})" if partner is not None else f"    0x{off:06X}: {op}")

# Now: are any of them CALL/JMP rather than READ/STORE?
print(f"\n  Categorization (call/jmp vs read/store/movea):")
for off, op, partner in xref_sites:
    op_low = op.lower()
    is_call_or_jmp = any(op_low.startswith(p) for p in ('jr', 'jmp', 'jarl', 'b ', 'br ', 'call'))
    is_read = op_low.startswith('ld.')
    is_write = op_low.startswith('st.')
    is_movea = op_low.startswith('movea')
    is_movhi = op_low.startswith('movhi')
    cat = 'CALL/JMP' if is_call_or_jmp else (
        'READ' if is_read else (
            'WRITE' if is_write else (
                'MOVEA' if is_movea else (
                    'MOVHI(addr-build)' if is_movhi else 'OTHER'))))
    print(f"    0x{off:06X}: [{cat:18s}] {op}")


print("\n" + "=" * 78)
print("CLAIM 6: Boot path 0x24 -> 0x80 -> conditional 0x8000 -> (*0x238)()")
print("=" * 78)

# 0x24 -> 0x80
print("\n  -- 0x24 disasm --")
insns = rz_disasm(0x24, n=4)
resolve_imm_pairs(insns)
print(format_lines(insns))
# Check the jr target
jr_targets = [ins.get('jump') for ins in insns
              if ins.get('opcode', '').strip().startswith('jr')]
print(f"  jr targets: {[hex(t) if t else None for t in jr_targets]}")
print(f"  -> Calls 0x80? {0x80 in jr_targets}")

# 0x80 — disassemble enough to see the conditional call to 0x8000 and indirect via 0x238
print("\n  -- 0x80 (startup) disasm, deep enough to find 0x8000 call site --")
insns80 = rz_disasm(0x80, n=200)
resolve_imm_pairs(insns80)
# Look for any jarl/jalr to 0x8000 or use of 0x8000 as a pointer
print("  Lines with 0x8000 or jarl referencing 0x8000:")
for ins in insns80:
    op = ins.get('opcode', '')
    jmp = ins.get('jump')
    ra = ins.get('resolved_addr')
    if jmp == 0x8000 or ra == 0x8000 or '0x8000' in op:
        print(f"    0x{ins['offset']:06X}: {op}  jump=0x{jmp:X}" if jmp is not None else f"    0x{ins['offset']:06X}: {op}")

# Look for the indirect call site that uses 0x238
print("\n  Lines that resolve to 0x238 or use r6 == 0x238:")
for ins in insns80:
    if ins.get('resolved_addr') == 0x238 or '0x238' in ins.get('opcode', ''):
        print(f"    0x{ins['offset']:06X}: {ins['opcode']}")

# Look for any 'jarl [reg]' patterns (V850 indirect call) AFTER the 0x8000 call
print("\n  Indirect-call-like instructions (jarl/jmp [reg]) in 0x80 range:")
for ins in insns80:
    op = ins.get('opcode', '').strip()
    if re.match(r'^(jarl|jmp)\s+\[', op) or 'jarl' in op or op.startswith('jmp '):
        print(f"    0x{ins['offset']:06X}: {op}")
