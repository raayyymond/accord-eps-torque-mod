
void V294_lkas_rate_pid(char param_1)

{
  bool bVar1;
  bool bVar2;
  bool bVar3;
  bool bVar4;
  bool bVar5;
  byte bVar6;
  ushort uVar7;
  ushort uVar8;
  ushort uVar9;
  ushort *puVar10;
  ushort uVar11;
  undefined1 uVar12;
  uint uVar13;
  int unaff_gp;
  int unaff_tp;
  ushort *puVar14;
  char cVar15;
  int iVar16;
  short sVar17;
  uint uVar18;
  char cVar19;
  uint uVar20;
  uint uVar21;
  byte bVar22;
  int iVar23;
  short sVar24;
  ushort uVar25;
  int iVar26;
  short sVar27;
  int iVar28;
  char cVar29;
  uint uVar30;
  int iVar31;
  undefined2 uVar32;
  uint uVar33;
  int iVar34;
  uint uVar35;
  undefined2 uVar36;
  uint uVar37;
  undefined2 uVar38;
  undefined *puVar39;
  undefined *puVar40;
  int iVar41;
  ushort *puVar42;
  char *pcVar43;
  char cVar44;
  
  uVar13 = (uint)*(ushort *)(&DAT_000072e8 + unaff_tp);
  uVar25 = *(ushort *)(&DAT_000072ea + unaff_tp);
  uVar7 = *(ushort *)(&DAT_000073f2 + unaff_tp);
  if (((((&DAT_00009600 < &DAT_00001900 + *(short *)(unaff_gp + -0x6a44)) ||
        (&DAT_00009600 < &DAT_00001900 + *(short *)(unaff_gp + -0x6a40))) ||
       (&DAT_00009600 < &DAT_00001900 + *(short *)(unaff_gp + -0x6a3c))) ||
      ((&DAT_00009600 < &DAT_00001900 + *(short *)(unaff_gp + -0x6a38) ||
       (&DAT_00009600 < &DAT_00001900 + *(short *)(unaff_gp + -0x6a46))))) ||
     (*(char *)(unaff_gp + -0x67f4) != '\x01')) {
    bVar1 = false;
    uVar20 = (uint)*(ushort *)(unaff_gp + -0x6a5e);
  }
  else {
    uVar20 = (uint)*(ushort *)(unaff_gp + -0x6a5e);
    bVar1 = uVar20 < 0x7d01;
  }
  iVar28 = (int)*(short *)(unaff_gp + -0x4f60);
  if (((&DAT_00006400 + iVar28 < &DAT_0000c801) && ((int)*(char *)(unaff_gp + -0x6752) + 1U < 3)) &&
     ((&DAT_00002ee0 + *(short *)(unaff_gp + -0x6a56) < (undefined *)0x5dc1 &&
      (*(char *)(unaff_gp + -0x6752) != 0)))) {
    uVar8 = *(ushort *)(&DAT_000073e4 + unaff_tp);
    uVar9 = *(ushort *)(&DAT_000073e2 + unaff_tp);
    uVar12 = 1;
    if (*(char *)(unaff_gp + -0x3d2c) == '\x01') {
      iVar23 = *(int *)(unaff_gp + -0x3d34);
      iVar31 = *(int *)(unaff_gp + -0x3d30);
    }
    else {
      iVar23 = 0;
      iVar31 = 0;
    }
    uVar18 = (uint)*(ushort *)(&DAT_000072e6 + unaff_tp);
    uVar35 = (uint)*(ushort *)(&DAT_000072e6 + unaff_tp);
    iVar34 = (*(short *)(&DAT_000073e8 + unaff_tp) * iVar31 >> 10) +
             ((int)((int)*(short *)(unaff_gp + -0x6a56) *
                   (uint)*(ushort *)(&DAT_000073ea + unaff_tp)) >> 10);
    uVar37 = iVar34 - iVar31;
    *(int *)(unaff_gp + -0x3d30) = iVar34;
    if (((int)(uVar37 - uVar18) < 0 != ((int)uVar37 < 0 && -1 < (int)(uVar37 - uVar18)) ||
         uVar37 == uVar18) &&
       (iVar34 = uVar37 + uVar35, iVar31 = uVar37 + uVar35, bVar6 = (byte)(-uVar35 >> 0x1f),
       uVar35 = uVar37,
       iVar34 < 0 != ((byte)(uVar37 >> 0x1f) != bVar6 && bVar6 == (byte)((uint)iVar31 >> 0x1f)))) {
      uVar35 = -(uint)*(ushort *)(&DAT_000072e6 + unaff_tp);
    }
    uVar18 = ((int)uVar35 >> 5) * 0x20;
    if ((int)uVar18 < 0) {
      uVar18 = ((int)uVar35 >> 5) * -0x20;
    }
    puVar39 = (&PTR_LAB_000cb844)[*(byte *)(unaff_gp + -0x674e)];
    puVar40 = (&PTR_LAB_000cb844)[*(byte *)(unaff_gp + -0x674e)];
    puVar14 = (ushort *)(puVar40 + 0x14);
    if (*(ushort *)(puVar39 + 2) < uVar20) {
      if (uVar20 < *(ushort *)(puVar39 + 0x12)) {
        puVar42 = (ushort *)(puVar39 + 4);
        uVar11 = *(ushort *)(puVar39 + 4);
        while (uVar11 <= uVar20) {
          puVar10 = puVar42 + 1;
          puVar14 = puVar14 + 1;
          puVar42 = puVar42 + 1;
          uVar11 = *puVar10;
        }
        uVar33 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                 (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
      }
      else {
        uVar33 = (uint)*(ushort *)(puVar40 + 0x24);
      }
    }
    else {
      uVar33 = (uint)*puVar14;
    }
    uVar37 = (uint)*(short *)(unaff_gp + -0x69ae);
    uVar33 = uVar33 & 0xffff;
    bVar6 = (byte)(*(short *)(unaff_gp + -0x69ae) >> 0xf);
    if ((int)(uVar37 - uVar33) < 0 != ((char)bVar6 < '\0' && -1 < (int)(uVar37 - uVar33)) ||
        uVar37 == uVar33) {
      uVar30 = -uVar33;
      bVar22 = (byte)(uVar30 >> 0x1f);
      bVar4 = (int)(uVar37 + uVar33) < 0 !=
              (bVar6 >> 7 != bVar22 && bVar22 == (byte)(uVar37 + uVar33 >> 0x1f));
      uVar33 = uVar30 * (bVar4 || uVar37 == uVar30) + uVar37 * (!bVar4 && uVar37 != uVar30);
    }
    uVar37 = iVar28 >> 5;
    if ((int)uVar37 < 0) {
      uVar37 = -uVar37;
    }
    *(char *)(unaff_gp + -0x682f) = (char)uVar37 * (0xfe >= uVar37) - (0xfe < uVar37);
    uVar30 = 0x3200;
    iVar31 = ((int)(iVar23 * (uint)uVar9) >> 5) + ((int)(iVar28 * (uint)uVar8) >> 5);
    iVar23 = iVar31 - iVar23 >> 4;
    *(int *)(unaff_gp + -0x3d34) = iVar31;
    if (iVar23 < 0x3201) {
      uVar30 = (uint)(iVar23 < -0x31ff) * -0x3200 + iVar23 * (uint)(-0x3200 < iVar23);
    }
    uVar37 = uVar30;
    if ((int)uVar30 < 0) {
      uVar37 = -uVar30;
    }
    bVar4 = true;
    if (iVar28 < 0) {
      if (-1 < (int)uVar30) goto LAB_000290aa;
    }
    else if ((int)uVar30 < 0) {
LAB_000290aa:
      bVar4 = false;
    }
    bVar3 = true;
  }
  else {
    uVar12 = 2;
    uVar18 = 0;
    uVar33 = 0;
    uVar35 = 0;
    *(undefined1 *)(unaff_gp + -0x682f) = 0;
    uVar37 = 0;
    bVar4 = false;
    bVar3 = false;
  }
  *(short *)(unaff_gp + -0x6a34) = (short)(uVar18 >> 5);
  *(undefined1 *)(unaff_gp + -0x3d2c) = uVar12;
  *(char *)(unaff_gp + -0x6830) = (char)(uVar37 >> 6);
  if (((uVar13 < uVar20) || (uVar20 < uVar25)) && (*(char *)(unaff_gp + -0x68b3) == '\0')) {
    bVar2 = false;
  }
  else {
    bVar2 = true;
  }
  if (((*(ushort *)(unaff_gp + -0x69aa) < 0x8001) && (uVar7 <= *(ushort *)(unaff_gp + -0x69aa))) &&
     ((bVar1 && ((bVar2 && (*(char *)(unaff_gp + -0x67fe) == '\x02')))))) {
    bVar2 = (int)*(short *)(unaff_gp + -0x69ae) + 0x4000U < 0x8001;
  }
  else {
    bVar2 = false;
  }
  iVar28 = FUN_00046ea6(9);
  cVar15 = (&DAT_000074e2)[unaff_tp];
  if ((((bVar3) && (iVar28 != 1)) && (*(char *)(unaff_gp + -0x67fa) != '\b')) &&
     (*(char *)(unaff_gp + -0x6807) != '\a')) {
    if ((*(uint *)(&DAT_00006400 + unaff_gp) & 8) == 0) {
      if (bVar2) {
        bVar6 = *(byte *)(unaff_gp + -0x6758);
        if (bVar6 < (byte)((&DAT_000074e0)[unaff_tp] + (&DAT_000074e1)[unaff_tp])) {
          cVar19 = *(char *)(unaff_gp + -0x68b3) != '\0';
          if (bVar6 < (byte)(&DAT_000074e1)[unaff_tp]) {
            if (((byte)(&DAT_000074b8)[unaff_tp] < *(byte *)(unaff_gp + -0x682f)) && (uVar33 != 0))
            {
              *(byte *)(unaff_gp + -0x6758) = bVar6 + 1;
            }
            else {
LAB_00029232:
              *(undefined1 *)(unaff_gp + -0x6758) = 0;
            }
          }
          else if ((*(char *)(unaff_gp + -0x6802) == '\x02') && (uVar33 == 0)) {
            bVar6 = *(byte *)(unaff_gp + -0x682f);
            bVar22 = (&DAT_000074b8)[unaff_tp];
            cVar19 = (bVar22 < bVar6) * '\x02' + cVar19 * (bVar6 <= bVar22);
            if (bVar6 <= bVar22) goto LAB_00029232;
          }
          else {
            cVar19 = '\x02';
            *(byte *)(unaff_gp + -0x6758) = bVar6 + 1;
          }
          cVar44 = *(char *)(unaff_gp + -0x6757);
          iVar28 = (int)cVar44;
          if (iVar28 < 1) {
            bVar6 = *(byte *)(unaff_gp + -0x682f);
            if ((((byte)(&DAT_000074b4)[unaff_tp] < bVar6) ||
                (*(ushort *)(&DAT_000071c0 + unaff_tp) < uVar37)) ||
               ((bVar4 && ((((byte)(&DAT_000074b7)[unaff_tp] < bVar6 &&
                            (*(ushort *)(&DAT_000071c2 + unaff_tp) < uVar37)) ||
                           (((byte)(&DAT_000074b6)[unaff_tp] < bVar6 &&
                            (*(ushort *)(&DAT_000071c4 + unaff_tp) < uVar37)))))))) {
              if ((char)(cVar44 + '\x01') < '\0') {
                *(char *)(unaff_gp + -0x6757) = cVar44 + '\x01';
                *(char *)(unaff_gp + -0x6807) = cVar19;
              }
              else {
                uVar12 = (&DAT_000074df)[unaff_tp];
                *(undefined1 *)(unaff_gp + -0x6807) = 4;
                *(undefined1 *)(unaff_gp + -0x6758) = 0;
                *(undefined1 *)(unaff_gp + -0x6757) = uVar12;
              }
            }
            else {
LAB_000292f8:
              *(char *)(unaff_gp + -0x6807) = cVar19;
              *(char *)(unaff_gp + -0x6757) = -cVar15;
            }
          }
          else {
            iVar23 = (int)cVar15;
            bVar6 = (byte)(cVar15 >> 7) >> 7;
            if (iVar28 - iVar23 < 0 ==
                ((byte)(cVar44 >> 7) >> 7 != bVar6 &&
                bVar6 == (byte)((uint)(iVar28 - iVar23) >> 0x1f)) && iVar28 != iVar23) {
              *(char *)(unaff_gp + -0x6757) = cVar44 + -1;
              *(undefined1 *)(unaff_gp + -0x6807) = 4;
              *(undefined1 *)(unaff_gp + -0x6758) = 0;
            }
            else {
              bVar6 = *(byte *)(unaff_gp + -0x682f);
              if ((((byte)(&DAT_000074b5)[unaff_tp] < bVar6) ||
                  (*(ushort *)(&DAT_000071c0 + unaff_tp) < uVar37)) ||
                 ((bVar4 && ((((byte)(&DAT_000074b7)[unaff_tp] < bVar6 &&
                              (*(ushort *)(&DAT_000071c2 + unaff_tp) < uVar37)) ||
                             (((byte)(&DAT_000074b6)[unaff_tp] < bVar6 &&
                              (*(ushort *)(&DAT_000071c4 + unaff_tp) < uVar37)))))))) {
                *(char *)(unaff_gp + -0x6757) = cVar15;
                *(undefined1 *)(unaff_gp + -0x6807) = 4;
                *(undefined1 *)(unaff_gp + -0x6758) = 0;
              }
              else {
                if ((char)(cVar44 + -1) < '\x01') goto LAB_000292f8;
                *(char *)(unaff_gp + -0x6757) = cVar44 + -1;
                *(undefined1 *)(unaff_gp + -0x6807) = 4;
                *(undefined1 *)(unaff_gp + -0x6758) = 0;
              }
            }
          }
        }
        else {
          *(undefined1 *)(unaff_gp + -0x6807) = 7;
          FUN_00016de6(0x49,1,1,1);
          *(undefined1 *)(unaff_gp + -0x6758) = 0;
          *(char *)(unaff_gp + -0x6757) = -cVar15;
        }
      }
      else {
        *(undefined1 *)(unaff_gp + -0x6807) = 3;
        *(undefined1 *)(unaff_gp + -0x6758) = 0;
        *(char *)(unaff_gp + -0x6757) = -cVar15;
      }
    }
    else {
      *(undefined1 *)(unaff_gp + -0x6807) = 6;
      *(undefined1 *)(unaff_gp + -0x6758) = 0;
      *(char *)(unaff_gp + -0x6757) = -cVar15;
    }
  }
  else {
    *(undefined1 *)(unaff_gp + -0x6807) = 7;
    *(undefined1 *)(unaff_gp + -0x6758) = 0;
    *(char *)(unaff_gp + -0x6757) = -cVar15;
  }
  bVar6 = *(byte *)(unaff_gp + -0x3d38);
  if (bVar6 < 5) {
    if (bVar6 == 0) {
LAB_0002935a:
      cVar15 = *(char *)(unaff_gp + -0x6805);
      goto LAB_0002971a;
    }
    if (bVar6 == 1) {
      cVar15 = *(char *)(unaff_gp + -0x6805);
      if (cVar15 == '\x01') {
        if (*(char *)(unaff_gp + -0x6803) == '\0') {
          if (*(byte *)(unaff_gp + -0x6807) < 3) {
            sVar27 = *(short *)(&DAT_000073f8 + unaff_tp);
            *(undefined1 *)(unaff_gp + -0x679f) = 1;
            *(undefined1 *)(unaff_gp + -0x3d38) = 3;
            *(undefined1 *)(unaff_gp + -0x6806) = 1;
            uVar25 = sVar27 + *(short *)(unaff_gp + -0x69b0);
            *(ushort *)(unaff_gp + -0x69b0) = uVar25;
            uVar18 = (uint)uVar25;
            cVar19 = *(char *)(unaff_gp + -0x679e);
          }
          else {
            uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
            cVar19 = *(char *)(unaff_gp + -0x679e);
          }
        }
        else if (*(char *)(unaff_gp + -0x6803) == '\x02') {
          if (*(byte *)(unaff_gp + -0x6807) < 3) {
            *(undefined1 *)(unaff_gp + -0x6806) = 1;
            sVar27 = *(short *)(&DAT_000073fc + unaff_tp);
            *(undefined1 *)(unaff_gp + -0x679f) = 2;
            cVar19 = *(char *)(unaff_gp + -0x679e);
            *(undefined1 *)(unaff_gp + -0x3d38) = 6;
            uVar25 = sVar27 + *(short *)(unaff_gp + -0x69b0);
            *(ushort *)(unaff_gp + -0x69b0) = uVar25;
            uVar18 = (uint)uVar25;
          }
          else {
            uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
            cVar19 = *(char *)(unaff_gp + -0x679e);
          }
        }
        else {
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
          cVar19 = *(char *)(unaff_gp + -0x679e);
        }
      }
      else {
        uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
        cVar19 = *(char *)(unaff_gp + -0x679e);
      }
      goto LAB_00029734;
    }
    if (bVar6 < 3) {
      cVar19 = *(char *)(unaff_gp + -0x6803);
      cVar15 = *(char *)(unaff_gp + -0x6805);
      if ((cVar19 == '\x01') && (cVar15 == '\0')) {
        uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
      }
      else {
        cVar44 = *(char *)(unaff_gp + -0x6807);
        if (cVar44 == '\a') {
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
        }
        else {
          if (cVar44 != '\x04') {
            if ((cVar15 == '\0') && (cVar19 == '\0')) {
              uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
            }
            else {
              uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
              if (cVar44 != '\x03') {
                if (cVar15 == '\0') {
                  if (cVar19 == '\x02') goto LAB_00029680;
                  cVar19 = *(char *)(unaff_gp + -0x679e);
                }
                else {
                  cVar19 = *(char *)(unaff_gp + -0x679e);
                }
                goto LAB_00029734;
              }
            }
LAB_000296f8:
            uVar25 = *(ushort *)(&DAT_000073f6 + unaff_tp);
            cVar19 = *(char *)(unaff_gp + -0x679e);
            *(undefined1 *)(unaff_gp + -0x3d38) = 4;
            *(undefined1 *)(unaff_gp + -0x679f) = 5;
            uVar20 = uVar18 - uVar25;
            *(undefined1 *)(unaff_gp + -0x6806) = 0;
            uVar18 = uVar20 & 0xffff;
            *(short *)(unaff_gp + -0x69b0) = (short)uVar20;
            goto LAB_00029734;
          }
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
        }
      }
      goto LAB_000296c6;
    }
    if (bVar6 == 3) {
      cVar15 = *(char *)(unaff_gp + -0x6805);
      if ((((*(char *)(unaff_gp + -0x6803) != '\x01') || (cVar15 != '\0')) &&
          (bVar6 = *(byte *)(unaff_gp + -0x6807), bVar6 != 7)) && (bVar6 != 4)) {
        if (((cVar15 != '\x01') || (*(char *)(unaff_gp + -0x6803) != '\0')) || (2 < bVar6)) {
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
          if (-1 < (int)(uVar18 - *(ushort *)(&DAT_000073f6 + unaff_tp)) &&
              uVar18 != *(ushort *)(&DAT_000073f6 + unaff_tp)) goto LAB_000296f8;
          goto LAB_0002971a;
        }
        if ((uint)*(ushort *)(&DAT_000073f8 + unaff_tp) + (uint)*(ushort *)(unaff_gp + -0x69b0) <
            0x8000) {
          cVar19 = *(char *)(unaff_gp + -0x679e);
          uVar20 = (uint)*(ushort *)(&DAT_000073f8 + unaff_tp) +
                   (uint)*(ushort *)(unaff_gp + -0x69b0);
          uVar18 = uVar20 & 0xffff;
          *(short *)(unaff_gp + -0x69b0) = (short)uVar20;
        }
        else {
          *(undefined1 *)(unaff_gp + -0x679f) = 3;
          *(undefined1 *)(unaff_gp + -0x6806) = 1;
          uVar18 = 0x8000;
          *(undefined2 *)(unaff_gp + -0x69b0) = 0x8000;
          *(undefined1 *)(unaff_gp + -0x3d38) = 2;
          cVar19 = *(char *)(unaff_gp + -0x679e);
        }
        goto LAB_00029734;
      }
LAB_000294d8:
      uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
      if (-1 < (int)(uVar18 - *(ushort *)(&DAT_000073f4 + unaff_tp)) &&
          uVar18 != *(ushort *)(&DAT_000073f4 + unaff_tp)) goto LAB_000296c6;
    }
    else {
      cVar15 = *(char *)(unaff_gp + -0x6805);
      if (((*(char *)(unaff_gp + -0x6803) == '\x01') && (cVar15 == '\0')) ||
         ((*(char *)(unaff_gp + -0x6807) == '\a' || (*(char *)(unaff_gp + -0x6807) == '\x04'))))
      goto LAB_000294d8;
      uVar20 = (uint)*(ushort *)(unaff_gp + -0x69b0);
      if (-1 < (int)(uVar20 - *(ushort *)(&DAT_000073f6 + unaff_tp)) &&
          uVar20 != *(ushort *)(&DAT_000073f6 + unaff_tp)) {
        cVar19 = *(char *)(unaff_gp + -0x679e);
        uVar18 = uVar20 - *(ushort *)(&DAT_000073f6 + unaff_tp) & 0xffff;
        *(short *)(unaff_gp + -0x69b0) = (short)(uVar20 - *(ushort *)(&DAT_000073f6 + unaff_tp));
        goto LAB_00029734;
      }
    }
LAB_0002971a:
    *(undefined1 *)(unaff_gp + -0x679e) = 0;
    *(undefined1 *)(unaff_gp + -0x3d38) = 1;
    *(undefined1 *)(unaff_gp + -0x6806) = 0;
    uVar18 = 0;
    *(undefined2 *)(unaff_gp + -0x69b0) = 0;
    cVar19 = '\0';
    *(undefined1 *)(unaff_gp + -0x679f) = 0;
  }
  else if (bVar6 < 6) {
    uVar20 = (uint)*(ushort *)(unaff_gp + -0x69b0);
    if ((int)(uVar20 - *(ushort *)(&DAT_000073f4 + unaff_tp)) < 0 ||
        uVar20 == *(ushort *)(&DAT_000073f4 + unaff_tp)) {
      cVar15 = *(char *)(unaff_gp + -0x6805);
      goto LAB_0002971a;
    }
    cVar19 = *(char *)(unaff_gp + -0x679e);
    uVar18 = uVar20 - *(ushort *)(&DAT_000073f4 + unaff_tp) & 0xffff;
    *(short *)(unaff_gp + -0x69b0) = (short)(uVar20 - *(ushort *)(&DAT_000073f4 + unaff_tp));
    cVar15 = *(char *)(unaff_gp + -0x6805);
  }
  else {
    if (bVar6 == 6) {
      cVar15 = *(char *)(unaff_gp + -0x6805);
      if ((*(char *)(unaff_gp + -0x6803) == '\x01') && (cVar15 == '\0')) {
        uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
      }
      else {
        bVar6 = *(byte *)(unaff_gp + -0x6807);
        if (bVar6 == 7) {
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
        }
        else {
          if (bVar6 != 4) {
            if (((cVar15 != '\x01') || (*(char *)(unaff_gp + -0x6803) != '\x02')) || (2 < bVar6)) {
              uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
              if (-1 < (int)(uVar18 - *(ushort *)(&DAT_000073fa + unaff_tp)) &&
                  uVar18 != *(ushort *)(&DAT_000073fa + unaff_tp)) goto LAB_00029680;
              goto LAB_0002971a;
            }
            if ((uint)*(ushort *)(&DAT_000073fc + unaff_tp) + (uint)*(ushort *)(unaff_gp + -0x69b0)
                < 0x8000) {
              uVar25 = *(ushort *)(&DAT_000073fc + unaff_tp);
              cVar19 = '\x01';
              *(undefined1 *)(unaff_gp + -0x679e) = 1;
              uVar20 = (uint)uVar25 + (uint)*(ushort *)(unaff_gp + -0x69b0);
              uVar18 = uVar20 & 0xffff;
              *(short *)(unaff_gp + -0x69b0) = (short)uVar20;
            }
            else {
              *(undefined1 *)(unaff_gp + -0x3d38) = 7;
              cVar19 = *(char *)(unaff_gp + -0x679e);
              *(undefined1 *)(unaff_gp + -0x679f) = 4;
              *(undefined1 *)(unaff_gp + -0x6806) = 1;
              uVar18 = 0x8000;
              *(undefined2 *)(unaff_gp + -0x69b0) = 0x8000;
            }
            goto LAB_00029734;
          }
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
        }
      }
    }
    else {
      if (bVar6 < 8) {
        cVar15 = *(char *)(unaff_gp + -0x6805);
        if ((cVar15 == '\0') && (*(char *)(unaff_gp + -0x6803) == '\x02')) {
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
        }
        else {
          cVar19 = *(char *)(unaff_gp + -0x6807);
          if (cVar19 != '\x03') {
            if ((*(char *)(unaff_gp + -0x6803) == '\x01') && (cVar15 == '\0')) {
              uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
            }
            else if (cVar19 == '\a') {
              uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
            }
            else {
              if (cVar19 != '\x04') {
                if ((cVar15 == '\0') && (*(char *)(unaff_gp + -0x6803) == '\0')) {
                  uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
                }
                else {
                  uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
                  if (cVar19 != '\x03') {
                    cVar19 = *(char *)(unaff_gp + -0x679e);
                    goto LAB_00029734;
                  }
                }
                goto LAB_000296f8;
              }
              uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
            }
            goto LAB_000296c6;
          }
          uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
        }
LAB_00029680:
        uVar25 = *(ushort *)(&DAT_000073fa + unaff_tp);
        cVar19 = *(char *)(unaff_gp + -0x679e);
        *(undefined1 *)(unaff_gp + -0x3d38) = 8;
        *(undefined1 *)(unaff_gp + -0x679f) = 6;
        uVar20 = uVar18 - uVar25;
        *(undefined1 *)(unaff_gp + -0x6806) = 0;
        uVar18 = uVar20 & 0xffff;
        *(short *)(unaff_gp + -0x69b0) = (short)uVar20;
        goto LAB_00029734;
      }
      if (bVar6 != 8) goto LAB_0002935a;
      uVar18 = (uint)*(ushort *)(unaff_gp + -0x69b0);
      cVar15 = *(char *)(unaff_gp + -0x6805);
      if ((int)(uVar18 - *(ushort *)(&DAT_000073fa + unaff_tp)) < 0 ||
          uVar18 == *(ushort *)(&DAT_000073fa + unaff_tp)) goto LAB_0002971a;
      if ((((*(char *)(unaff_gp + -0x6803) != '\x01') || (cVar15 != '\0')) &&
          (*(char *)(unaff_gp + -0x6807) != '\a')) && (*(char *)(unaff_gp + -0x6807) != '\x04')) {
        cVar19 = *(char *)(unaff_gp + -0x679e);
        uVar20 = uVar18 - *(ushort *)(&DAT_000073fa + unaff_tp);
        uVar18 = uVar20 & 0xffff;
        *(short *)(unaff_gp + -0x69b0) = (short)uVar20;
        goto LAB_00029734;
      }
    }
LAB_000296c6:
    *(undefined1 *)(unaff_gp + -0x3d38) = 5;
    *(undefined1 *)(unaff_gp + -0x679f) = 7;
    *(undefined1 *)(unaff_gp + -0x6806) = 0;
    cVar19 = *(char *)(unaff_gp + -0x679e);
  }
LAB_00029734:
  bVar6 = *(byte *)(unaff_gp + -0x3d37);
  if (bVar6 == 0) {
LAB_00029a28:
    uVar32 = *(undefined2 *)(&DAT_00007288 + unaff_tp);
    cVar44 = *(char *)(unaff_gp + -0x6809);
    *(undefined1 *)(unaff_gp + -0x3d37) = 1;
    *(undefined1 *)(unaff_gp + -0x6756) = 0;
    *(undefined2 *)(unaff_gp + -0x6a7e) = uVar32;
    *(undefined2 *)(unaff_gp + -0x6b2c) = 0;
    iVar28 = 0;
  }
  else if (bVar6 == 1) {
    uVar25 = *(ushort *)(unaff_gp + -0x6a7e);
    cVar44 = *(char *)(unaff_gp + -0x6809);
    if (uVar25 < *(ushort *)(&DAT_00007288 + unaff_tp)) {
LAB_00029974:
      *(ushort *)(unaff_gp + -0x6a7e) = uVar25 + 1;
      *(undefined1 *)(unaff_gp + -0x3d37) = 1;
      *(undefined2 *)(unaff_gp + -0x6b2c) = 0;
      iVar28 = 0;
      *(undefined1 *)(unaff_gp + -0x6756) = 0;
    }
    else if ((cVar44 == '\x01') && (bVar1)) {
      uVar20 = (uint)*(ushort *)(unaff_gp + -0x6a5e);
      uVar25 = *(ushort *)(&DAT_00007736 + unaff_tp);
      *(char *)(unaff_gp + -0x6756) =
           (char)((int)(uint)(byte)(&DAT_000074de)[unaff_tp] >> 1) + '\x01';
      puVar14 = (ushort *)(&DAT_0000773e + unaff_tp);
      *(undefined2 *)(unaff_gp + -0x6a7e) = 1;
      *(undefined1 *)(unaff_gp + -0x3d37) = 3;
      *(undefined1 *)(unaff_gp + -0x3d36) = 1;
      if (uVar25 < uVar20) {
        if (uVar20 < *(ushort *)(&DAT_0000773c + unaff_tp)) {
          puVar42 = (ushort *)(&DAT_00007738 + unaff_tp);
          uVar25 = *(ushort *)(&DAT_00007738 + unaff_tp);
          while (uVar25 <= uVar20) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          sVar27 = (short)((int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                          (int)((uint)*puVar42 - (uint)puVar42[-1])) + *puVar14;
        }
        else {
          sVar27 = *(short *)(&DAT_00007744 + unaff_tp);
        }
      }
      else {
        sVar27 = *(short *)(&DAT_0000773e + unaff_tp);
      }
      iVar28 = (int)sVar27;
      *(short *)(unaff_gp + -0x6b2c) = sVar27;
    }
    else {
      *(undefined1 *)(unaff_gp + -0x3d37) = 1;
      *(undefined2 *)(unaff_gp + -0x6b2c) = 0;
      iVar28 = 0;
      *(undefined1 *)(unaff_gp + -0x6756) = 0;
    }
  }
  else if (bVar6 < 3) {
    cVar44 = *(char *)(unaff_gp + -0x6809);
    uVar25 = *(ushort *)(unaff_gp + -0x6a7e);
    if ((cVar44 != '\x01') || (!bVar1)) goto LAB_00029974;
    if (uVar25 < *(ushort *)(&DAT_00007288 + unaff_tp)) {
      *(ushort *)(unaff_gp + -0x6a7e) = uVar25 + 1;
      iVar28 = (int)*(short *)(unaff_gp + -0x6b2c);
    }
    else {
      *(undefined2 *)(unaff_gp + -0x6a7e) = 1;
      *(undefined1 *)(unaff_gp + -0x3d37) = 3;
      *(undefined1 *)(unaff_gp + -0x3d36) = 1;
      uVar20 = (uint)*(ushort *)(unaff_gp + -0x6a5e);
      puVar14 = (ushort *)(&DAT_0000773e + unaff_tp);
      uVar25 = *(ushort *)(&DAT_00007736 + unaff_tp);
      *(char *)(unaff_gp + -0x6756) =
           (char)((int)(uint)(byte)(&DAT_000074de)[unaff_tp] >> 1) + '\x01';
      if (uVar25 < uVar20) {
        if (uVar20 < *(ushort *)(&DAT_0000773c + unaff_tp)) {
          puVar42 = (ushort *)(&DAT_00007738 + unaff_tp);
          uVar25 = *(ushort *)(&DAT_00007738 + unaff_tp);
          while (uVar25 <= uVar20) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          sVar27 = (short)((int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                          (int)((uint)*puVar42 - (uint)puVar42[-1])) + *puVar14;
        }
        else {
          sVar27 = *(short *)(&DAT_00007744 + unaff_tp);
        }
      }
      else {
        sVar27 = *(short *)(&DAT_0000773e + unaff_tp);
      }
      iVar28 = (int)sVar27;
      *(short *)(unaff_gp + -0x6b2c) = sVar27;
    }
  }
  else {
    if (bVar6 != 3) goto LAB_00029a28;
    cVar44 = *(char *)(unaff_gp + -0x6809);
    if ((cVar44 == '\x01') && (bVar1)) {
      sVar27 = *(short *)(unaff_gp + -0x6a7e) + 1;
      if (*(char *)(unaff_gp + -0x3d36) == '\x01') {
        bVar6 = (&DAT_000074de)[unaff_tp];
        bVar22 = *(byte *)(unaff_gp + -0x6756);
        *(short *)(unaff_gp + -0x6a7e) = sVar27;
        if (bVar22 < bVar6) {
LAB_00029954:
          *(byte *)(unaff_gp + -0x6756) = bVar22 + 1;
          iVar28 = (int)*(short *)(unaff_gp + -0x6b2c);
        }
        else {
          cVar29 = '\x01';
          if (*(ushort *)(&DAT_0000728a + unaff_tp) <=
              (ushort)((ushort)(byte)(&DAT_000074de)[unaff_tp] + sVar27)) {
            cVar29 = (char)((int)(uint)(byte)(&DAT_000074de)[unaff_tp] >> 1) + '\x01';
          }
          *(undefined1 *)(unaff_gp + -0x3d36) = 2;
          *(char *)(unaff_gp + -0x6756) = cVar29;
          iVar28 = (int)-*(short *)(unaff_gp + -0x6b2c);
          *(short *)(unaff_gp + -0x6b2c) = -*(short *)(unaff_gp + -0x6b2c);
        }
      }
      else if (*(char *)(unaff_gp + -0x3d36) == '\x02') {
        bVar22 = *(byte *)(unaff_gp + -0x6756);
        if (bVar22 < (byte)(&DAT_000074de)[unaff_tp]) {
          *(short *)(unaff_gp + -0x6a7e) = sVar27;
          goto LAB_00029954;
        }
        sVar17 = sVar27 - (ushort)(byte)(&DAT_000074de)[unaff_tp];
        sVar24 = *(short *)(&DAT_0000728a + unaff_tp) -
                 (short)((int)(uint)(byte)(&DAT_000074de)[unaff_tp] >> 1);
        bVar6 = (byte)(sVar24 >> 0xf) >> 7;
        if ((int)sVar17 - (int)sVar24 < 0 ==
            ((byte)(sVar17 >> 0xf) >> 7 != bVar6 &&
            bVar6 == (byte)((uint)((int)sVar17 - (int)sVar24) >> 0x1f))) {
          *(undefined1 *)(unaff_gp + -0x3d36) = 0;
          *(undefined1 *)(unaff_gp + -0x3d37) = 2;
          *(undefined1 *)(unaff_gp + -0x6756) = 0;
          *(undefined2 *)(unaff_gp + -0x6a7e) = 1;
          iVar28 = 0;
          *(undefined2 *)(unaff_gp + -0x6b2c) = 0;
        }
        else {
          *(undefined1 *)(unaff_gp + -0x3d36) = 1;
          *(undefined1 *)(unaff_gp + -0x6756) = 1;
          uVar20 = (uint)*(ushort *)(unaff_gp + -0x6a5e);
          uVar25 = *(ushort *)(&DAT_00007736 + unaff_tp);
          *(short *)(unaff_gp + -0x6a7e) = sVar27;
          puVar14 = (ushort *)(&DAT_0000773e + unaff_tp);
          if (uVar25 < uVar20) {
            if (uVar20 < *(ushort *)(&DAT_0000773c + unaff_tp)) {
              puVar42 = (ushort *)(&DAT_00007738 + unaff_tp);
              uVar25 = *(ushort *)(&DAT_00007738 + unaff_tp);
              while (uVar25 <= uVar20) {
                puVar10 = puVar42 + 1;
                puVar14 = puVar14 + 1;
                puVar42 = puVar42 + 1;
                uVar25 = *puVar10;
              }
              sVar27 = (short)((int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                              (int)((uint)*puVar42 - (uint)puVar42[-1])) + *puVar14;
            }
            else {
              sVar27 = *(short *)(&DAT_00007744 + unaff_tp);
            }
          }
          else {
            sVar27 = *(short *)(&DAT_0000773e + unaff_tp);
          }
          iVar28 = (int)sVar27;
          *(short *)(unaff_gp + -0x6b2c) = sVar27;
        }
      }
      else {
        *(short *)(unaff_gp + -0x6a7e) = sVar27;
        iVar28 = (int)*(short *)(unaff_gp + -0x6b2c);
      }
    }
    else {
      *(undefined1 *)(unaff_gp + -0x3d36) = 0;
      *(undefined2 *)(unaff_gp + -0x6b2c) = 0;
      *(undefined2 *)(unaff_gp + -0x6a7e) = 1;
      *(undefined1 *)(unaff_gp + -0x3d37) = 1;
      iVar28 = 0;
      *(undefined1 *)(unaff_gp + -0x6756) = 0;
    }
  }
  if (((uVar18 != 0) || (cVar15 == '\x01')) && (bVar3)) {
    if (*(char *)(unaff_gp + -0x680a) == '\x01') {
      iVar34 = 0;
      uVar20 = (uint)*(ushort *)(unaff_gp + -0x6a34);
      puVar14 = (ushort *)(&DAT_00007722 + unaff_tp);
      uVar33 = 0;
      uVar13 = 0;
      iVar31 = 0x7fffffff;
      iVar16 = 0;
      if (*(ushort *)(&DAT_00007712 + unaff_tp) < uVar20) {
        if (uVar20 < *(ushort *)(&DAT_00007720 + unaff_tp)) {
          puVar42 = (ushort *)(&DAT_00007714 + unaff_tp);
          uVar25 = *(ushort *)(&DAT_00007714 + unaff_tp);
          while (uVar25 <= uVar20) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          sVar27 = (short)((int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                          (int)((uint)*puVar42 - (uint)puVar42[-1])) + *puVar14;
        }
        else {
          sVar27 = *(short *)(&DAT_00007730 + unaff_tp);
        }
      }
      else {
        sVar27 = *(short *)(&DAT_00007722 + unaff_tp);
      }
      uVar20 = -((int)(short)((ushort)((int)uVar35 >= 0) - (ushort)((int)uVar35 < 0)) * (int)sVar27)
      ;
    }
    else {
      uVar20 = (uint)*(byte *)(unaff_gp + -0x682f);
      bVar1 = *(char *)(unaff_gp + -0x6803) == '\x02';
      if ((byte)(&DAT_000074b8)[unaff_tp] < uVar20) {
        uVar37 = (uint)*(byte *)(unaff_gp + -0x6830);
        iVar31 = 0;
        iVar23 = (uint)*(byte *)(unaff_gp + -0x674e) << 2;
      }
      else {
        if ((int)uVar33 < 0) {
          if (*(short *)(unaff_gp + -0x4f60) < 0) goto LAB_00029aa0;
LAB_00029b7c:
          iVar23 = (uint)*(byte *)(unaff_gp + -0x674e) * 4;
          iVar31 = *(int *)(&DAT_000cba04 + iVar23);
          puVar14 = (ushort *)(*(int *)(&DAT_000cba04 + iVar23) + 10);
          if (*(ushort *)(iVar31 + 2) < uVar20) {
            if (uVar20 < *(ushort *)(iVar31 + 8)) {
              puVar42 = (ushort *)(iVar31 + 4);
              uVar25 = *(ushort *)(iVar31 + 4);
              while (uVar25 <= uVar20) {
                puVar10 = puVar42 + 1;
                puVar14 = puVar14 + 1;
                puVar42 = puVar42 + 1;
                uVar25 = *puVar10;
              }
              uVar37 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                       (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
            }
            else {
              uVar37 = (uint)*(ushort *)(*(int *)(&DAT_000cba04 + iVar23) + 0x10);
            }
          }
          else {
            uVar37 = (uint)*puVar14;
          }
          iVar31 = *(int *)(&DAT_000cb8b4 + iVar23);
          puVar14 = (ushort *)(*(int *)(&DAT_000cb8b4 + iVar23) + 10);
          if (*(ushort *)(iVar31 + 2) < uVar20) {
            if (uVar20 < *(ushort *)(iVar31 + 8)) {
              puVar42 = (ushort *)(iVar31 + 4);
              uVar25 = *(ushort *)(iVar31 + 4);
              while (uVar25 <= uVar20) {
                puVar10 = puVar42 + 1;
                puVar14 = puVar14 + 1;
                puVar42 = puVar42 + 1;
                uVar25 = *puVar10;
              }
              uVar30 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                       (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
            }
            else {
              uVar30 = (uint)*(ushort *)(*(int *)(&DAT_000cb8b4 + iVar23) + 0x10);
            }
          }
          else {
            uVar30 = (uint)*puVar14;
          }
          iVar31 = (uVar37 & 0xffff) * (uint)bVar1 + (uVar30 & 0xffff) * (uint)!bVar1;
        }
        else {
          if (*(short *)(unaff_gp + -0x4f60) < 0) goto LAB_00029b7c;
LAB_00029aa0:
          uVar37 = (uint)*(byte *)(unaff_gp + -0x674e);
          iVar23 = uVar37 * 4;
          puVar40 = (&PTR_LAB_000cba74)[uVar37];
          puVar14 = (ushort *)((&PTR_LAB_000cba74)[uVar37] + 10);
          if (*(ushort *)(puVar40 + 2) < uVar20) {
            if (uVar20 < *(ushort *)(puVar40 + 8)) {
              puVar42 = (ushort *)(puVar40 + 4);
              uVar25 = *(ushort *)(puVar40 + 4);
              while (uVar25 <= uVar20) {
                puVar10 = puVar42 + 1;
                puVar14 = puVar14 + 1;
                puVar42 = puVar42 + 1;
                uVar25 = *puVar10;
              }
              uVar30 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                       (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
            }
            else {
              uVar30 = (uint)*(ushort *)((&PTR_LAB_000cba74)[uVar37] + 0x10);
            }
          }
          else {
            uVar30 = (uint)*puVar14;
          }
          puVar40 = (&PTR_LAB_000cb924)[uVar37];
          puVar14 = (ushort *)((&PTR_LAB_000cb924)[uVar37] + 10);
          if (*(ushort *)(puVar40 + 2) < uVar20) {
            if (uVar20 < *(ushort *)(puVar40 + 8)) {
              puVar42 = (ushort *)(puVar40 + 4);
              uVar25 = *(ushort *)(puVar40 + 4);
              while (uVar25 <= uVar20) {
                puVar10 = puVar42 + 1;
                puVar14 = puVar14 + 1;
                puVar42 = puVar42 + 1;
                uVar25 = *puVar10;
              }
              uVar37 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                       (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
            }
            else {
              uVar37 = (uint)*(ushort *)((&PTR_LAB_000cb924)[uVar37] + 0x10);
            }
          }
          else {
            uVar37 = (uint)*puVar14;
          }
          iVar31 = (uVar30 & 0xffff) * (uint)bVar1 + (uVar37 & 0xffff) * (uint)!bVar1;
        }
        uVar37 = (uint)*(byte *)(unaff_gp + -0x6830);
        puVar14 = (ushort *)(&DAT_0000797e + unaff_tp);
        if (*(ushort *)(&DAT_00007976 + unaff_tp) < uVar37) {
          if (uVar37 < *(ushort *)(&DAT_0000797c + unaff_tp)) {
            puVar42 = (ushort *)(&DAT_00007978 + unaff_tp);
            uVar25 = *(ushort *)(&DAT_00007978 + unaff_tp);
            while (uVar25 <= uVar37) {
              puVar10 = puVar42 + 1;
              puVar14 = puVar14 + 1;
              puVar42 = puVar42 + 1;
              uVar25 = *puVar10;
            }
            uVar30 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar37 - puVar42[-1])) /
                     (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
          }
          else {
            uVar30 = (uint)*(ushort *)(&DAT_00007984 + unaff_tp);
          }
        }
        else {
          uVar30 = (uint)*(ushort *)(&DAT_0000797e + unaff_tp);
        }
        iVar31 = (int)((iVar31 * uVar30 & 0xffff) * uVar33) >> 0x10;
      }
      uVar30 = (uint)(byte)(&DAT_000074f0)[unaff_tp];
      uVar33 = iVar31 >> 6;
      bVar4 = (int)uVar33 < 0;
      bVar6 = (byte)(iVar31 >> 0x1e);
      if ((int)(uVar33 - uVar30) < 0 == ((char)bVar6 < '\0' && -1 < (int)(uVar33 - uVar30)) &&
          uVar33 != uVar30) {
        uVar33 = (uint)(byte)(&DAT_000074f0)[unaff_tp];
      }
      else {
        uVar30 = (uint)(byte)(&DAT_000074f1)[unaff_tp];
        bVar22 = (byte)(-uVar30 >> 0x1f);
        if ((int)(uVar33 + uVar30) < 0 !=
            (bVar6 >> 7 != bVar22 && bVar22 == (byte)(uVar33 + uVar30 >> 0x1f))) {
          uVar33 = -(uint)(byte)(&DAT_000074f1)[unaff_tp];
        }
      }
      if ((int)uVar33 < 0) {
        uVar33 = -uVar33;
      }
      iVar34 = *(int *)((int)&PTR_LAB_000c9a88 + iVar23);
      iVar31 = *(int *)((int)&PTR_LAB_000c9a88 + iVar23);
      uVar30 = uVar33 & 0xff;
      *(char *)(unaff_gp + -0x674b) = (char)uVar33;
      puVar14 = (ushort *)(iVar31 + 0x16);
      if (*(ushort *)(iVar34 + 2) < uVar30) {
        if (uVar30 < *(ushort *)(iVar34 + 0x14)) {
          puVar42 = (ushort *)(iVar34 + 4);
          uVar25 = *(ushort *)(iVar34 + 4);
          while (uVar25 <= uVar30) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          uVar13 = (uint)*puVar14;
          uVar25 = (short)((int)((puVar14[1] - uVar13) * (uVar30 - puVar42[-1])) /
                          (int)((uint)*puVar42 - (uint)puVar42[-1])) + *puVar14;
        }
        else {
          uVar25 = *(ushort *)(iVar31 + 0x28);
        }
      }
      else {
        uVar25 = *puVar14;
      }
      iVar31 = (int)(short)((ushort)!bVar4 - (ushort)bVar4) * (int)(short)uVar25;
      uVar21 = (uint)*(ushort *)(&DAT_000072e4 + unaff_tp);
      *(short *)(unaff_gp + -0x6a32) = (short)iVar31;
      iVar31 = iVar31 * 4 - uVar35;
      uVar35 = iVar31 >> 5;
      bVar6 = (byte)(iVar31 >> 0x1d);
      iVar34 = 0;
      if ((int)(uVar35 - uVar21) < 0 == ((char)bVar6 < '\0' && -1 < (int)(uVar35 - uVar21)) &&
          uVar35 != uVar21) {
        iVar34 = uVar35 - *(ushort *)(&DAT_000072e4 + unaff_tp);
      }
      else {
        uVar21 = (uint)*(ushort *)(&DAT_000072e4 + unaff_tp);
        bVar22 = (byte)(-uVar21 >> 0x1f);
        if ((int)(uVar35 + uVar21) < 0 !=
            (bVar6 >> 7 != bVar22 && bVar22 == (byte)(uVar35 + uVar21 >> 0x1f))) {
          iVar34 = *(ushort *)(&DAT_000072e4 + unaff_tp) + uVar35;
        }
      }
      iVar26 = (int)((uint)*(ushort *)(&DAT_000071ba + unaff_tp) << 10) >> 3;
      iVar34 = (*(int *)(unaff_gp + -0x6dd0) >> 3) +
               ((int)(iVar34 * (uint)*(ushort *)(&DAT_000073e6 + unaff_tp)) >> 3);
      bVar3 = iVar34 < 0 && -1 < iVar34 - iVar26;
      bVar2 = iVar34 - iVar26 < 0;
      bVar5 = iVar34 != iVar26;
      bVar4 = bVar2 == bVar3;
      iVar16 = iVar26 * (uint)(bVar4 && bVar5) + uVar13 * (!bVar4 || !bVar5);
      if (bVar2 != bVar3 || !bVar5) {
        iVar16 = -iVar26;
        bVar6 = (byte)((uint)iVar16 >> 0x1f);
        bVar4 = iVar34 + iVar26 < 0 !=
                ((byte)((uint)iVar34 >> 0x1f) != bVar6 &&
                bVar6 == (byte)((uint)(iVar34 + iVar26) >> 0x1f));
        iVar16 = iVar16 * (uint)(bVar4 || iVar34 == iVar16) +
                 iVar34 * (uint)(!bVar4 && iVar34 != iVar16);
      }
      iVar41 = *(int *)(&DAT_000cb994 + iVar23);
      iVar26 = *(int *)(&DAT_000cb994 + iVar23);
      *(short *)(unaff_gp + -0x697a) = (short)uVar33;
      puVar14 = (ushort *)(iVar26 + 0xc);
      iVar34 = iVar16 << 3;
      uVar33 = uVar33 & 0xffff;
      if (*(ushort *)(iVar41 + 2) < uVar33) {
        if (uVar33 < *(ushort *)(iVar41 + 10)) {
          puVar42 = (ushort *)(iVar41 + 4);
          uVar25 = *(ushort *)(iVar41 + 4);
          while (uVar25 <= uVar33) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          uVar13 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar33 - puVar42[-1])) /
                   (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
        }
        else {
          uVar13 = (uint)*(ushort *)(iVar26 + 0x14);
        }
      }
      else {
        uVar13 = (uint)*puVar14;
      }
      iVar26 = iVar31 * (uVar13 & 0xffff);
      uVar35 = (uint)*(ushort *)(&DAT_000071bc + unaff_tp);
      uVar33 = iVar26 >> 8;
      bVar6 = (byte)(iVar26 >> 0x1f);
      if ((int)(uVar33 - uVar35) < 0 == ((char)bVar6 < '\0' && -1 < (int)(uVar33 - uVar35)) &&
          uVar33 != uVar35) {
        uVar13 = (uint)*(ushort *)(&DAT_000071bc + unaff_tp);
      }
      else {
        uVar35 = (uint)*(ushort *)(&DAT_000071bc + unaff_tp);
        bVar22 = (byte)(-uVar35 >> 0x1f);
        bVar3 = bVar6 >> 7 != bVar22 && bVar22 == (byte)(uVar33 + uVar35 >> 0x1f);
        bVar2 = (int)(uVar33 + uVar35) < 0;
        bVar4 = bVar2 == bVar3;
        uVar13 = uVar33 * bVar4 + (uVar13 & 0xffff) * (uint)!bVar4;
        if (bVar2 != bVar3) {
          uVar13 = -(uint)*(ushort *)(&DAT_000071bc + unaff_tp);
        }
      }
      bVar4 = 0x177000 < *(int *)(unaff_gp + -0x6cf8) + 0xbb800U;
      iVar26 = *(int *)((int)&PTR_DAT_000cb7d4 + iVar23);
      puVar14 = (ushort *)(*(int *)((int)&PTR_DAT_000cb7d4 + iVar23) + 10);
      if (*(ushort *)(iVar26 + 2) < uVar30) {
        if (uVar30 < *(ushort *)(iVar26 + 8)) {
          puVar42 = (ushort *)(iVar26 + 4);
          uVar25 = *(ushort *)(iVar26 + 4);
          while (uVar25 <= uVar30) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          uVar35 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar30 - puVar42[-1])) /
                   (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
        }
        else {
          uVar35 = (uint)*(ushort *)(*(int *)((int)&PTR_DAT_000cb7d4 + iVar23) + 0x10);
        }
      }
      else {
        uVar35 = (uint)*puVar14;
      }
      iVar26 = (iVar31 - (iVar31 * (uint)bVar4 + *(int *)(unaff_gp + -0x6cf8) * (uint)!bVar4)) *
               (uVar35 & 0xffff);
      uVar35 = (uint)*(ushort *)(&DAT_000071b6 + unaff_tp);
      uVar33 = iVar26 >> 3;
      bVar6 = (byte)(iVar26 >> 0x1b);
      if ((int)(uVar33 - uVar35) < 0 == ((char)bVar6 < '\0' && -1 < (int)(uVar33 - uVar35)) &&
          uVar33 != uVar35) {
        uVar33 = (uint)*(ushort *)(&DAT_000071b6 + unaff_tp);
      }
      else {
        uVar35 = (uint)*(ushort *)(&DAT_000071b6 + unaff_tp);
        bVar22 = (byte)(-uVar35 >> 0x1f);
        if ((int)(uVar33 + uVar35) < 0 !=
            (bVar6 >> 7 != bVar22 && bVar22 == (byte)(uVar33 + uVar35 >> 0x1f))) {
          uVar33 = -(uint)*(ushort *)(&DAT_000071b6 + unaff_tp);
        }
      }
      iVar26 = *(int *)((int)&PTR_LAB_000cbb54 + iVar23);
      iVar16 = (iVar16 >> 7) + uVar13 + uVar33;
      puVar14 = (ushort *)(*(int *)((int)&PTR_LAB_000cbb54 + iVar23) + 0xe);
      if (*(ushort *)(iVar26 + 2) < uVar37) {
        if (uVar37 < *(ushort *)(iVar26 + 0xc)) {
          puVar42 = (ushort *)(iVar26 + 4);
          uVar25 = *(ushort *)(iVar26 + 4);
          while (uVar25 <= uVar37) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          uVar35 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar37 - puVar42[-1])) /
                   (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
        }
        else {
          uVar35 = (uint)*(ushort *)(*(int *)((int)&PTR_LAB_000cbb54 + iVar23) + 0x18);
        }
      }
      else {
        uVar35 = (uint)*puVar14;
      }
      iVar26 = *(int *)((int)&PTR_DAT_000cbc34 + iVar23);
      puVar14 = (ushort *)(*(int *)((int)&PTR_DAT_000cbc34 + iVar23) + 0xe);
      if (*(ushort *)(iVar26 + 2) < uVar37) {
        if (uVar37 < *(ushort *)(iVar26 + 0xc)) {
          puVar42 = (ushort *)(iVar26 + 4);
          uVar25 = *(ushort *)(iVar26 + 4);
          while (uVar25 <= uVar37) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          uVar37 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar37 - puVar42[-1])) /
                   (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
        }
        else {
          uVar37 = (uint)*(ushort *)(*(int *)((int)&PTR_DAT_000cbc34 + iVar23) + 0x18);
        }
      }
      else {
        uVar37 = (uint)*puVar14;
      }
      iVar26 = *(int *)((int)&PTR_LAB_000cbae4 + iVar23);
      puVar14 = (ushort *)(*(int *)((int)&PTR_LAB_000cbae4 + iVar23) + 0xe);
      if (*(ushort *)(iVar26 + 2) < uVar20) {
        if (uVar20 < *(ushort *)(iVar26 + 0xc)) {
          puVar42 = (ushort *)(iVar26 + 4);
          uVar25 = *(ushort *)(iVar26 + 4);
          while (uVar25 <= uVar20) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          uVar30 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                   (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
        }
        else {
          uVar30 = (uint)*(ushort *)(*(int *)((int)&PTR_LAB_000cbae4 + iVar23) + 0x18);
        }
      }
      else {
        uVar30 = (uint)*puVar14;
      }
      iVar26 = *(int *)(&DAT_000cbbc4 + iVar23);
      iVar23 = *(int *)(&DAT_000cbbc4 + iVar23);
      puVar14 = (ushort *)(iVar23 + 0xe);
      if (*(ushort *)(iVar26 + 2) < uVar20) {
        if (uVar20 < *(ushort *)(iVar26 + 0xc)) {
          puVar42 = (ushort *)(iVar26 + 4);
          uVar25 = *(ushort *)(iVar26 + 4);
          while (uVar25 <= uVar20) {
            puVar10 = puVar42 + 1;
            puVar14 = puVar14 + 1;
            puVar42 = puVar42 + 1;
            uVar25 = *puVar10;
          }
          uVar20 = (int)(((uint)puVar14[1] - (uint)*puVar14) * (uVar20 - puVar42[-1])) /
                   (int)((uint)*puVar42 - (uint)puVar42[-1]) + (uint)*puVar14;
        }
        else {
          uVar20 = (uint)*(ushort *)(iVar23 + 0x18);
        }
      }
      else {
        uVar20 = (uint)*puVar14;
      }
      uVar20 = ((int)(((uVar35 & 0xffff) * (uint)bVar1 + (uVar37 & 0xffff) * (uint)!bVar1) *
                      ((uVar30 & 0xffff) * (uint)bVar1 + (uVar20 & 0xffff) * (uint)!bVar1) & 0xffff)
               >> 8) * iVar16 >> 8;
    }
    uVar32 = (undefined2)iVar16;
    uVar36 = (undefined2)uVar33;
    uVar38 = (undefined2)uVar13;
    uVar13 = (uint)*(ushort *)(&DAT_000071be + unaff_tp);
    if ((int)(uVar20 - uVar13) < 0 == ((int)uVar20 < 0 && -1 < (int)(uVar20 - uVar13)) &&
        uVar20 != uVar13) {
      iVar23 = (int)*(short *)(&DAT_000071be + unaff_tp);
    }
    else {
      uVar13 = (uint)*(ushort *)(&DAT_000071be + unaff_tp);
      bVar6 = (byte)(-uVar13 >> 0x1f);
      if ((int)(uVar20 + uVar13) < 0 ==
          ((byte)(uVar20 >> 0x1f) != bVar6 && bVar6 == (byte)(uVar20 + uVar13 >> 0x1f))) {
        iVar23 = (int)(short)uVar20;
      }
      else {
        iVar23 = (int)-*(short *)(&DAT_000071be + unaff_tp);
      }
    }
  }
  else {
    iVar34 = 0;
    uVar38 = 0;
    uVar36 = 0;
    uVar32 = 0;
    iVar31 = 0x7fffffff;
    iVar23 = 0;
  }
  uVar25 = *(ushort *)(&DAT_000073ee + unaff_tp);
  *(short *)(unaff_gp + -0x6b2e) = (short)iVar23;
  sVar27 = *(short *)(&DAT_000073ec + unaff_tp);
  *(undefined2 *)(unaff_gp + -0x6b32) = uVar38;
  *(int *)(unaff_gp + -0x6cf8) = iVar31;
  *(int *)(unaff_gp + -0x6dd0) = iVar34;
  cVar15 = (&DAT_000074a3)[unaff_tp];
  *(undefined2 *)(unaff_gp + -0x6b36) = uVar36;
  *(undefined2 *)(unaff_gp + -0x6b34) = uVar32;
  iVar23 = ((int)sVar27 * *(int *)(unaff_gp + -0x3d3c) >> 10) + ((int)(iVar23 * (uint)uVar25) >> 10)
  ;
  iVar31 = *(int *)(unaff_gp + -0x3d3c) + iVar23;
  iVar34 = iVar31 >> 5;
  *(int *)(unaff_gp + -0x3d3c) = iVar23;
  if ((cVar15 == '\x01') && (*(char *)(unaff_gp + -0x6806) == '\0')) {
    iVar23 = (int)*(short *)(&DAT_000071b8 + unaff_tp);
    iVar16 = (int)(short)iVar34;
    bVar6 = (byte)(*(short *)(&DAT_000071b8 + unaff_tp) >> 0xf) >> 7;
    if (((iVar16 - iVar23 < 0 !=
          ((byte)((short)iVar34 >> 0xf) >> 7 != bVar6 &&
          bVar6 == (byte)((uint)(iVar16 - iVar23) >> 0x1f)) || iVar16 == iVar23) &&
        (uVar13 = (uint)*(ushort *)(&DAT_000071b8 + unaff_tp), bVar6 = (byte)(-uVar13 >> 0x1f),
        (int)(iVar34 + uVar13) < 0 ==
        ((byte)((byte)(iVar31 >> 0x1d) >> 7) != bVar6 && bVar6 == (byte)(iVar34 + uVar13 >> 0x1f))))
       || (iVar34 * *(short *)(unaff_gp + -0x6b30) < 1)) {
      iVar23 = 0;
      goto LAB_0002a1ee;
    }
  }
  iVar23 = (int)(short)((int)(iVar34 * uVar18) >> 0xf);
LAB_0002a1ee:
  uVar20 = (uint)*(short *)(&DAT_00007cd0 + unaff_tp);
  uVar35 = (uint)*(ushort *)(&DAT_000071b4 + unaff_tp);
  iVar28 = (iVar28 + iVar23) *
           (int)(short)*(char *)(unaff_gp + -0x6752) * (int)*(short *)(&DAT_00007cd0 + unaff_tp);
  uVar13 = iVar28 >> 0xf;
  bVar6 = (byte)(iVar28 >> 0x1f);
  *(short *)(unaff_gp + -0x6b30) = (short)iVar23;
  if ((int)(uVar13 - uVar35) < 0 == ((char)bVar6 < '\0' && -1 < (int)(uVar13 - uVar35)) &&
      uVar13 != uVar35) {
    uVar13 = (uint)*(short *)(&DAT_000071b4 + unaff_tp);
  }
  else {
    uVar35 = (uint)*(ushort *)(&DAT_000071b4 + unaff_tp);
    bVar22 = (byte)(-uVar35 >> 0x1f);
    if ((int)(uVar13 + uVar35) < 0 !=
        (bVar6 >> 7 != bVar22 && bVar22 == (byte)(uVar13 + uVar35 >> 0x1f))) {
      uVar13 = -(uint)*(ushort *)(&DAT_000071b4 + unaff_tp);
    }
  }
  *(short *)(unaff_gp + -0x6b38) = (short)uVar13;
  if ((*(char *)(unaff_gp + -0x67a4) == '\x02') || (*(char *)(unaff_gp + -0x67a4) == '\x03')) {
    bVar6 = 1;
    if (cVar19 != '\x01') {
      uVar25 = *(ushort *)(&DAT_000073dc + unaff_tp);
    }
    else {
      uVar25 = *(ushort *)(&DAT_000073da + unaff_tp);
    }
    *(short *)(unaff_gp + -0x697e) = 0x400 - (short)(uVar18 * (0x400 - (uint)uVar25) >> 0xf);
    if (cVar19 != '\x01') {
      uVar25 = *(ushort *)(&DAT_000073e0 + unaff_tp);
    }
    else {
      uVar25 = *(ushort *)(&DAT_000073de + unaff_tp);
    }
    uVar20 = (uint)uVar25;
    sVar27 = 0x400 - (short)(uVar18 * (0x400 - uVar20) >> 0xf);
  }
  else {
    bVar6 = 0;
    sVar27 = 0x400;
    *(undefined2 *)(unaff_gp + -0x697e) = 0x400;
  }
  *(short *)(unaff_gp + -0x697c) = sVar27;
  if ((uVar18 != 0) || (iVar28 = uVar20 * (cVar44 == '\x01'), cVar44 == '\x01')) {
    iVar28 = 1;
  }
  uVar20 = (uint)*(byte *)(*(int *)(unaff_gp + -0x257c) + 0x14);
  iVar23 = (uint)(7 < uVar20) * 7 + uVar20 * (uVar20 < 8);
  pcVar43 = (char *)(iVar23 + unaff_gp + -16000);
  *pcVar43 = *pcVar43 + '\x01';
  cVar15 = *(char *)(iVar23 + unaff_gp + -16000);
  *(undefined1 *)(unaff_gp + -0x67a2) = 1;
  *(ushort *)(unaff_gp + -0x6b3c) = (short)uVar13 * (ushort)bVar6;
  *(bool *)(unaff_gp + -0x67a7) = iVar28 != 0;
  *(undefined1 *)(unaff_gp + -0x67a3) = 1;
  if ((cVar15 != param_1) && (*(char *)(unaff_gp + -0x3e78 + iVar23) == '\x01')) {
    FUN_0001cba6();
  }
  return;
}

