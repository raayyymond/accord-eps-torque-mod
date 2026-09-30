"""ADV-D step 6: the harness score() of the BUILT V295 image (cells read by address from the image file, hash-checked),
V294 in the same batch.  Default plants + stress members (M_LOOP), modes A and B, dists full and lp."""
import sys, json, os, time
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
c5 = H.Cells.from_image(V295, "V295", SHA)
c4 = H.Cells.v294()
print("V295 cells diff vs V294 (from the IMAGES):", c5.diff(c4), " edit class:", c5.edit_class(c4), " problems:", c5.problems())
assert c5.diff(c4) == {"fb_b": (567, 1050)}
t0 = time.time()
r = H.score(c5, plants=H.DEFAULT_PLANTS, base=c4)
with open("d6_score_out.txt", "w") as f:
    H.print_score(r, file=f)
json.dump(H.to_jsonable(r), open("d6_score.json", "w"))
print("done %.0f s" % (time.time() - t0))
