cd C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/delay/e1_xcorr
i=0
for ks in 0.7 1.0 1.5; do for F in 0.0 0.01; do
  MB_GRID="{\"J\":[8e-5,1.5e-4,3e-4,6e-4],\"b\":[1.5e-3,3e-3,5e-3,8e-3],\"F\":[$F],\"ks\":[$ks]}" python s06_mb.py real real2_ks${ks}_F${F} > out/mb_real2_ks${ks}_F${F}.log 2>&1 &
done; done
wait
