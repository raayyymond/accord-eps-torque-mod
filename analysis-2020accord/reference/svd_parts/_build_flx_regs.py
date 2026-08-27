#!/usr/bin/env python3
"""Build FLX SVD fragment for Section 24 FlexRay."""
import sys, io, xml.etree.ElementTree as ET
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RO = 'read-only'
RW = 'read-write'
WO = 'write-only'

# ============================================================
# REGISTER DEFINITIONS
# (symbol, offset_hex, name, size_bits, access, reset_hex_str, fields)
# fields = list of (msb, lsb, name, desc)
# ============================================================

REGS = []

# ---- HIF registers ----
REGS += [
    ('FLX0CI',   0x0000, 'Controller information',                32, RO,  '0x65726179', [
        (31,0,'FLX0MN','Controller information (ASCII eray)'),
    ]),
    ('FLX0VI',   0x0004, 'Vendor information',                   32, RO,  '0x01050004', [
        (31,24,'FLX0VI_ID','Vendor ID'),
        (23,16,'FLX0FMR','FlexRay controller release number'),
        (7,0,  'FLX0PCN','Product code number'),
    ]),
    ('FLX0CS',   0x0008, 'Control setting',                      32, RW,  '0x00000002', [
        (31,24,'FLX0CSLK','Control setting lock key'),
        (1,1,  'FLX0MD',  'Controller disable'),
        (0,0,  'FLX0SR',  'Software reset'),
    ]),
]

# ---- Special registers ----
REGS += [
    ('FLX0TEST1', 0x0010, 'Test register 1',                    32, RW,  '0x00000300', [
        (31,28,'FLX0CERB','Coding error report channel B'),
        (27,24,'FLX0CERA','Coding error report channel A'),
        (21,21,'FLX0TXENB','Control of channel B transmit enable signal'),
        (20,20,'FLX0TXENA','Control of channel A transmit enable signal'),
        (19,19,'FLX0TXB','Control of channel B transmit signal'),
        (18,18,'FLX0TXA','Control of channel A transmit signal'),
        (17,17,'FLX0RXB','Monitor channel B receive signal'),
        (16,16,'FLX0RXA','Monitor channel A receive signal'),
        (9,9,  'FLX0AOB','Activity detected on channel B'),
        (8,8,  'FLX0AOA','Activity detected on channel A'),
        (5,4,  'FLX0TMC','Test multiplexer control'),
        (1,1,  'FLX0ELBE','External loop back enable'),
        (0,0,  'FLX0WRTEN','Write test register enable'),
    ]),
    ('FLX0TEST2', 0x0014, 'Test register 2',                    32, RW,  '0x00000000', [
        (6,4,  'FLX0SSEL','RAM segment setting'),
        (2,0,  'FLX0RS',  'RAM selection setting'),
    ]),
    ('FLX0LCK',  0x001C, 'Lock register',                       32, RW,  '0x00000000', [
        (15,8, 'FLX0TMK','Test mode key'),
        (7,0,  'FLX0CLK','Configuration lock key'),
    ]),
]

