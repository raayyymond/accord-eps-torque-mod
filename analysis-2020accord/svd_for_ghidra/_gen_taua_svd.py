import os
os.makedirs('_svd_parts', exist_ok=True)

def make_taua(n, b0, b1):
    lines = []
    def a(s): lines.append(s)

    gap = b1 - b0  # offset from base0 to base1

    a(f'<peripheral>')
    a(f'  <name>TAUA{n}</name>')
    a(f'  <description>Timer Array Unit A {n}</description>')
    a(f'  <baseAddress>0x{b0:08X}</baseAddress>')
    block_size = gap + 0x1C8 + 2
    a(f'  <addressBlock><offset>0x0</offset><size>0x{block_size:X}</size><usage>registers</usage></addressBlock>')
    a(f'  <registers>')

    # CMORm: base0 + 0x200 + m*4, 16-bit R/W, reset 0x0000, m=0..15
    for m in range(16):
        off = 0x200 + m*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}CMOR{m}</name>')
        a(f'      <description>TAUA{n} Channel Mode OS Register {m}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>16</size>')
        a(f'      <access>read-write</access>')
        a(f'      <resetValue>0x0000</resetValue>')
        a(f'      <fields>')
        a(f'        <field><name>CKS</name><description>Sampling clock select [1:0]</description><bitRange>[15:14]</bitRange></field>')
        a(f'        <field><name>CCS</name><description>Count clock select [1:0]</description><bitRange>[13:12]</bitRange></field>')
        a(f'        <field><name>MAS</name><description>Master/slave select (even ch only)</description><bitRange>[11:11]</bitRange></field>')
        a(f'        <field><name>STS</name><description>External start trigger select [2:0]</description><bitRange>[10:8]</bitRange></field>')
        a(f'        <field><name>COS</name><description>Capture update timing [1:0]</description><bitRange>[7:6]</bitRange></field>')
        a(f'        <field><name>MD</name><description>Operating mode [4:0]</description><bitRange>[4:0]</bitRange></field>')
        a(f'      </fields>')
        a(f'    </register>')

    # TPS: base0 + 0x240
    a(f'    <register>')
    a(f'      <name>TAUA{n}TPS</name>')
    a(f'      <description>TAUA{n} Prescaler Clock Select Register</description>')
    a(f'      <addressOffset>0x240</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0xFFFF</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>PRS3</name><description>CK3_PRE prescaler select [3:0]</description><bitRange>[15:12]</bitRange></field>')
    a(f'        <field><name>PRS2</name><description>CK2 prescaler select [3:0]</description><bitRange>[11:8]</bitRange></field>')
    a(f'        <field><name>PRS1</name><description>CK1 prescaler select [3:0]</description><bitRange>[7:4]</bitRange></field>')
    a(f'        <field><name>PRS0</name><description>CK0 prescaler select [3:0]</description><bitRange>[3:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # BRS: base0 + 0x244, 8-bit R/W
    a(f'    <register>')
    a(f'      <name>TAUA{n}BRS</name>')
    a(f'      <description>TAUA{n} Prescaler Baud Rate Setting Register</description>')
    a(f'      <addressOffset>0x244</addressOffset>')
    a(f'      <size>8</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x00</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>BRS</name><description>CK3 division coefficient [7:0]</description><bitRange>[7:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TOM: base0 + 0x248
    a(f'    <register>')
    a(f'      <name>TAUA{n}TOM</name>')
    a(f'      <description>TAUA{n} Channel Output Mode Register</description>')
    a(f'      <addressOffset>0x248</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TOMm</name><description>Output mode per channel: 0=independent 1=synchronous</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TOC: base0 + 0x24C
    a(f'    <register>')
    a(f'      <name>TAUA{n}TOC</name>')
    a(f'      <description>TAUA{n} Channel Output Configuration Register</description>')
    a(f'      <addressOffset>0x24C</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TOCm</name><description>Output config per channel: 0=mode1 1=mode2</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TDE: base0 + 0x250
    a(f'    <register>')
    a(f'      <name>TAUA{n}TDE</name>')
    a(f'      <description>TAUA{n} Channel Dead Time Output Enable Register</description>')
    a(f'      <addressOffset>0x250</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TDEm</name><description>Dead time enable per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TDM: base0 + 0x254
    a(f'    <register>')
    a(f'      <name>TAUA{n}TDM</name>')
    a(f'      <description>TAUA{n} Channel Dead Time Output Mode Register</description>')
    a(f'      <addressOffset>0x254</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TDMm</name><description>Dead time mode per channel: 0=duty 1=TIN-edge</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TRE: base0 + 0x258
    a(f'    <register>')
    a(f'      <name>TAUA{n}TRE</name>')
    a(f'      <description>TAUA{n} Channel Real-Time Output Enable Register</description>')
    a(f'      <addressOffset>0x258</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TREm</name><description>Real-time output enable per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TRC: base0 + 0x25C
    a(f'    <register>')
    a(f'      <name>TAUA{n}TRC</name>')
    a(f'      <description>TAUA{n} Channel Real-Time Output Control Register</description>')
    a(f'      <addressOffset>0x25C</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TRCm</name><description>Real-time trigger channel: 0=next upper 1=self</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # RDE: base0 + 0x260
    a(f'    <register>')
    a(f'      <name>TAUA{n}RDE</name>')
    a(f'      <description>TAUA{n} Channel Reload Data Enable Register</description>')
    a(f'      <addressOffset>0x260</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>RDEm</name><description>Simultaneous rewrite enable per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # RDM: base0 + 0x264
    a(f'    <register>')
    a(f'      <name>TAUA{n}RDM</name>')
    a(f'      <description>TAUA{n} Channel Reload Data Mode Register</description>')
    a(f'      <addressOffset>0x264</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>RDMm</name><description>Simultaneous rewrite timing: 0=master-start 1=triangle-peak</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # RDS: base0 + 0x268
    a(f'    <register>')
    a(f'      <name>TAUA{n}RDS</name>')
    a(f'      <description>TAUA{n} Channel Reload Data Control Channel Select Register</description>')
    a(f'      <addressOffset>0x268</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>RDSm</name><description>Rewrite trigger source per channel: 0=master 1=upper</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # RDC: base0 + 0x26C
    a(f'    <register>')
    a(f'      <name>TAUA{n}RDC</name>')
    a(f'      <description>TAUA{n} Channel Reload Data Control Register</description>')
    a(f'      <addressOffset>0x26C</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>RDCm</name><description>Simultaneous rewrite trigger channel select</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # DASi: base0 + 0x270 + i*4, i=0..7
    for i in range(8):
        off = 0x270 + i*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}DAS{i}</name>')
        a(f'      <description>TAUA{n} DMA Window Address Setting Register {i}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>16</size>')
        a(f'      <access>read-write</access>')
        a(f'      <resetValue>0x0000</resetValue>')
        a(f'      <fields>')
        a(f'        <field><name>DASodd</name><description>Odd channel DMA window address [15:8]</description><bitRange>[15:8]</bitRange></field>')
        a(f'        <field><name>DASeven</name><description>Even channel DMA window address [7:0]</description><bitRange>[7:0]</bitRange></field>')
        a(f'      </fields>')
        a(f'    </register>')

    # --- base1 registers ---
    # CDRm: base1 + m*4, m=0..15
    for m in range(16):
        off = gap + m*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}CDR{m}</name>')
        a(f'      <description>TAUA{n} Channel Data Register {m}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>16</size>')
        a(f'      <access>read-write</access>')
        a(f'      <resetValue>0x0000</resetValue>')
        a(f'      <fields>')
        a(f'        <field><name>CDR</name><description>Capture/compare data [15:0]</description><bitRange>[15:0]</bitRange></field>')
        a(f'      </fields>')
        a(f'    </register>')

    # TOL: base1 + 0x40
    a(f'    <register>')
    a(f'      <name>TAUA{n}TOL</name>')
    a(f'      <description>TAUA{n} Channel Output Active Level Register</description>')
    a(f'      <addressOffset>0x{gap+0x40:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TOLm</name><description>Output logic per channel: 0=positive 1=inverted</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # RDT: base1 + 0x44, write-only
    a(f'    <register>')
    a(f'      <name>TAUA{n}RDT</name>')
    a(f'      <description>TAUA{n} Channel Reload Data Trigger Register</description>')
    a(f'      <addressOffset>0x{gap+0x44:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>write-only</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>RDTm</name><description>Trigger simultaneous rewrite pending per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # RSF: base1 + 0x48, read-only
    a(f'    <register>')
    a(f'      <name>TAUA{n}RSF</name>')
    a(f'      <description>TAUA{n} Channel Reload Status Register</description>')
    a(f'      <addressOffset>0x{gap+0x48:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-only</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>RSFm</name><description>Simultaneous rewrite pending status per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TRO: base1 + 0x4C
    a(f'    <register>')
    a(f'      <name>TAUA{n}TRO</name>')
    a(f'      <description>TAUA{n} Channel Real-Time Output Register</description>')
    a(f'      <addressOffset>0x{gap+0x4C:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TROm</name><description>Real-time output value per channel: 0=low 1=high</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TME: base1 + 0x50
    a(f'    <register>')
    a(f'      <name>TAUA{n}TME</name>')
    a(f'      <description>TAUA{n} Channel Modulation Output Enable Register</description>')
    a(f'      <addressOffset>0x{gap+0x50:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TMEm</name><description>Modulation output enable per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TDL: base1 + 0x54
    a(f'    <register>')
    a(f'      <name>TAUA{n}TDL</name>')
    a(f'      <description>TAUA{n} Channel Dead Time Output Level Register</description>')
    a(f'      <addressOffset>0x{gap+0x54:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TDLm</name><description>Dead time phase per channel: 0=normal 1=reverse</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TO: base1 + 0x58
    a(f'    <register>')
    a(f'      <name>TAUA{n}TO</name>')
    a(f'      <description>TAUA{n} Channel Output Register</description>')
    a(f'      <addressOffset>0x{gap+0x58:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TOm</name><description>Output level per channel: 0=low 1=high</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TOE: base1 + 0x5C
    a(f'    <register>')
    a(f'      <name>TAUA{n}TOE</name>')
    a(f'      <description>TAUA{n} Channel Output Enable Register</description>')
    a(f'      <addressOffset>0x{gap+0x5C:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-write</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TOEm</name><description>Timer output enable per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # CNTm: base1 + 0x80 + m*4, read-only, m=0..15
    for m in range(16):
        off = gap + 0x80 + m*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}CNT{m}</name>')
        a(f'      <description>TAUA{n} Channel Counter Register {m}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>16</size>')
        a(f'      <access>read-only</access>')
        a(f'      <fields>')
        a(f'        <field><name>CNT</name><description>16-bit counter value</description><bitRange>[15:0]</bitRange></field>')
        a(f'      </fields>')
        a(f'    </register>')

    # CMURm: base1 + 0xC0 + m*4, 8-bit R/W, m=0..15
    for m in range(16):
        off = gap + 0xC0 + m*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}CMUR{m}</name>')
        a(f'      <description>TAUA{n} Channel Mode User Register {m}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>8</size>')
        a(f'      <access>read-write</access>')
        a(f'      <resetValue>0x00</resetValue>')
        a(f'      <fields>')
        a(f'        <field><name>TIS</name><description>TIN valid edge select: 00=fall 01=rise 10=both-low 11=both-high</description><bitRange>[1:0]</bitRange></field>')
        a(f'      </fields>')
        a(f'    </register>')

    # DWRm: base1 + 0x100 + m*4, m=0..15
    for m in range(16):
        off = gap + 0x100 + m*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}DWR{m}</name>')
        a(f'      <description>TAUA{n} DMA Window Register {m}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>16</size>')
        a(f'      <access>read-write</access>')
        a(f'      <resetValue>0x0000</resetValue>')
        a(f'    </register>')

    # CSRm: base1 + 0x140 + m*4, 8-bit R, m=0..15
    for m in range(16):
        off = gap + 0x140 + m*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}CSR{m}</name>')
        a(f'      <description>TAUA{n} Channel Status Register {m}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>8</size>')
        a(f'      <access>read-only</access>')
        a(f'      <resetValue>0x00</resetValue>')
        a(f'      <fields>')
        a(f'        <field><name>CSF</name><description>Count direction: 0=up 1=down</description><bitRange>[1:1]</bitRange></field>')
        a(f'        <field><name>OVF</name><description>Counter overflow flag</description><bitRange>[0:0]</bitRange></field>')
        a(f'      </fields>')
        a(f'    </register>')

    # CSCm: base1 + 0x180 + m*4, 8-bit W, m=0..15
    for m in range(16):
        off = gap + 0x180 + m*4
        a(f'    <register>')
        a(f'      <name>TAUA{n}CSC{m}</name>')
        a(f'      <description>TAUA{n} Channel Status Clear Trigger Register {m}</description>')
        a(f'      <addressOffset>0x{off:X}</addressOffset>')
        a(f'      <size>8</size>')
        a(f'      <access>write-only</access>')
        a(f'      <resetValue>0x00</resetValue>')
        a(f'      <fields>')
        a(f'        <field><name>CLOV</name><description>Clear overflow flag (write 1)</description><bitRange>[0:0]</bitRange></field>')
        a(f'      </fields>')
        a(f'    </register>')

    # TE: base1 + 0x1C0, read-only
    a(f'    <register>')
    a(f'      <name>TAUA{n}TE</name>')
    a(f'      <description>TAUA{n} Channel Enable Status Register</description>')
    a(f'      <addressOffset>0x{gap+0x1C0:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>read-only</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TEm</name><description>Counter enable status per channel</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TS: base1 + 0x1C4, write-only
    a(f'    <register>')
    a(f'      <name>TAUA{n}TS</name>')
    a(f'      <description>TAUA{n} Channel Start Trigger Register</description>')
    a(f'      <addressOffset>0x{gap+0x1C4:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>write-only</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TSm</name><description>Start counter per channel (write 1)</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    # TT: base1 + 0x1C8, write-only
    a(f'    <register>')
    a(f'      <name>TAUA{n}TT</name>')
    a(f'      <description>TAUA{n} Channel Stop Trigger Register</description>')
    a(f'      <addressOffset>0x{gap+0x1C8:X}</addressOffset>')
    a(f'      <size>16</size>')
    a(f'      <access>write-only</access>')
    a(f'      <resetValue>0x0000</resetValue>')
    a(f'      <fields>')
    a(f'        <field><name>TTm</name><description>Stop counter per channel (write 1)</description><bitRange>[15:0]</bitRange></field>')
    a(f'      </fields>')
    a(f'    </register>')

    a(f'  </registers>')
    a(f'</peripheral>')
    return '\n'.join(lines)

svd0 = make_taua(0, 0xFF808000, 0xFFFFC400)
svd1 = make_taua(1, 0xFF809000, 0xFFFFC800)

out = svd0 + '\n' + svd1

with open('_svd_parts/section13_taua.svd', 'w', encoding='utf-8') as f:
    f.write(out)

print(f'Done. Total lines: {out.count(chr(10))}')
print(f'Total chars: {len(out)}')
