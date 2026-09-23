"""Which params did any V293-era config set that the V294 r1 config does not override, and what value would they hold?"""
import json
from pathlib import Path
OUT = Path(__file__).resolve().parent
R = json.load(open(OUT / "decoded_all.json"))
v = lambda n: R[n]["values"]

pre = v("toggle-backup_latest_20260910.json")          # last full device backup before V293 (2026-09-10)
v282b = v("toggle-backup_V282_20260904.json")
r1 = v("toggle-config_V294_accel-trim_r1.json")
rev = v("toggle-config_V294_accel-trim_r1_REVERT_to_V293_r64.json")
asflown = v("toggle-config_V293_r64_ARM-A_asflown.json")

# every config the device may have imported during V293 (flight lineage + A/B arms; withdrawn ones listed separately)
flown_seq = ["toggle-config_V293_torque_mode.json", "toggle-config_V293_torque_mode_r2.json",
             "toggle-config_V293_torque_mode_r3.json", "toggle-config_V293_torque_mode_r4.json",
             "toggle-config_V293_torque_mode_r5.json", "toggle-config_V293_r64_ARM-A_asflown.json"]
others = ["toggle-config_V293_r64_ARM-B_holdlevel-off.json", "toggle-config_V293_r64_ARM-D_observer-off.json",
          "toggle-config_V293_r64_ARM-KP3_margin-safe.json", "SUPERSEDED_toggle-config_V293_r64_ARM-KP_loopgain.json",
          "WITHDRAWN-DO-NOT-FLY_toggle-config_V293_r64_ARM-KP2_shaped-loopgain.json",
          "WITHDRAWN-DO-NOT-FLY_toggle-config_V293_r64_ARM-RF_prefilter-halved.json",
          "toggle-config_V293_torque_mode_r3_REVERT_to_r2.json", "toggle-config_V293_torque_mode_r4_REVERT_to_r3.json",
          "toggle-config_V293_torque_mode_r5_REVERT_to_r4.json"]
union = set()
for n in flown_seq + others:
    union |= set(v(n))
print("keys ever set by a V293-era config:", len(union))
print("keys in r1:", len(r1))
not_in_r1 = sorted(union - set(r1))
print("\nV293-era keys NOT set by r1 (value on device = last imported unless changed by hand):")
print(f"{'key':28s} {'pre-V293(09-10)':>16s} {'V282(09-04)':>12s} {'rev6.4 asflown':>15s}")
for k in not_in_r1:
    print(f"{k:28s} {str(pre.get(k,'<absent>')):>16s} {str(v282b.get(k,'<absent>')):>12s} {str(asflown.get(k,'<absent>')):>15s}")
print("\nr1 keys vs pre-V293 device backup (2026-09-10) and V282 backup (2026-09-04):")
print(f"{'key':28s} {'r1':>8s} {'pre-V293':>10s} {'V282':>10s} {'asflown6.4':>11s}")
for k in r1:
    print(f"{k:28s} {str(r1[k]):>8s} {str(pre.get(k,'<absent>')):>10s} {str(v282b.get(k,'<absent>')):>10s} {str(asflown.get(k,'<absent>')):>11s}")
print("\nREVERT vs asflown: extra keys", sorted(set(rev) - set(asflown)), "missing", sorted(set(asflown) - set(rev)),
      "changed", {k: (asflown[k], rev[k]) for k in asflown if k in rev and asflown[k] != rev[k]})
print("REVERT value types == asflown types:", all(type(rev[k]) is type(asflown[k]) for k in asflown))
# keys r1 sets that are NOT among the V293-era union (new or V282-era)
print("\nr1 keys never set by a V293-era config:", sorted(set(r1) - union))
