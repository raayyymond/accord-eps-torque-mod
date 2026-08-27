"""Replay the bootloader's CheckProgrammingDependencies CRC walk (FUN 0xB006).

Reverse-engineered from code.bin via radare2 (v850):
  - FUN_0xB006 verifies a region by walking a backward linked list of CRC blocks.
  - Region = [region_start, region_start+region_len).  END = region_start+region_len.
  - First block bounds come from the trailer at END:
        start_page = u16le(END-8); num_pages = u16le(END-6)
        block_start = start_page << 12
        block_len   = (num_pages << 12) - 4
  - For each block: crc32(img[block_start : block_start+block_len]) must equal
        u32le(img[block_start + block_len])      (the stored trailer word)
  - Termination / linkage (in FUN_0xB006 order):
        if block_start == region_start: PASS (done)
        elif block_start == 0xC6000:    bridge -> main block
                                        block_start = region_start (0x13000)
                                        block_len   = 0xB1FFC   (hard-coded in BL)
                                        (stored CRC then at 0x13000+0xB1FFC = 0xC4FFC)
        else: advance via linked list using THIS block's start page fields:
                next_start_page = u16le(block_start-8)
                next_num_pages  = u16le(block_start-6)
  - CRC primitive FUN_0xAE4C = HW DCRA unit @0xFF836020 = Ethernet CRC32 = zlib.crc32.

===================================================================================================
THE 0xC6000 BRIDGE IS REAL.  VERIFIED 2026-07-19 AT THE BYTE LEVEL.  DO NOT "FIX" IT AGAIN.
===================================================================================================
Earlier on 2026-07-19 the lead removed this bridge, believing it to be a mis-decode by radare2's
default (wrong) v850 plugin.  THAT WAS AN ERROR and it has been reverted.  The bridge is genuinely
present in the bootloader.  Decompile of FUN_0000b006 in code.bin:

    if (puVar3 == &LAB_000c6000) { puVar3 = &DAT_00013000; puVar2 = &DAT_000b1ffc; }
    else { puVar2 = ...(puVar3-6)*0x1000-4; puVar3 = ...(puVar3-8)<<0xc; }

and the raw constants in code.bin, independently confirmed:

    0xB070 movea 0x6000 / 0xB072 movhi 0x000C  -> the literal 0xC6000 compared against
    0xB07A         0x3000 / 0xB07C        0x0001  -> 0x13000
    0xB080         0x1FFC / 0xB082        0x000B  -> 0xB1FFC

So the bootloader really does jump 0xC6000 -> main and never dereferences the link fields that
would lead it to [0xC5000, 0xC5FFC).  walk() below replays that faithfully, bridge included.

===================================================================================================
BUT [0xC5000, 0xC5FFC) IS STILL A REAL BLOCK WITH A REAL, MAINTAINED CRC
===================================================================================================
Skipped by this routine does NOT mean nonexistent.  The block is self-describing exactly like every
other one (0xC5FF8 = 0x00C5 start_page, 0xC5FFA = 0x0001 num_pages) and its stored CRC32 at 0xC5FFC
is CORRECT in stock, V31, V37 and V38.  Something maintains it; what checks it is UNRESOLVED.

Following the linked list faithfully (no bridge) yields 50 blocks, all passing on every historical
image.  The bootloader's own walk covers 49 of them.  The difference is exactly [0xC5000,0xC5FFC).

    walk()            <- replays the BOOTLOADER.  49 blocks.  Use this to predict UDS NRC 0x72.
    walk_all_blocks() <- follows the stored linked list.  50 blocks.  Use this as a HYGIENE check:
                         any block we write into should stay internally consistent whether or not
                         the bootloader happens to look at it.

V40 wrote the motor-rate cap tables into [0xC5000,0xC5FFC) and left its CRC stale.  walk() passes
that image 49/49 and so did the flasher's dependency check; walk_all_blocks() fails it at exactly
that block.  V40 also faulted at ignition.  Whether those two facts are causally linked is NOT
established -- the only checker located so far (FUN_0000b006) is UDS-session-only and its failure
path ends in NRC 0x72 with no DTC and no motor-off.  Keep the CRC correct regardless: it costs four
bytes and it is the difference between "known consistent" and "unknown".
"""
import sys, zlib

