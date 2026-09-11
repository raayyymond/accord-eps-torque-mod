# -*- coding: utf-8 -*-
"""sr_routes.py -- route id -> EPS firmware build, and a COARSE arm for the invariance test.

Sources, in order of authority:
  1. explicit `("<full route id>", "<build>")` tuples in the kit's extract/analysis scripts
     (these already carry the 2026-09-03 re-attributions -- e.g. r32/r33 are V280 rev 2, NOT V278);
  2. plurality of `V\\d+` tokens within +-260 chars of the route id across docs/ + scripts.

🛑 KEYED ON THE FULL ROUTE ID.  The dongle's counter RESET, so 0x1b, 0x24, 0x31, 0x35, 0x37,
0x3a, 0x59 and 0x5e each name TWO DIFFERENT ROUTES on disk.
Routes with no attribution anywhere are "unknown" and are reported as their own arm, never merged.
"""
BUILD = {
    "75604b0a432fdc89_00000013--f484e75b00": "V52c",
    "75604b0a432fdc89_0000001a--a4ef772958": None,
    "75604b0a432fdc89_0000001b--d2abf1af1c": None,
    "75604b0a432fdc89_0000001b--d7c81cf9b5": "V107",
    "75604b0a432fdc89_0000001c--ade8fd5b4a": None,
    "75604b0a432fdc89_0000001e--28ef595061": "V107",
    "75604b0a432fdc89_00000021--489af1e5b7": "V108",
    "75604b0a432fdc89_00000022--00f57626e0": "V112",
    "75604b0a432fdc89_00000023--fc5f268959": "V112",
    "75604b0a432fdc89_00000024--6f4943e0a6": "V122",
    "75604b0a432fdc89_00000024--bc45926e80": "V56",
    "75604b0a432fdc89_00000028--66ab5a2233": None,
    "75604b0a432fdc89_00000029--47bc9c9d99": None,
    "75604b0a432fdc89_0000002b--604bd0e8f8": None,
    "75604b0a432fdc89_0000002b--7926e8f7e5": "V67",
    "75604b0a432fdc89_0000002c--eb219f392c": "V59",
    "75604b0a432fdc89_0000002d--10714693cd": None,
    "75604b0a432fdc89_0000002e--855ecfcf30": "V276",
    "75604b0a432fdc89_00000031--0441e00d2b": "V59",
    "75604b0a432fdc89_00000031--a680e9b2ac": "V278r3",
    "75604b0a432fdc89_00000032--33a5dbbcb3": "V280r2",
    "75604b0a432fdc89_00000033--1948a2c354": "V280r2",
    "75604b0a432fdc89_00000034--e2d2d5381f": "V280r2",
    "75604b0a432fdc89_00000035--580292087d": "V281r3",
    "75604b0a432fdc89_00000035--77808fe7ce": "V64",
    "75604b0a432fdc89_00000036--f4be1a18e9": "V283",
    "75604b0a432fdc89_00000037--4a79da5d18": "V283",
    "75604b0a432fdc89_00000037--6231e33f3d": "V62",
    "75604b0a432fdc89_00000038--f77bddf4bd": "V283",
    "75604b0a432fdc89_00000039--f56039af87": "V282",
    "75604b0a432fdc89_0000003a--283a39a1d6": "V282",
    "75604b0a432fdc89_0000003a--4e55c1e0f4": "V65",
    "75604b0a432fdc89_0000003b--a4a7f4dbf1": None,
    "75604b0a432fdc89_0000003c--927965c2b4": "V282",
    "75604b0a432fdc89_00000047--3e0b6134c0": "V67",
    "75604b0a432fdc89_0000004a--346bf31d97": "V67",
    "75604b0a432fdc89_0000004c--d0ea3c14b4": "V68",
    "75604b0a432fdc89_0000004e--11f5b814b6": "V68",
    "75604b0a432fdc89_0000004f--61171e660d": "V69",
    "75604b0a432fdc89_00000050--50f2e00e8f": "V70",
    "75604b0a432fdc89_00000054--4e67ae1164": "V71b",
    "75604b0a432fdc89_00000058--1d1005262f": "V71c",
    "75604b0a432fdc89_00000059--9070b9dcee": "V72",
    "75604b0a432fdc89_00000059--ad34044e59": None,
    "75604b0a432fdc89_0000005a--2d32bec040": "V73",
    "75604b0a432fdc89_0000005e--03a9714d78": "V288r2",
    "75604b0a432fdc89_0000005e--857d0bd164": "V75",
    "75604b0a432fdc89_00000061--3b8f2f9278": "V74",
    "75604b0a432fdc89_00000062--1c7daa54e8": "V289r1",
    "75604b0a432fdc89_00000063--1d4b188022": "V289r1",
    "75604b0a432fdc89_00000065--ae43aa0f27": "V76",
    "75604b0a432fdc89_00000066--276b942769": "V80",
    "75604b0a432fdc89_00000067--9b3ebbe218": "V81",
    "75604b0a432fdc89_00000068--0b7efae911": "V84",
    "75604b0a432fdc89_0000006d--5d03a5adb4": "V84",
    "75604b0a432fdc89_0000006e--649c462a6e": "V85",
    "75604b0a432fdc89_0000006f--80ca318af4": "V86b",
    "75604b0a432fdc89_00000070--66544f819d": "V86b",
    "75604b0a432fdc89_00000071--ac50da2a6a": "V87",
    "75604b0a432fdc89_00000073--9380c74d52": "V88",
    "75604b0a432fdc89_00000074--ef6c21294f": None,
    "75604b0a432fdc89_00000075--9bbcb3f7da": "V90",
    "75604b0a432fdc89_00000076--c81e964e05": "V89",
    "75604b0a432fdc89_00000077--7411859c54": "V90",
    "75604b0a432fdc89_00000078--93548c06b3": "V91",
    "75604b0a432fdc89_00000079--cb7538ffae": "V91",
    "75604b0a432fdc89_0000007d--83a5c80392": "V94",
    "75604b0a432fdc89_0000007e--e5f2d1465f": "V96",
    "75604b0a432fdc89_0000007f--2bb30756e7": "V96",
    "75604b0a432fdc89_00000080--6c8b103892": "V97",
    "75604b0a432fdc89_00000081--c7103d2cb4": "V98",
    "75604b0a432fdc89_00000082--e30d55731b": "V99",
    "75604b0a432fdc89_00000085--cad692c3d3": "V100",
    "75604b0a432fdc89_00000095--6d7c6deef5": "V101",
    "75604b0a432fdc89_00000096--57f5183b32": "V102",
    "75604b0a432fdc89_00000097--489d7896b3": "stock",
    "75604b0a432fdc89_0000009e--54bb0788af": "V103",
    "75604b0a432fdc89_000000a4--bdd0c0aa4e": "V104",
    "75604b0a432fdc89_000000a5--1419044ddf": "V105",
    "75604b0a432fdc89_000000a6--78293a259e": "V106",
}


def arm(route):
    b = BUILD.get(route)
    if b is None:
        return "unknown"
    if b == "stock":
        return "stock"
    n = int("".join(ch for ch in b if ch.isdigit()))
    if n < 80:
        return "V52-V76"
    if n < 200:
        return "V80-V122"
    if n < 288:
        return "V276-V283"
    return "V288-V289"
