cd C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/delay/e1_xcorr
python s06_mb.py real real > out/mb_real.log 2>&1 &
python s06_mb.py synth pcA_D30 30 8e-5 6e-4 0.02 1.0 0 > out/mb_pcA.log 2>&1 &
python s06_mb.py synth pcB_D60 60 8e-5 6e-4 0.02 1.0 0 > out/mb_pcB.log 2>&1 &
python s06_mb.py synth pcC_D30 30 3e-4 6e-4 0.02 1.0 0 > out/mb_pcC.log 2>&1 &
python s06_mb.py synth pcD_D60 60 1e-3 3e-3 0.02 1.0 0 > out/mb_pcD.log 2>&1 &
python s06_mb.py synth pcE_D45off 45 1.2e-4 9e-4 0.015 1.2 0 > out/mb_pcE.log 2>&1 &
python s06_mb.py synth pcF_D30fb 30 8e-5 6e-4 0.02 1.0 1e-3 > out/mb_pcF.log 2>&1 &
python s06_mb.py synth pcG_D60fb 60 8e-5 1.5e-3 0.01 1.0 1e-3 > out/mb_pcG.log 2>&1 &
wait