# ---- Interrupt registers ----
REGS += [
    ('FLX0EIR',  0x0020, 'Error interrupt register',            32, RW,  '0x00000000', [
        (26,26,'FLX0TABBE','Transmission slot boundary violation on channel B'),
        (25,25,'FLX0LTVBE','Latest transmit violation on channel B'),
        (24,24,'FLX0EDBE', 'Error detected on channel B'),
        (18,18,'FLX0TABAE','Transmission slot boundary violation on channel A'),
        (17,17,'FLX0LTVAE','Latest transmit violation on channel A'),
        (16,16,'FLX0EDAE', 'Error detected on channel A'),
        (11,11,'FLX0MHFE', 'Message handler constraints flag'),
        (10,10,'FLX0IOBAE','Illegal output buffer access'),
        (9,9,  'FLX0IIBAE','Illegal input buffer access'),
        (8,8,  'FLX0EFAE', 'Empty FIFO access'),
        (7,7,  'FLX0RFOE', 'Receive FIFO overrun'),
        (5,5,  'FLX0CCLE', 'CHI command locked'),
        (4,4,  'FLX0CCFE', 'Clock correction failure'),
        (3,3,  'FLX0SFOE', 'Sync frame overflow'),
        (2,2,  'FLX0SFBME','Sync frames below minimum'),
        (1,1,  'FLX0CNAE', 'Command not accepted'),
        (0,0,  'FLX0PEMCE','POC error mode changed'),
    ]),
    ('FLX0SIR',  0x0024, 'Status interrupt register',           32, RW,  '0x00000000', [
        (25,25,'FLX0CLMTSB','Clear MTS channel B'),
        (24,24,'FLX0CLWUPB','Clear wakeup channel B'),
        (17,17,'FLX0CLMTSA','Clear MTS channel A'),
        (16,16,'FLX0WUPAF', 'Wakeup pattern received on channel A'),
        (15,15,'FLX0WUPBF', 'Wakeup pattern received on channel B'),
        (14,14,'FLX0MTSB',  'MTS received on channel B'),
        (13,13,'FLX0MTSA',  'MTS received on channel A'),
        (12,12,'FLX0WSTAF', 'Wakeup status changed flag'),
        (11,11,'FLX0CYCS',  'Cycle start'),
        (10,10,'FLX0TXI',   'Transmission interrupt'),
        (9,9,  'FLX0RXI',   'Receive interrupt'),
        (8,8,  'FLX0RFNE',  'Receive FIFO not empty'),
        (7,7,  'FLX0RFCL',  'Receive FIFO critical level'),
        (6,6,  'FLX0NMVC',  'Network management vector changed'),
        (5,5,  'FLX0TI1',   'Timer interrupt 1'),
        (4,4,  'FLX0TI0',   'Timer interrupt 0'),
        (3,3,  'FLX0TIBC',  'Transfer input buffer completed'),
        (2,2,  'FLX0TOBC',  'Transfer output buffer completed'),
        (1,1,  'FLX0SWE',   'Stop watch event'),
        (0,0,  'FLX0SUCST', 'Startup completed successfully'),
    ]),
    ('FLX0EILS', 0x0028, 'Error interrupt line select',         32, RW,  '0x00000000', [
        (26,26,'FLX0TABBELS','TABBE interrupt line select'),
        (25,25,'FLX0LTVBELS','LTVBE interrupt line select'),
        (24,24,'FLX0EDBELS', 'EDBE interrupt line select'),
        (18,18,'FLX0TABAELS','TABAE interrupt line select'),
        (17,17,'FLX0LTVAELS','LTVAE interrupt line select'),
        (16,16,'FLX0EDAELS', 'EDAE interrupt line select'),
        (11,11,'FLX0MHFELS', 'MHFE interrupt line select'),
        (10,10,'FLX0IOBAELS','IOBAE interrupt line select'),
        (9,9,  'FLX0IIBAELS','IIBAE interrupt line select'),
        (8,8,  'FLX0EFAELS', 'EFAE interrupt line select'),
        (7,7,  'FLX0RFOELS', 'RFOE interrupt line select'),
        (5,5,  'FLX0CCLELS', 'CCLE interrupt line select'),
        (4,4,  'FLX0CCFELS', 'CCFE interrupt line select'),
        (3,3,  'FLX0SFOELS', 'SFOE interrupt line select'),
        (2,2,  'FLX0SFBMELS','SFBME interrupt line select'),
        (1,1,  'FLX0CNAELS', 'CNAE interrupt line select'),
        (0,0,  'FLX0PEMCELS','PEMCE interrupt line select'),
    ]),
    ('FLX0SILS', 0x002C, 'Status interrupt line select',        32, RW,  '0x0303FFFF', [
        (25,25,'FLX0CLMTSBLS','CLMTSB line select'),
        (24,24,'FLX0CLWUPBLS','CLWUPB line select'),
        (17,17,'FLX0CLMTSALS','CLMTSA line select'),
        (16,16,'FLX0CLWUPALS','CLWUPA line select'),
        (15,15,'FLX0WUPBFLS','WUPBF line select'),
        (14,14,'FLX0MTSBLS',  'MTSB line select'),
        (13,13,'FLX0MTSALS',  'MTSA line select'),
        (12,12,'FLX0WSTAFLS', 'WSTAF line select'),
        (11,11,'FLX0CYCSFLS', 'CYCS line select'),
        (10,10,'FLX0TXILS',   'TXI line select'),
        (9,9,  'FLX0RXILS',   'RXI line select'),
        (8,8,  'FLX0RFNELS',  'RFNE line select'),
        (7,7,  'FLX0RFCLLS',  'RFCL line select'),
        (6,6,  'FLX0NMVCLS',  'NMVC line select'),
        (5,5,  'FLX0TI1LS',   'TI1 line select'),
        (4,4,  'FLX0TI0LS',   'TI0 line select'),
        (3,3,  'FLX0TIBCLS',  'TIBC line select'),
        (2,2,  'FLX0TOBCLS',  'TOBC line select'),
        (1,1,  'FLX0SWELS',   'SWE line select'),
        (0,0,  'FLX0SUCSLS',  'SUCST line select'),
    ]),
    ('FLX0EIES', 0x0030, 'Error interrupt enable set',          32, RW,  '0x00000000', [
        (26,26,'FLX0TABBEES','TABBE enable set'),
        (25,25,'FLX0LTVBEES','LTVBE enable set'),
        (24,24,'FLX0EDBEES', 'EDBE enable set'),
        (18,18,'FLX0TABAEES','TABAE enable set'),
        (17,17,'FLX0LTVAEES','LTVAE enable set'),
        (16,16,'FLX0EDAEES', 'EDAE enable set'),
        (11,11,'FLX0MHFEES', 'MHFE enable set'),
        (10,10,'FLX0IOBAEES','IOBAE enable set'),
        (9,9,  'FLX0IIBAEES','IIBAE enable set'),
        (8,8,  'FLX0EFAEES', 'EFAE enable set'),
        (7,7,  'FLX0RFOEESS','RFOE enable set'),
        (5,5,  'FLX0CCLEE_S','CCLE enable set'),
        (4,4,  'FLX0CCFEE_S','CCFE enable set'),
        (3,3,  'FLX0SFOEES', 'SFOE enable set'),
        (2,2,  'FLX0SFBMEES','SFBME enable set'),
        (1,1,  'FLX0CNAEES', 'CNAE enable set'),
        (0,0,  'FLX0PEMCEES','PEMCE enable set'),
    ]),
    ('FLX0EIER', 0x0034, 'Error interrupt enable reset',        32, RW,  '0x00000000', [
        (26,26,'FLX0TABBEERS','TABBE enable reset'),
        (25,25,'FLX0LTVBEERS','LTVBE enable reset'),
        (24,24,'FLX0EDBEERS', 'EDBE enable reset'),
        (18,18,'FLX0TABAEERS','TABAE enable reset'),
        (17,17,'FLX0LTVAEERS','LTVAE enable reset'),
        (16,16,'FLX0EDAEERS', 'EDAE enable reset'),
        (11,11,'FLX0MHFEERS', 'MHFE enable reset'),
        (10,10,'FLX0IOBAEEERS','IOBAE enable reset'),
        (9,9,  'FLX0IIBAEEERS','IIBAE enable reset'),
        (8,8,  'FLX0EFAEERS', 'EFAE enable reset'),
        (7,7,  'FLX0RFOEERS', 'RFOE enable reset'),
        (5,5,  'FLX0CCLEERS', 'CCLE enable reset'),
        (4,4,  'FLX0CCFEERS', 'CCFE enable reset'),
        (3,3,  'FLX0SFOEERS', 'SFOE enable reset'),
        (2,2,  'FLX0SFBMEERS','SFBME enable reset'),
        (1,1,  'FLX0CNAEERS', 'CNAE enable reset'),
        (0,0,  'FLX0PEMCEERS','PEMCE enable reset'),
    ]),
    ('FLX0SIES', 0x0038, 'Status interrupt enable set',         32, RW,  '0x00000000', [
        (17,17,'FLX0CLMTSAES','CLMTSA enable set'),
        (16,16,'FLX0CLWUPAES','CLWUPA enable set'),
        (15,15,'FLX0WUPBFES','WUPBF enable set'),
        (14,14,'FLX0MTSBES', 'MTSB enable set'),
        (13,13,'FLX0MTSAES', 'MTSA enable set'),
        (12,12,'FLX0WSTAFES','WSTAF enable set'),
        (11,11,'FLX0CYCSES', 'CYCS enable set'),
        (10,10,'FLX0TXIES',  'TXI enable set'),
        (9,9,  'FLX0RXIES',  'RXI enable set'),
        (8,8,  'FLX0RFNEES', 'RFNE enable set'),
        (7,7,  'FLX0RFCLES', 'RFCL enable set'),
        (6,6,  'FLX0NMVCES', 'NMVC enable set'),
        (5,5,  'FLX0TI1ES',  'TI1 enable set'),
        (4,4,  'FLX0TI0ES',  'TI0 enable set'),
        (3,3,  'FLX0TIBCES', 'TIBC enable set'),
        (2,2,  'FLX0TOBCES', 'TOBC enable set'),
        (1,1,  'FLX0SWEES',  'SWE enable set'),
        (0,0,  'FLX0SUCSTES','SUCST enable set'),
    ]),
    ('FLX0SIER', 0x003C, 'Status interrupt enable reset',       32, RW,  '0x00000000', [
        (17,17,'FLX0CLMTSAER','CLMTSA enable reset'),
        (16,16,'FLX0CLWUPAER','CLWUPA enable reset'),
        (15,15,'FLX0WUPBFER','WUPBF enable reset'),
        (14,14,'FLX0MTSBER', 'MTSB enable reset'),
        (13,13,'FLX0MTSAER', 'MTSA enable reset'),
        (12,12,'FLX0WSTAFER','WSTAF enable reset'),
        (11,11,'FLX0CYCSER', 'CYCS enable reset'),
        (10,10,'FLX0TXIER',  'TXI enable reset'),
        (9,9,  'FLX0RXIER',  'RXI enable reset'),
        (8,8,  'FLX0RFNEER', 'RFNE enable reset'),
        (7,7,  'FLX0RFCLER', 'RFCL enable reset'),
        (6,6,  'FLX0NMVCER', 'NMVC enable reset'),
        (5,5,  'FLX0TI1ER',  'TI1 enable reset'),
        (4,4,  'FLX0TI0ER',  'TI0 enable reset'),
        (3,3,  'FLX0TIBCER', 'TIBC enable reset'),
        (2,2,  'FLX0TOBCER', 'TOBC enable reset'),
        (1,1,  'FLX0SWEER',  'SWE enable reset'),
        (0,0,  'FLX0SUCSTER','SUCST enable reset'),
    ]),
    ('FLX0ILE',  0x0040, 'Interrupt line enable',               32, RW,  '0x00000000', [
        (1,1,'FLX0EINT1','Interrupt line 1 enable'),
        (0,0,'FLX0EINT0','Interrupt line 0 enable'),
    ]),
    ('FLX0T0C',  0x0044, 'Timer 0 configuration',               32, RW,  '0x00000000', [
        (26,26,'FLX0T0RC','Timer 0 repetition bit'),
        (25,24,'FLX0T0MS','Timer 0 mode select'),
        (22,16,'FLX0T0CC','Timer 0 cycle code'),
        (13,0, 'FLX0T0MO','Timer 0 macrotick offset'),
    ]),
    ('FLX0T1C',  0x0048, 'Timer 1 configuration',               32, RW,  '0x00020000', [
        (17,17,'FLX0T1RC','Timer 1 repetition bit'),
        (16,16,'FLX0T1MS','Timer 1 mode select'),
        (12,0, 'FLX0T1MC','Timer 1 macrotick count'),
    ]),
    ('FLX0STPW1',0x004C, 'Stop watch register 1',               32, RW,  '0x00000000', [
        (17,17,'FLX0ESWT','Enable stop watch trigger'),
        (16,16,'FLX0SWMS','Stop watch mode select'),
        (13,8, 'FLX0SWCC','Stop watch cycle code'),
        (5,0,  'FLX0SWCV','Stop watch comparison value'),
    ]),
    ('FLX0STPW2',0x0050, 'Stop watch register 2',               32, RO,  '0x00000000', [
        (29,16,'FLX0STMTV','Stop watch captured macrotick value'),
        (13,8, 'FLX0STCCV','Stop watch captured cycle counter value'),
    ]),
]

