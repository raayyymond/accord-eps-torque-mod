# -*- coding: utf-8 -*-
"""Read the cumulative non-stock delta for the V290 close-out artifact DIRECTLY FROM THE IMAGES.
stock = the true stock dump (stock_fw_dump/code.bin), V282 and V289 plain images.  Raw little-endian byte reads;
no build-script constants.  Output: analysis-2020accord/_scratch/out/v290_closeout_delta.json
Run: python v290_closeout_delta_from_images.py   (ACCORD_FIRMWARE_ROOT honoured)"""
import os, sys, json, hashlib, struct
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(KIT, "_scratch", "out", "v290_closeout_delta.json")
IMG = {
 "stock": ROOT + "stock_fw_dump/code.bin",
 "V282":  ROOT + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
 "V289":  ROOT + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
B = {k: open(v, "rb").read() for k, v in IMG.items()}
H = {k: hashlib.sha256(v).hexdigest() for k, v in B.items()}
def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]
def u8(b, a): return b[a]
def f32(b, a): return struct.unpack_from("<f", b, a)[0]
def hx(b, a, n): return b[a:a+n].hex()

# scalar cells: (address, reader, what it physically is, what it does to the car, introducing build)
CELLS = [
 ("0xC6CD0", s16, "private forward LKAS gain (Q15, /32768)", "the 6x forward gain; single largest authority multiplier on the LKAS path", "V57 (5346 from V102)"),
 ("0xC646C", u16, "shared sensor scale (stock gain source)", "the cell the forward gain read from before 0x2A1F0 repointed it", "V38 touched, restored"),
 ("0x2A1F0", u16, "displacement of the forward-gain load", "repoints the forward path off 0xC646C onto the private 0xC6CD0", "V57, restored V81"),
 ("0xC61B2", u16, "forward tracking clamp (+)", "tracks the 6x gain so the clamp does not bind before the gain does", "V102"),
 ("0xC61B4", u16, "forward output clamp T", "output torque clamp after the gain", "V38 2048, V101 4096, V102 3072"),
 ("0xC61B6", u16, "D-term clamp", "never moved on the flight line", "-"),
 ("0xC61BC", u16, "P clamp", "never moved", "-"),
 ("0xC61BE", u16, "PID sum clamp S (also the V289 notch output clamp)", "never moved", "-"),
 ("0xC62E6", s16, "LKAS PID feedback saturation clamp (x256)", "PID sees 6x more feedback before saturating", "V276 15360; V280 46080"),
 ("0xC63E6", u16, "Ki", "integral gain, ships at zero", "-"),
 ("0xC63E8", s16, "fb lag pole a (two-sample sum)", "feedback filter pole: 923 = 16.5 Hz, 875 = 25 Hz", "V289"),
 ("0xC63EA", u16, "fb lag pole b", "keeps DC 2b/(1024-a) = 30.89 while the pole moves", "V289"),
 ("0xC63EC", u16, "output lag pole a (5.05 Hz)", "never moved", "-"),
 ("0xC63EE", u16, "output lag pole b", "never moved", "-"),
 ("0xC6446", u16, "r24 engaged rate-lane gain arm (Lever B)", "x10 stock on the 4-tap bar-torque derivative when engaged", "V67; 5244 from V88/V104"),
 ("0x3AA96", u8,  "r24/r26 gate byte", "C5 = dead gate (gp-0x683c), FB = STEER_CONTROL_ACTIVE (gp-0x6806): makes Lever B live", "V67; FB from V104"),
 ("0xC649B", u8,  "biquad enable cal", "with the 0x35A08 repoint, arms Honda's 55 Hz notch engaged-only", "V103"),
 ("0xC62EA", u16, "low-speed steer lockout threshold", "320 = 5 km/h; 0 disables the lockout, LKAS keeps authority at creep", "V53, restored V81"),
 ("0xC674E", s16, "EME soft-limit +A (int16)", "Excessive-Motor-Effort interlock ceiling x5", "V25 to V38"),
 ("0xC6750", s16, "EME soft-limit +B", "same interlock family", "V25 to V38"),
 ("0xC675A", s16, "EME soft-limit -A", "same", "V25 to V38"),
 ("0xC675C", s16, "EME soft-limit -B", "same", "V25 to V38"),
 ("0xC6768", u16, "EME ramp knot 0", "same interlock family", "V31 to V38"),
 ("0xC676A", u16, "EME ramp knot 1", "same", "V31 to V38"),
 ("0xC676C", u16, "EME ramp knot 2", "same", "V31 to V38"),
 ("0xC6598", f32, "EME float mirror", "float twin of the int quad; the lockstep monitor compares them", "V29 to V38"),
 ("0xC659C", f32, "EME float mirror", "", "V29 to V38"),
 ("0xC65AC", f32, "EME float mirror", "", "V29 to V38"),
 ("0xC65B0", f32, "EME float mirror", "", "V29 to V38"),
 ("0xC65C4", f32, "EME float mirror", "", "V29 to V38"),
 ("0xC65C8", f32, "EME float mirror", "", "V29 to V38"),
 ("0xC65CC", f32, "EME float mirror", "", "V29 to V38"),
 ("0xC40BC", u16, "Coulomb-relay knee", "relay saturates later", "V112 (carried by the V255 rebase)"),
 ("0xC40D2", u16, "relay gain K1", "measured NULL at both bands", "V112 (carried by rebase)"),
 ("0xC40DC", u16, "alpha2 (2nd HF filter coeff)", "", "V109 (carried by rebase)"),
 ("0xC61C0", u16, "STEER_STATUS debounce SM cal", "blanked to max; UNACCOUNTED (no lineage entry)", "V36"),
 ("0xC61C2", u16, "STEER_STATUS debounce SM cal", "blanked to max; UNACCOUNTED", "V36"),
 ("0xC61C4", u16, "STEER_STATUS debounce SM cal", "blanked to max; UNACCOUNTED", "V36"),
 ("0xC64B4", u16, "STEER_STATUS debounce SM cal", "blanked to max: disables the gentle-EME debounce", "V36"),
 ("0xC64B6", u16, "STEER_STATUS debounce SM cal", "same", "V36"),
 ("0xC64B8", u8,  "DTC-0x49 fail-counter increment gate", "V37's fix for the dash-light fault V36 unmasked", "V37"),
 ("0xC64DE", u8,  "hold count of the gp-0x6b2c sign-flipping square wave", "17 to 27 ticks; road-validated under a label later found wrong", "V18"),
 ("0x13109", u8,  "version-string byte", "marks the image non-stock on a UDS version query", "V22"),
 ("0x14120", u8,  "version-string byte", "same", "V22"),
]
scalars = []
for addr, rd, what, does, intro in CELLS:
    a = int(addr, 16)
    vals = {k: rd(B[k], a) for k in B}
    if rd is f32: vals = {k: round(v, 3) for k, v in vals.items()}
    scalars.append({"addr": addr, "what": what, "does": does, "introduced": intro,
                    "stock": vals["stock"], "V282": vals["V282"], "V289": vals["V289"],
                    "changed_v282": vals["stock"] != vals["V282"], "changed_v289": vals["V282"] != vals["V289"]})

