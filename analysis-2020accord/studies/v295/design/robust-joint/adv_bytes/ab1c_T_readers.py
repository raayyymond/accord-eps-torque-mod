# -*- coding: utf-8 -*-
"""ab1c_T_readers.py -- every access to the delivered lane torque gp-0x6b38 (what b scales) and to gp-0x6b30 (yr, the
output-gate sign memory) in the V294 image, all encodings, with the ab1 decoder (controls asserted there).  ANALYSIS ONLY."""
exec(open(__file__.replace("ab1c_T_readers.py", "ab1_bytes.py")).read().split("print(\"\n[3]")[0])
for nm, lo, hi in (("gp-0x6b38 (T, short)", -0x6B38, -0x6B37), ("gp-0x6b30 (yr prev)", -0x6B30, -0x6B2F),
                   ("gp-0x6b2e (S publish)", -0x6B2E, -0x6B2D), ("gp-0x6b3c (T gated copy)", -0x6B3C, -0x6B3B)):
    census(nm, 4, lo, hi)