# ---- CC control registers ----
REGS += [
    ('FLX0SUCC1',0x0080, 'SUC configuration register 1',        32, RW,  '0x0C401080', [
        (27,27,'FLX0CCHB','Connected to channel B'),
        (26,26,'FLX0CCHA','Connected to channel A'),
        (25,25,'FLX0MTSB_S','Select channel B for MTS transmission'),
        (24,24,'FLX0MTSA_S','Select channel A for MTS transmission'),
        (23,23,'FLX0HCSE','Halt due to clock sync error'),
        (22,22,'FLX0TSM', 'Transmission slot mode'),
        (21,21,'FLX0WUCS','Wakeup channel select'),
        (20,16,'FLX0PTA', 'Passive to active'),
        (15,11,'FLX0CSA', 'Cold start attempts'),
        (9,9,  'FLX0TXSY','Transmit sync frame in key slot'),
        (8,8,  'FLX0TXST','Transmit startup frame in key slot'),
        (7,7,  'FLX0PBSY','POC busy'),
        (3,0,  'FLX0CMD', 'CHI command vector'),
    ]),
    ('FLX0SUCC2',0x0084, 'SUC configuration register 2',        32, RW,  '0x01000504', [
        (27,24,'FLX0LTN','Listen timeout noise'),
        (20,0, 'FLX0LT', 'Listen timeout'),
    ]),
    ('FLX0SUCC3',0x0088, 'SUC configuration register 3',        32, RW,  '0x00000011', [
        (7,4,'FLX0WCP','Wakeup CAS pattern repetitions'),
        (3,0,'FLX0WCF','Wakeup counter during first gap'),
    ]),
    ('FLX0NEMC', 0x008C, 'NEM configuration register',          32, RW,  '0x00000000', [
        (3,0,'FLX0NML','Network management vector length'),
    ]),
    ('FLX0PRTC1',0x0090, 'PRT configuration register 1',        32, RW,  '0x084C0633', [
        (31,28,'FLX0BRP',  'Baud rate prescaler'),
        (26,24,'FLX0SPPW', 'Samples per bit window'),
        (22,16,'FLX0SPP',  'Samples per bit'),
        (14,8, 'FLX0CASM', 'CAS/MTS symbol length'),
        (5,0,  'FLX0TSSY', 'Transmission start sequence length'),
    ]),
    ('FLX0PRTC2',0x0094, 'PRT configuration register 2',        32, RW,  '0x0F2D0A0E', [
        (31,24,'FLX0RXI','RX to idle delay'),
        (22,16,'FLX0RXL','RX low idle delay'),
        (13,8, 'FLX0TXI_D','TX to idle delay'),
        (5,0,  'FLX0TXL','TX low idle delay'),
    ]),
    ('FLX0MHDC', 0x0098, 'MHD configuration register',          32, RW,  '0x00000000', [
        (28,16,'FLX0SLT', 'Static slot transmit buffer'),
        (6,0,  'FLX0SFDL','Static frame data length'),
    ]),
    ('FLX0GTUC01',0x00A0,'GTU configuration register 1',        32, RW,  '0x00000280', [
        (19,0,'FLX0UT','Microtick per cycle'),
    ]),
    ('FLX0GTUC02',0x00A4,'GTU configuration register 2',        32, RW,  '0x0002000A', [
        (19,16,'FLX0SNM','Sync node max'),
        (13,0, 'FLX0MPC','Macrotick per cycle'),
    ]),
    ('FLX0GTUC03',0x00A8,'GTU configuration register 3',        32, RW,  '0x02020000', [
        (31,24,'FLX0UIOA','Microtick initial offset channel A'),
        (23,16,'FLX0UIOB','Microtick initial offset channel B'),
        (14,8, 'FLX0MIOA','Macrotick initial offset channel A'),
        (6,0,  'FLX0MIOB','Macrotick initial offset channel B'),
    ]),
    ('FLX0GTUC04',0x00AC,'GTU configuration register 4',        32, RW,  '0x00080007', [
        (18,8,'FLX0NIT','Network idle time start'),
        (6,0, 'FLX0OCS','Offset correction start'),
    ]),
    ('FLX0GTUC05',0x00B0,'GTU configuration register 5',        32, RW,  '0x0E000000', [
        (28,16,'FLX0DCA','Delay compensation channel A'),
        (12,0, 'FLX0DCB','Delay compensation channel B'),
    ]),
    ('FLX0GTUC06',0x00B4,'GTU configuration register 6',        32, RW,  '0x00020000', [
        (19,0,'FLX0ASR','Accepted startup range'),
    ]),
    ('FLX0GTUC07',0x00B8,'GTU configuration register 7',        32, RW,  '0x00020004', [
        (18,8,'FLX0SSL','Static slot length'),
        (6,0, 'FLX0NSS','Number of static slots'),
    ]),
    ('FLX0GTUC08',0x00BC,'GTU configuration register 8',        32, RW,  '0x00000002', [
        (13,8,'FLX0MSL','Minislot length'),
        (5,0, 'FLX0NMS','Number of minislots'),
    ]),
    ('FLX0GTUC09',0x00C0,'GTU configuration register 9',        32, RW,  '0x00000101', [
        (12,8,'FLX0APO', 'Action point offset'),
        (4,0, 'FLX0MAPO','Minislot action point offset'),
    ]),
    ('FLX0GTUC10',0x00C4,'GTU configuration register 10',       32, RW,  '0x00020005', [
        (18,8,'FLX0MOC','Maximum offset correction'),
        (5,0, 'FLX0MRC','Maximum rate correction'),
    ]),
    ('FLX0GTUC11',0x00C8,'GTU configuration register 11',       32, RW,  '0x00000000', [
        (8,8, 'FLX0ECAS','External clock correction channel A select'),
        (7,0, 'FLX0EDCR','External delay correction'),
    ]),
]