CODE = [
 ("0x2A174", 4, "V289 hook (ld.hu 0x73ee,tp,r7 becomes jr 0xC4C00)"),
 ("0x29D72", 4, "V288 hook site (must be stock on V282/V289)"),
 ("0x55C0E", 4, "0x14A telemetry cave hook (jarl 0xC4B34)"),
 ("0x35A08", 2, "biquad ARM flag source repoint"), ("0x35A12", 1, "biquad arm comparison"), ("0x35A18", 1, "biquad arm branch condition"),
 ("0x454FE", 1, "gp-0x67fa selector substitution byte (measured inert)"),
 ("0x55DF2", 4, "427 MOTOR_TORQUE tap source window"), ("0x55E0F", 2, "427 packer sar shift"),
 ("0xC4B34", 8, "0x14A telemetry cave first bytes"), ("0xC4BD6", 4, "0x14A cave exit"),
 ("0xC4BDC", 8, "V289 telemetry tail first bytes"), ("0xC4C00", 8, "V289 notch cave first bytes"),
 ("0xC4FFC", 4, "page CRC 0xC4xxx"), ("0xC6FFC", 4, "page CRC 0xC6xxx"),
]
code = [{"addr": a, "len": n, "what": w, "stock": hx(B["stock"], int(a, 16), n), "V282": hx(B["V282"], int(a, 16), n), "V289": hx(B["V289"], int(a, 16), n)} for a, n, w in CODE]

def rec(b, ptr_table, slot=7):
    entry = struct.unpack_from("<I", b, ptr_table + 4 * slot)[0]
    n = u16(b, entry)
    X = [u16(b, entry + 2 + 2 * i) for i in range(n)]
    Y = [s16(b, entry + 2 + 2 * n + 2 * i) for i in range(n)]
    return {"ptr_entry": hex(entry), "n": n, "X": X, "Y": Y}
BANKS = {"assist_map_0xC9A88": 0xC9A88, "kp_0xCB994": 0xCB994, "kd_0xCB7D4": 0xCB7D4,
         "fadeA_0xCBA04": 0xCBA04, "fadeB_0xCBA74": 0xCBA74, "taper_opp_0xCB8B4": 0xCB8B4, "taper_same_0xCB924": 0xCB924}
banks = {name: {k: rec(B[k], p) for k in B} for name, p in BANKS.items()}

def runs(a, b, lo=0x13000, hi=0x100000, gap=2):
    out = []; cur = None
    for i in range(lo, hi):
        if a[i] != b[i]:
            if cur and i - cur[1] <= gap: cur[1] = i + 1
            else:
                if cur: out.append(cur)
                cur = [i, i + 1]
    if cur: out.append(cur)
    return out
def summarize(a, b):
    r = runs(a, b); nb = sum(1 for i in range(0x13000, 0x100000) if a[i] != b[i])
    return {"bytes": nb, "runs": len(r), "runs_list": [[hex(x), hex(y), y - x] for x, y in r]}
diffs = {"stock_vs_V282": summarize(B["stock"], B["V282"]), "stock_vs_V289": summarize(B["stock"], B["V289"]), "V282_vs_V289": summarize(B["V282"], B["V289"])}
out = {"images": IMG, "sha256": H, "scalars": scalars, "code": code, "banks": banks, "diffs": diffs}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), indent=1)
print("hashes", {k: v[:12] for k, v in H.items()})
print("diffs", {k: (v["bytes"], v["runs"]) for k, v in diffs.items()})
for s in scalars:
    if s["changed_v282"] or s["changed_v289"]: print(s["addr"], s["stock"], s["V282"], s["V289"], s["what"][:40])
for n, b in banks.items(): print(n, "stockY", b["stock"]["Y"], "| V282Y", b["V282"]["Y"], "| V289==V282", b["V282"] == b["V289"], "| X", b["V282"]["X"])
for c in code: print(c["addr"], c["stock"], c["V282"], c["V289"], c["what"][:30])
print("wrote", OUT)
