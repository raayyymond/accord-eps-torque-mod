"""Adversarial method/arithmetic check of finding 'unwind-is-feedforward-release-plus-45ms-lag'.
Re-derives every numeric claim independently from the committed s3_accel/out artifacts
(ensemble.pkl, s3_stats.json, s3_pass2_stats.json) rather than trusting the finding's report.
Result: command hold/unwind/late/ret numbers, best-lag point estimates + CIs, and the
stratified drv_unwind driver-torque numbers all reproduce EXACTLY (see verify_out.txt).
The "P+I share" statistic (-0.12 torque / -0.58 V282) is NOT backed by any committed script;
best reconstruction (share = median_event(mean PI in window) / (|that| + |median_event(mean F)|))
gives V282 -0.581 (matches) but torque -0.142 (vs claimed -0.12), and the number moves to -0.09..-0.16
depending on window [0,1.0) vs [0,1.5) and pooled-vs-median aggregation. Direction/order-of-magnitude
survives every reconstruction; the exact digit and its absence of a CI do not.
"""