# ---- CC status registers ----
REGS += [
    ('FLX0CCSV', 0x0100, 'CC status vector',                    32, RO,  '0x00104000', [
        (31,29,'FLX0WSV',  'Wakeup status'),
        (28,28,'FLX0RCA',  'Remaining cold start attempts'),
        (27,26,'FLX0SLM',  'Slot mode'),
        (23,22,'FLX0CSNI', 'Cold start noise indicator'),
        (21,20,'FLX0CSAI', 'Cold start abort indicator'),
        (19,19,'FLX0CSI',  'Cold start inhibit'),
        (17,17,'FLX0HRQ',  'Halt request'),
        (16,16,'FLX0FSI',  'Freeze status indicator'),
        (14,14,'FLX0CCPBSY','POC busy'),
        (13,8, 'FLX0POCS', 'POC state'),
    ]),
    ('FLX0CCEV', 0x0104, 'CC error vector',                     32, RO,  '0x00000000', [
        (19,18,'FLX0ERRM', 'Error mode'),
        (15,10,'FLX0LTVC', 'Listen timeout violation counter'),
        (9,8,  'FLX0OFCR', 'Offset correction failed counter'),
        (5,0,  'FLX0CCFC', 'Clock correction failed counter'),
    ]),
    ('FLX0SCV',  0x0110, 'Slot counter value',                  32, RO,  '0x00000000', [
        (21,10,'FLX0SCCA','Slot counter channel A'),
        (9,0,  'FLX0SCCB','Slot counter channel B'),
    ]),
    ('FLX0MTCCV',0x0114, 'Macrotick and cycle counter value',   32, RO,  '0x00000000', [
        (21,16,'FLX0CCV','Cycle counter value'),
        (13,0, 'FLX0MTV','Macrotick value'),
    ]),
    ('FLX0RCV',  0x0118, 'Rate correction value',               32, RO,  '0x00000000', [
        (10,0,'FLX0RCVVAL','Rate correction value'),
    ]),
    ('FLX0OCV',  0x011C, 'Offset correction value',             32, RO,  '0x00000000', [
        (18,0,'FLX0OCVVAL','Offset correction value'),
    ]),
    ('FLX0SFS',  0x0120, 'Sync frame status',                   32, RO,  '0x00000000', [
        (15,12,'FLX0VSAE','Valid sync frames even channel A'),
        (11,8, 'FLX0VSBE','Valid sync frames even channel B'),
        (7,4,  'FLX0VSAO','Valid sync frames odd channel A'),
        (3,0,  'FLX0VSBO','Valid sync frames odd channel B'),
    ]),
    ('FLX0SWNIT',0x0124, 'Symbol window and NIT status',        32, RO,  '0x00000000', [
        (25,25,'FLX0SESA','Syntax error symbol window channel A'),
        (24,24,'FLX0SBSA','Slot boundary violation symbol window channel A'),
        (23,23,'FLX0TCSA','Transmission conflict symbol window channel A'),
        (17,17,'FLX0SESB','Syntax error symbol window channel B'),
        (16,16,'FLX0SBSB','Slot boundary violation symbol window channel B'),
        (15,15,'FLX0TCSB','Transmission conflict symbol window channel B'),
        (9,9,  'FLX0SENA','Syntax error NIT channel A'),
        (8,8,  'FLX0SBNA','Slot boundary violation NIT channel A'),
        (1,1,  'FLX0SENB','Syntax error NIT channel B'),
        (0,0,  'FLX0SBNB','Slot boundary violation NIT channel B'),
    ]),
    ('FLX0ACS',  0x0128, 'Aggregated channel status',           32, RW,  '0x00000000', [
        (23,23,'FLX0CEDBE','Content error detected channel B even'),
        (22,22,'FLX0SEDBE','Slot boundary violation channel B even'),
        (21,21,'FLX0CIBE', 'Content error in boundary channel B'),
        (20,20,'FLX0SBVBE','Slot boundary violation channel B'),
        (19,19,'FLX0CEDAE','Content error detected channel A even'),
        (18,18,'FLX0SEDAE','Slot boundary violation channel A even'),
        (17,17,'FLX0CIAE', 'Content error in boundary channel A'),
        (16,16,'FLX0SBVAE','Slot boundary violation channel A'),
    ]),
]

