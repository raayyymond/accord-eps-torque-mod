cd C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/delay/e1_xcorr
for r in 0000006e--6ca3e014fd 0000006c--68c6e94b17 0000006d--05e83bb04f 00000076--d0b7ea7e4d 00000075--6c8687d5bd 00000064--ce6b0b0ebb; do python s01_chain_extract.py $r > out/extract_$r.log 2>&1; done
python s01_chain_extract.py 0000006c--2bc842dbac 20 > out/extract_0000006c--2bc842dbac.log 2>&1