def u16(b, o): return b[o] | (b[o+1] << 8)
def u32(b, o): return b[o] | (b[o+1] << 8) | (b[o+2] << 16) | (b[o+3] << 24)

def _blocks(img, region_start, region_len, bridge):
    """Yield (block_start, block_end) in chain order.  bridge=True replays the bootloader."""
    END = region_start + region_len
    bstart = u16(img, END-8) << 12
    blen   = (u16(img, END-6) << 12) - 4
    bridged = False
    seen = 0
    while True:
        if bstart + blen + 4 > len(img) or bstart < 0:
            yield ("OOB", bstart, blen); return
        yield (bstart, blen)
        seen += 1
        if bstart == region_start: return
        if bridge and bstart == 0xC6000 and not bridged:
            bridged = True
            bstart, blen = region_start, 0xB1FFC     # hard-coded in BL; VERIFIED, see docstring
            continue
        nsp  = u16(img, bstart-8)
        nnpg = u16(img, bstart-6)
        nbstart = nsp << 12
        if nbstart == bstart: return
        bstart, blen = nbstart, (nnpg << 12) - 4
        if seen > 200: return


def _run(img, region_start, region_len, label, bridge, kind):
    END = region_start + region_len
    print(f"\n=== {kind} {label}: region [0x{region_start:X}, 0x{END:X}) ===")
    seen = fails = 0
    for item in _blocks(img, region_start, region_len, bridge):
        if item[0] == "OOB":
            print(f"  [STOP] block 0x{item[1]:X} len 0x{item[2]:X} out of image bounds"); break
        bstart, blen = item
        crc    = zlib.crc32(img[bstart:bstart+blen]) & 0xFFFFFFFF
        stored = u32(img, bstart+blen)
        ok = (crc == stored)
        seen += 1
        if not ok: fails += 1
        print(f"  blk#{seen:2d} [0x{bstart:06X}, 0x{bstart+blen:06X})  "
              f"calc=0x{crc:08X} stored=0x{stored:08X}  {'OK ' if ok else '*** MISMATCH ***'}")
    print(f"  result: {seen} block(s) checked, {fails} mismatch(es) -> "
          f"{'PASS' if fails==0 else 'FAIL'}")
    return fails


def walk(img, region_start=0x13000, region_len=0xED000, label=""):
    """Faithful replay of the bootloader's FUN_0xB006, INCLUDING the verified 0xC6000 bridge.

    49 blocks. This is what predicts the UDS CheckProgrammingDependencies result (NRC 0x72).
    It does NOT cover [0xC5000,0xC5FFC) -- by design, in the firmware itself.
    """
    return _run(img, region_start, region_len, label, bridge=True, kind="verify BL walk")


def walk_all_blocks(img, region_start=0x13000, region_len=0xED000, label=""):
    """Follow the stored linked list with no bridge: 50 blocks, including [0xC5000,0xC5FFC).

    Hygiene check, NOT a bootloader replay. Use it so a build can never again leave a stale CRC in
    a block merely because the bootloader declines to look at that block.
    """
    return _run(img, region_start, region_len, label, bridge=False, kind="verify FULL chain")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "code.bin"
    with open(path, "rb") as f:
        img = f.read()
    print(f"loaded {path}: 0x{len(img):X} bytes")
    bl = walk(img, label=path)
    full = walk_all_blocks(img, label=path)
    print(f"\nsummary: bootloader walk {bl} fail(s), full chain {full} fail(s)")
    if full and not bl:
        print("  -> a block the BOOTLOADER SKIPS has a stale CRC. Not necessarily fatal, but it")
        print("     means an image was written without keeping its blocks self-consistent.")