# ESID01..15 at 0x0130..0x0168 (step 4, 15 regs)
for m in range(1, 16):
    offset = 0x0130 + (m-1)*4
    REGS.append((
        f'FLX0ESID{m:02d}', offset,
        f'Even sync ID register {m:02d}',
        32, RO, '0x00000000',
        [
            (15,15,f'FLX0RXEB{m:02d}','Sync frame received on channel B'),
            (14,14,f'FLX0RXEA{m:02d}','Sync frame received on channel A'),
            (9,0,  f'FLX0EID{m:02d}', 'Even sync ID'),
        ]
    ))

# OSID01..15 at 0x0170..0x01A8 (step 4, 15 regs)
for m in range(1, 16):
    offset = 0x0170 + (m-1)*4
    REGS.append((
        f'FLX0OSID{m:02d}', offset,
        f'Odd sync ID register {m:02d}',
        32, RO, '0x00000000',
        [
            (15,15,f'FLX0RXOB{m:02d}','Sync frame received on channel B odd'),
            (14,14,f'FLX0RXOA{m:02d}','Sync frame received on channel A odd'),
            (9,0,  f'FLX0OID{m:02d}', 'Odd sync ID'),
        ]
    ))

# NMV1..3 at 0x01B0..0x01B8 (step 4, 3 regs)
for m in range(1, 4):
    offset = 0x01B0 + (m-1)*4
    REGS.append((
        f'FLX0NMV{m}', offset,
        f'Network management vector register {m}',
        32, RO, '0x00000000',
        [(31,0,f'FLX0NM{m}D','Network management vector data')]
    ))

# ---- Message buffer control registers ----
REGS += [
    ('FLX0MRC',  0x0300, 'Message RAM configuration',           32, RW,  '0x01800000', [
        (26,26,'FLX0SPLM','Single payload limit mode'),
        (25,24,'FLX0SEC', 'Static frame ID rejection'),
        (23,16,'FLX0LCB', 'Last configured buffer'),
        (15,8, 'FLX0FFB', 'First FIFO buffer'),
        (7,0,  'FLX0FDB', 'First dynamic buffer'),
    ]),
    ('FLX0FRF',  0x0304, 'FIFO rejection filter',               32, RW,  '0x01800000', [
        (26,26,'FLX0RNF', 'Reject null frames'),
        (25,24,'FLX0RSS', 'Reject sync segment frames'),
        (10,0, 'FLX0RFID','Receive FIFO frame ID rejection'),
    ]),
    ('FLX0FRFM', 0x0308, 'FIFO rejection filter mask',          32, RW,  '0x00000000', [
        (10,0,'FLX0RFIDM','FIFO frame ID rejection mask'),
    ]),
    ('FLX0FCL',  0x030C, 'FIFO critical level',                 32, RW,  '0x00000080', [
        (7,0,'FLX0CL','FIFO critical level'),
    ]),
]

