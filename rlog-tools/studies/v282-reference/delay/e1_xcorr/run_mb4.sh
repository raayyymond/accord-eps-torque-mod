cd C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/delay/e1_xcorr
for ks in 0.7 1.0 1.5; do
  G="{\"J\":[8e-5,1.5e-4,3e-4,6e-4],\"b\":[1.5e-3,3e-3,5e-3,8e-3],\"F\":[0.0,0.01],\"ks\":[$ks]}"
  MB_DIST=0.015 MB_GRID="$G" python s06_mb.py synth pcJ_ks$ks 30 1.5e-4 3e-3 0.0 1.0 0 > out/mb_pcJ_ks$ks.log 2>&1 &
  MB_DIST=0.0 MB_GRID="$G" python s06_mb.py synth pcK_ks$ks 30 1.5e-4 3e-3 0.0 1.0 3e-3 > out/mb_pcK_ks$ks.log 2>&1 &
done
wait
for t in pcJ pcK; do python s10_merge.py ${t}M ${t}_ks0.7 ${t}_ks1.0 ${t}_ks1.5 > out/s10_${t}M.txt 2>&1; python s09_mb_summary.py ${t}M > out/s09_${t}M.txt 2>&1; done
echo FIN