# ---- Message buffer status registers ----
REGS += [
    ('FLX0MHDS', 0x0310, 'Message handler status',              32, RW,  '0x00000000', [
        (31,31,'FLX0PIBF','Payload input buffer full'),
        (30,30,'FLX0FMBD','Faulty message buffer detected'),
        (29,29,'FLX0MFMB','Maximum FIFO message buffer'),
        (28,28,'FLX0CRAM','Clear RAM active'),
        (27,27,'FLX0FMB', 'Faulty message buffer'),
        (23,16,'FLX0MBT', 'Message buffer transmit'),
        (7,0,  'FLX0MBU', 'Message buffer update'),
    ]),
    ('FLX0LDTS', 0x0314, 'Last dynamic transmit slot',          32, RO,  '0x00000000', [
        (20,10,'FLX0LDTA','Last dynamic transmit slot channel A'),
        (9,0,  'FLX0LDTB','Last dynamic transmit slot channel B'),
    ]),
    ('FLX0FSR',  0x0318, 'FIFO status register',                32, RO,  '0x00000000', [
        (25,25,'FLX0RFOV','Receive FIFO overrun'),
        (23,16,'FLX0RFFL','Receive FIFO fill level'),
        (7,0,  'FLX0RFAI','Receive FIFO access index'),
    ]),
    ('FLX0MHDF', 0x031C, 'Message handler constraints flags',   32, RW,  '0x00000000', [
        (6,6,'FLX0WAHPE', 'Write access to header partition error'),
        (5,5,'FLX0DTBFBE','Data transmit buffer full error channel B'),
        (4,4,'FLX0DTBFAE','Data transmit buffer full error channel A'),
        (3,3,'FLX0FNFBE', 'FIFO not free channel B error'),
        (2,2,'FLX0FNFAE', 'FIFO not free channel A error'),
        (1,1,'FLX0SNUBE', 'Sync node undefined error channel B'),
        (0,0,'FLX0SNUAE', 'Sync node undefined error channel A'),
    ]),
    ('FLX0TXRQ1',0x0320, 'Transmission request 1',              32, RO,  '0x00000000', [
        (31,0,'FLX0TXR031','Transmission request bits 031:000'),
    ]),
    ('FLX0TXRQ2',0x0324, 'Transmission request 2',              32, RO,  '0x00000000', [
        (31,0,'FLX0TXR063','Transmission request bits 063:032'),
    ]),
    ('FLX0TXRQ3',0x0328, 'Transmission request 3',              32, RO,  '0x00000000', [
        (31,0,'FLX0TXR095','Transmission request bits 095:064'),
    ]),
    ('FLX0TXRQ4',0x032C, 'Transmission request 4',              32, RO,  '0x00000000', [
        (31,0,'FLX0TXR127','Transmission request bits 127:096'),
    ]),
    ('FLX0NDAT1',0x0330, 'New data 1',                          32, RO,  '0x00000000', [
        (31,0,'FLX0ND031','New data bits 031:000'),
    ]),
    ('FLX0NDAT2',0x0334, 'New data 2',                          32, RO,  '0x00000000', [
        (31,0,'FLX0ND063','New data bits 063:032'),
    ]),
    ('FLX0NDAT3',0x0338, 'New data 3',                          32, RO,  '0x00000000', [
        (31,0,'FLX0ND095','New data bits 095:064'),
    ]),
    ('FLX0NDAT4',0x033C, 'New data 4',                          32, RO,  '0x00000000', [
        (31,0,'FLX0ND127','New data bits 127:096'),
    ]),
    ('FLX0MBSC1',0x0340, 'Message buffer status changed 1',     32, RO,  '0x00000000', [
        (31,0,'FLX0MBC031','Message buffer status changed bits 031:000'),
    ]),
    ('FLX0MBSC2',0x0344, 'Message buffer status changed 2',     32, RO,  '0x00000000', [
        (31,0,'FLX0MBC063','Message buffer status changed bits 063:032'),
    ]),
    ('FLX0MBSC3',0x0348, 'Message buffer status changed 3',     32, RO,  '0x00000000', [
        (31,0,'FLX0MBC095','Message buffer status changed bits 095:064'),
    ]),
    ('FLX0MBSC4',0x034C, 'Message buffer status changed 4',     32, RO,  '0x00000000', [
        (31,0,'FLX0MBC127','Message buffer status changed bits 127:096'),
    ]),
]

# ---- Identification registers ----
REGS += [
    ('FLX0CREL', 0x03F0, 'Core release register',               32, RO,  '0x10271031', [
        (31,28,'FLX0REL', 'Core release'),
        (27,20,'FLX0STEP','Core step'),
        (19,16,'FLX0YEAR','Core release year'),
        (15,8, 'FLX0MON', 'Core release month'),
        (7,0,  'FLX0DAY', 'Core release day'),
    ]),
    ('FLX0ENDN', 0x03F4, 'Endian register',                     32, RO,  '0x87654321', [
        (31,0,'FLX0ETV','Endian test value'),
    ]),
]

# ---- Input buffer: WRDSm (m=01..64) at 0x0400..0x04FC ----
for m in range(1, 65):
    offset = 0x0400 + (m-1)*4
    REGS.append((
        f'FLX0WRDS{m:02d}', offset,
        f'Write data section register {m:02d}',
        32, RW, '0x00000000',
        [(31,0,f'FLX0DW{m:02d}','Data word')]
    ))

REGS += [
    ('FLX0WRHS1',0x0500, 'Write header section 1',              32, RW,  '0x00000000', [
        (29,29,'FLX0WHMBI', 'Message buffer interrupt enable'),
        (28,28,'FLX0WHTXM', 'Transmission mode'),
        (27,27,'FLX0WHPPIT','Payload preamble indicator transmit'),
        (26,26,'FLX0WHCFG', 'Buffer direction TX/RX'),
        (25,25,'FLX0WHCHB', 'Channel B assignment'),
        (24,24,'FLX0WHCHA', 'Channel A assignment'),
        (22,16,'FLX0WHCYC', 'Cycle counter filter'),
        (10,0, 'FLX0WHFID', 'Frame ID'),
    ]),
    ('FLX0WRHS2',0x0504, 'Write header section 2',              32, RW,  '0x00000000', [
        (22,16,'FLX0WHCRC','Header CRC'),
        (6,0,  'FLX0WHPLC','Payload length configured'),
    ]),
    ('FLX0WRHS3',0x0508, 'Write header section 3',              32, RW,  '0x00000000', [
        (6,0,'FLX0WHDP','Data pointer'),
    ]),
    ('FLX0IBCM', 0x0510, 'Input buffer command mask',           32, RW,  '0x00000000', [
        (5,5,'FLX0LHSH','Write header section to IBF'),
        (4,4,'FLX0LDSH','Write data section to IBF'),
        (3,3,'FLX0STXR','Set transmission request'),
    ]),
    ('FLX0IBCR', 0x0514, 'Input buffer command request',        32, RW,  '0x00000000', [
        (15,15,'FLX0IBSYH','Input buffer host busy'),
        (14,14,'FLX0IBSYS','Input buffer shadow busy'),
        (6,0,  'FLX0IBRH', 'Input buffer request host side'),
    ]),
]

# ---- Output buffer: RDDSm (m=01..64) at 0x0600..0x06FC ----
for m in range(1, 65):
    offset = 0x0600 + (m-1)*4
    REGS.append((
        f'FLX0RDDS{m:02d}', offset,
        f'Read data section register {m:02d}',
        32, RO, '0x00000000',
        [(31,0,f'FLX0RDW{m:02d}','Read data word')]
    ))

REGS += [
    ('FLX0RDHS1',0x0700, 'Read header section 1',               32, RO,  '0x00000000', [
        (29,29,'FLX0RHMBI', 'Message buffer interrupt'),
        (28,28,'FLX0RHTXM', 'Transmission mode'),
        (27,27,'FLX0RHPPIT','Payload preamble indicator'),
        (26,26,'FLX0RHCFG', 'Buffer direction'),
        (25,25,'FLX0RHCHB', 'Channel B assignment'),
        (24,24,'FLX0RHCHA', 'Channel A assignment'),
        (22,16,'FLX0RHCYC', 'Cycle counter filter'),
        (10,0, 'FLX0RHFID', 'Frame ID'),
    ]),
    ('FLX0RDHS2',0x0704, 'Read header section 2',               32, RO,  '0x00000000', [
        (22,16,'FLX0RHCRC','Header CRC'),
        (14,8, 'FLX0RHPLR','Payload length received'),
        (6,0,  'FLX0RHPLC','Payload length configured'),
    ]),
    ('FLX0RDHS3',0x0708, 'Read header section 3',               32, RO,  '0x00000000', [
        (28,16,'FLX0RHRCC','Receive cycle count'),
        (6,0,  'FLX0RHDP', 'Data pointer'),
    ]),
    ('FLX0MBS',  0x070C, 'Message buffer status',               32, RO,  '0x00000000', [
        (7,7,'FLX0MBSEDE', 'ECC double error detected'),
        (6,6,'FLX0MBSSCE', 'Single cycle error'),
        (5,5,'FLX0MBSCEOB','Content error odd channel B'),
        (4,4,'FLX0MBSCEOA','Content error odd channel A'),
        (3,3,'FLX0MBSVFRB','Valid frame received channel B'),
        (2,2,'FLX0MBSVFRA','Valid frame received channel A'),
        (1,1,'FLX0MBSFSEB','Frame start error B'),
        (0,0,'FLX0MBSFSEA','Frame start error A'),
    ]),
    ('FLX0OBCM', 0x0710, 'Output buffer command mask',          32, RW,  '0x00000000', [
        (2,2,'FLX0RDSS','Read data section from OBF'),
        (1,1,'FLX0RHSS','Read header section from OBF'),
    ]),
    ('FLX0OBCR', 0x0714, 'Output buffer command request',       32, RW,  '0x00000000', [
        (15,15,'FLX0OBSYS','Output buffer shadow busy'),
        (14,14,'FLX0OBSYH','Output buffer host busy'),
        (9,9,  'FLX0VIEW', 'Select view'),
        (8,8,  'FLX0OBREQ','Transfer request'),
        (6,0,  'FLX0OBRS', 'Output buffer request shadow'),
    ]),
]

# ============================================================
# ECC registers: E7AxCTL (x=0..6)
# These are NOT in the FLX0 peripheral - they live at separate addresses
# Base address: FF46_4000H for E7A0CTL, stepping by 0x100 each
# We emit them as a separate peripheral ECC_FLX
# ============================================================

ECC_REGS = []
ECC_BASE = 0xFF464000
for x in range(7):
    abs_addr = ECC_BASE + x * 0x100
    ECC_REGS.append((
        f'E7A{x}CTL', abs_addr - ECC_BASE,
        f'FlexRay ECC{x} control register',
        32, RW, None,
        [
            (10,10,f'E7A{x}CTLER2C', 'ECC error clear bit'),
            (2,2,  f'E7A{x}CTLECCER2','ECC error flag'),
        ]
    ))

# ============================================================
# SVD generation
# ============================================================

def esc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def reg_xml(sym, offset, name, size, access, reset, fields, indent=4):
    ind = '  ' * indent
    ind1 = '  ' * (indent+1)
    ind2 = '  ' * (indent+2)
    ind3 = '  ' * (indent+3)
    lines = []
    lines.append(f'{ind}<register>')
    lines.append(f'{ind1}<name>{sym}</name>')
    lines.append(f'{ind1}<description>{esc(name)}</description>')
    lines.append(f'{ind1}<addressOffset>0x{offset:04X}</addressOffset>')
    lines.append(f'{ind1}<size>{size}</size>')
    lines.append(f'{ind1}<access>{access}</access>')
    if reset is not None:
        lines.append(f'{ind1}<resetValue>{reset}</resetValue>')
    if fields:
        lines.append(f'{ind1}<fields>')
        for (msb, lsb, fname, fdesc) in fields:
            lines.append(f'{ind2}<field>')
            lines.append(f'{ind3}<name>{fname}</name>')
            lines.append(f'{ind3}<description>{esc(fdesc)}</description>')
            lines.append(f'{ind3}<bitRange>[{msb}:{lsb}]</bitRange>')
            lines.append(f'{ind2}</field>')
        lines.append(f'{ind1}</fields>')
    lines.append(f'{ind}</register>')
    return '\n'.join(lines)

def peripheral_xml(pname, pdesc, base, addr_block_size, regs_list):
    lines = []
    lines.append(f'<peripheral>')
    lines.append(f'  <name>{pname}</name>')
    lines.append(f'  <description>{esc(pdesc)}</description>')
    lines.append(f'  <baseAddress>0x{base:08X}</baseAddress>')
    lines.append(f'  <addressBlock>')
    lines.append(f'    <offset>0x0</offset>')
    lines.append(f'    <size>0x{addr_block_size:04X}</size>')
    lines.append(f'    <usage>registers</usage>')
    lines.append(f'  </addressBlock>')
    lines.append(f'  <registers>')
    for r in regs_list:
        sym, offset, name, size, access, reset, fields = r
        lines.append(reg_xml(sym, offset, name, size, access, reset, fields))
    lines.append(f'  </registers>')
    lines.append(f'</peripheral>')
    return '\n'.join(lines)

# ============================================================
# Validation
# ============================================================

def validate(regs, label):
    offsets_seen = {}
    names_seen = set()
    errors = []
    for r in regs:
        sym, offset = r[0], r[1]
        if sym in names_seen:
            errors.append(f'  DUPLICATE NAME: {sym}')
        names_seen.add(sym)
        if offset in offsets_seen:
            errors.append(f'  DUPLICATE OFFSET 0x{offset:04X}: {sym} vs {offsets_seen[offset]}')
        offsets_seen[offset] = sym
    if errors:
        print(f'VALIDATION ERRORS in {label}:')
        for e in errors:
            print(e)
    else:
        print(f'{label}: {len(regs)} registers, no duplicates')
    return errors

errors1 = validate(REGS, 'FLX0')
errors2 = validate(ECC_REGS, 'ECC_FLX')

# ============================================================
# Write SVD
# ============================================================

# FLX0 base = 0xFF580000
FLX0_BASE = 0xFF580000

# Highest register offset in FLX0 is 0x0714 (OBCR) + 4 bytes = 0x0718
FLX0_SIZE = 0x0718

# ECC base = 0xFF464000, highest is E7A6CTL at offset 0x600, size 4 => 0x604
ECC_BASE_ADDR = ECC_BASE
ECC_SIZE = 0x604

out_path = 'C:/Users/dudei/Desktop/Projects/firmware-analysis-kit/analysis-2020accord/_svd_parts/section24_flexray.svd'

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('<!-- Section 24 FlexRay (FLX) - V850E2/Px4 UPD70F3508 -->\n')
    f.write('<!-- FLX0 base: 0xFF580000 (Table 24-2) -->\n')
    f.write('<!-- ECC_FLX base: 0xFF464000 (E7A0CTL..E7A6CTL) -->\n')
    f.write('\n')

    # FLX0 regs: convert to 7-tuples (strip the reset formatting)
    flx_regs_clean = []
    for r in REGS:
        sym, offset, name, size, access, reset_str, fields = r
        flx_regs_clean.append((sym, offset, name, size, access, reset_str, fields))

    f.write(peripheral_xml(
        'FLX0',
        'FlexRay controller 0 (E-Ray)',
        FLX0_BASE,
        FLX0_SIZE,
        flx_regs_clean
    ))
    f.write('\n\n')

    # ECC peripheral
    ecc_regs_clean = []
    for r in ECC_REGS:
        sym, offset, name, size, access, reset_str, fields = r
        ecc_regs_clean.append((sym, offset, name, size, access, reset_str, fields))

    f.write(peripheral_xml(
        'ECC_FLX',
        'FlexRay ECC error control registers (E7A0CTL..E7A6CTL)',
        ECC_BASE_ADDR,
        ECC_SIZE,
        ecc_regs_clean
    ))
    f.write('\n')

print(f'Written to {out_path}')

# ============================================================
# Validate XML well-formedness
# ============================================================
import xml.etree.ElementTree as ET
with open(out_path, encoding='utf-8') as f:
    content = f.read()

try:
    ET.fromstring('<r>' + content + '</r>')
    print('XML well-formedness: PASS')
except ET.ParseError as e:
    print(f'XML well-formedness: FAIL -- {e}')

# Summary
print()
print('=== SUMMARY ===')
print(f'Peripherals emitted: 2 (FLX0, ECC_FLX)')
print(f'FLX0 base address: 0x{FLX0_BASE:08X}')
print(f'ECC_FLX base address: 0x{ECC_BASE_ADDR:08X}')
print(f'FLX0 registers: {len(REGS)}')
print(f'ECC_FLX registers: {len(ECC_REGS)}')
print(f'Total registers: {len(REGS)+len(ECC_REGS)}')
print()
print('Skipped (reserved ranges):')
print('  0x000C: Reserved (1 register)')
print('  0x0018: Reserved (1 register)')
print('  0x0054-0x007C: Reserved (11 registers)')
print('  0x009C: Reserved (1 register)')
print('  0x00CC-0x00FC: Reserved (14 registers)')
print('  0x0108-0x010C: Reserved (2 registers)')
print('  0x012C: Reserved (1 register)')
print('  0x016C: Reserved (1 register)')
print('  0x01AC: Reserved (1 register)')
print('  0x01BC-0x02FC: Reserved (81 registers)')
print('  0x0350-0x03EC: Reserved (41 registers)')
print('  0x03F8-0x03FC: Reserved (2 registers)')
print('  0x050C: Reserved (1 register)')
print('  0x0518-0x05FC: Reserved (59 registers)')
print('  0x0718-0x07FC: Reserved (59 registers)')
print()
print('FLXnVI vendor-specific initial value 0x01050004 used (Table 24-3).')
