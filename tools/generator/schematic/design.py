from gen import Design, build

d = Design()
R = 'Resistor_SMD:R_1206_3216Metric'
C = 'Capacitor_SMD:C_1206_3216Metric'
SOIC8 = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'


def r(sheet, group, val, a, b, mpn='', note=''):
    return d.add(sheet, group, 'Device:R', val, R, {1: a, 2: b}, 'R', mpn=mpn, note=note)


def c(sheet, group, val, a, b, note=''):
    return d.add(sheet, group, 'Device:C', val, C, {1: a, 2: b}, 'C', note=note)


S1, S2, S3, S4 = 'input.kicad_sch', 'channels.kicad_sch', 'control.kicad_sch', 'power.kicad_sch'
d.sheet(S1, 'Input and protection', 'DUT terminals, fuse, reverse-polarity diode, TVS, remote sense, hardware OVP/OTP')
d.sheet(S2, 'Power channels', '4 CC channels: setpoint, OPA2196 loop, linear MOSFET, Kelvin shunt, INA228')
d.sheet(S3, 'Control', 'Wemos D1 mini Pro (ESP8266), DAC8565, ARM/CLAMP logic, fan, NTC, front panel')
d.sheet(S4, 'Power supplies', '12 V auxiliary input, analog 5 V (78L05), 5 V buck for WiFi')

# =========================== FOGLIO 1: INGRESSO ===========================
def M(p, x, y, r=0, wired=()):
    p.pos, p.rot, p.wired = (x, y), r, set(map(str, wired))
    return p


D1 = d.draw[S1] = []
g = 'Input'
D1.append(('title', 'DUT terminals and power-path protection', 22, 34))
M(d.add(S1, g, 'Connector_Generic:Conn_01x01', 'DUT+', 'MountingHole:MountingHole_5.3mm_M5_Pad_Via', {1: 'DUT_P'}, 'J',
        note='M5 stud, 25 A'), 30.48, 50.8, 180, wired=[1])
M(d.add(S1, g, 'Device:Fuse', '25A ATO', 'Fuse:Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin', {1: 'DUT_P', 2: 'VLOAD'}, 'F',
        note='ATO blade fuse 25 A'), 48.26, 50.8, 90, wired=[1, 2])
D1.append(('wire', [(35.56, 50.8), (44.45, 50.8)]))
D1.append(('wire', [(52.07, 50.8), (63.5, 50.8), (86.36, 50.8), (106.68, 50.8), (124.46, 50.8)]))
D1.append(('label', 'VLOAD', 124.46, 50.8, (1, 0)))
for xx in (63.5, 86.36, 106.68):
    D1.append(('junc', xx, 50.8))
    D1.append(('wire', [(xx, 50.8), (xx, 54.61)]))
M(d.add(S1, g, 'Device:D_Schottky_AKA', 'VS-30CTQ100S', 'Package_TO_SOT_SMD:TO-263-2', {1: 'GND', 2: 'VLOAD', 3: 'GND'}, 'D',
        mpn='VS-30CTQ100SPbF', note='Reverse polarity: conducts and blows F1 (check I2t)'), 63.5, 58.42, 270, wired=[2])
M(d.add(S1, g, 'Device:D_TVS', 'SMCJ64CA', 'Diode_SMD:D_SMC', {1: 'VLOAD', 2: 'GND'}, 'D', mpn='SMCJ64CA'), 86.36, 58.42, 270, wired=[1])
M(c(S1, g, '100n 100V', 'VLOAD', 'GND', note='X7R'), 106.68, 58.42, wired=[1])
M(d.add(S1, g, 'Connector_Generic:Conn_01x01', 'DUT-', 'MountingHole:MountingHole_5.3mm_M5_Pad_Via', {1: 'GND'}, 'J',
        note='M5 stud, 25 A - ground star point'), 30.48, 68.58, 180)

D1.append(('title', 'Remote sense (voltage measured by the INA228s)', 22, 88))
M(d.add(S1, g, 'Connector:Screw_Terminal_01x02', 'SENSE', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',
        {1: 'SENSE_P_EXT', 2: 'SENSE_N_EXT'}, 'J', note='1=SENSE+ 2=SENSE-'), 30.48, 111.76, 180, wired=[1, 2])
M(r(S1, g, '100R', 'SENSE_P_EXT', 'VSENSE'), 45.72, 111.76, 90, wired=[1, 2])
D1.append(('wire', [(35.56, 111.76), (41.91, 111.76)]))
D1.append(('wire', [(49.53, 111.76), (58.42, 111.76), (68.58, 111.76), (78.74, 111.76), (91.44, 111.76)]))
D1.append(('label', 'VSENSE', 91.44, 111.76, (1, 0)))
for xx in (58.42, 68.58):
    D1.append(('junc', xx, 111.76))
    D1.append(('wire', [(xx, 111.76), (xx, 115.57)]))
M(d.add(S1, g, 'Device:D_TVS', 'SMAJ64CA', 'Diode_SMD:D_SMA', {1: 'VSENSE', 2: 'GND'}, 'D', mpn='SMAJ64CA'), 58.42, 119.38, 270, wired=[1])
M(c(S1, g, '10n 100V', 'VSENSE', 'GND'), 68.58, 119.38, wired=[1])
M(r(S1, g, '10k', 'VLOAD', 'VSENSE', note='Fallback when sense leads are not connected'), 78.74, 104.14, wired=[2])
D1.append(('wire', [(78.74, 107.95), (78.74, 111.76)]))
D1.append(('junc', 78.74, 111.76))
M(d.add(S1, g, 'Device:R', '10R', R, {1: 'GND', 2: 'SENSE_N_EXT'}, 'R', note='SENSE- referenced to ground only'), 38.1, 101.6, wired=[2])
D1.append(('wire', [(35.56, 109.22), (38.1, 109.22), (38.1, 105.41)]))

g = 'Reference'
D1.append(('title', '2.5 V reference and OVP / OTP comparators (open-collector outputs on ARM)', 22, 142.16))
M(r(S1, g, '1k', '+5V', 'VREF_2V5'), 35.56, 156.21, wired=[2])
tl = M(d.add(S1, g, 'Reference_Voltage:TL431D', 'TL431ID', SOIC8, {1: 'VREF_2V5', 2: 'GND', 3: 'GND', 6: 'GND', 7: 'GND', 8: 'VREF_2V5'},
             'U', mpn='TL431IDR', nc=('4', '5')), 35.56, 167.64, 90, wired=[1, 8])
D1.append(('wire', [(35.56, 160.02), (35.56, 162.56), (35.56, 165.1)]))
D1.append(('wire', [(33.02, 167.64), (30.48, 167.64), (30.48, 162.56), (35.56, 162.56)]))
D1.append(('junc', 35.56, 162.56))
D1.append(('wire', [(35.56, 162.56), (45.72, 162.56), (73.66, 162.56)]))
D1.append(('label', 'VREF_2V5', 45.72, 162.56, (0, -1)))
# OVP
M(r(S1, g, '10k', 'VREF_2V5', 'OVP_REF'), 73.66, 170.18, wired=[1, 2])
D1.append(('wire', [(73.66, 162.56), (73.66, 166.37)]))
D1.append(('wire', [(73.66, 173.99), (73.66, 177.8), (81.28, 177.8), (83.82, 177.8)]))
D1.append(('junc', 81.28, 177.8))
D1.append(('wire', [(81.28, 177.8), (81.28, 167.64), (85.09, 167.64)]))
M(r(S1, g, '1M', 'OVP_REF', 'ARM', note='OVP hysteresis'), 88.9, 167.64, 90, wired=[1, 2])
D1.append(('wire', [(92.71, 167.64), (101.6, 167.64), (101.6, 180.34)]))
cmp_ = M(d.add(S1, g, 'Comparator:LM393', 'LM393', SOIC8, {3: 'OVP_REF', 2: 'OVP_DIV', 1: 'ARM'}, 'U', unit=1, mpn='LM393DR'),
         91.44, 180.34, wired=[1, 2, 3])
D1.append(('wire', [(99.06, 180.34), (101.6, 180.34), (109.22, 180.34)]))
D1.append(('junc', 101.6, 180.34))
D1.append(('label', 'ARM', 109.22, 180.34, (1, 0)))
M(r(S1, g, '249k', 'VLOAD', 'OVP_DIV', note='1206 >= 200 V'), 60.96, 187.96, wired=[2])
M(r(S1, g, '10k', 'OVP_DIV', 'GND', note='0.1%'), 60.96, 200.66, wired=[1])
M(c(S1, g, '100n', 'OVP_DIV', 'GND'), 71.12, 200.66, wired=[1])
D1.append(('wire', [(60.96, 191.77), (60.96, 194.31), (60.96, 196.85)]))
D1.append(('wire', [(60.96, 194.31), (71.12, 194.31), (78.74, 194.31)]))
D1.append(('wire', [(71.12, 194.31), (71.12, 196.85)]))
D1.append(('junc', 60.96, 194.31))
D1.append(('junc', 71.12, 194.31))
D1.append(('wire', [(78.74, 194.31), (78.74, 182.88), (83.82, 182.88)]))
# OTP
D1.append(('label', 'NTC1', 147.32, 177.8, (-1, 0)))
D1.append(('wire', [(147.32, 177.8), (160.02, 177.8), (167.64, 177.8)]))
D1.append(('junc', 160.02, 177.8))
D1.append(('wire', [(160.02, 177.8), (160.02, 167.64), (168.91, 167.64)]))
M(r(S1, g, '1M', 'NTC1', 'ARM', note='OTP hysteresis'), 172.72, 167.64, 90, wired=[1, 2])
D1.append(('wire', [(176.53, 167.64), (185.42, 167.64), (185.42, 180.34)]))
M(d.add(S1, g, 'Comparator:LM393', 'LM393', SOIC8, {5: 'NTC1', 6: 'OTP_REF', 7: 'ARM'}, 'U', unit=2, ref=cmp_.ref),
  175.26, 180.34, wired=[5, 6, 7])
D1.append(('wire', [(182.88, 180.34), (185.42, 180.34), (193.04, 180.34)]))
D1.append(('junc', 185.42, 180.34))
D1.append(('label', 'ARM', 193.04, 180.34, (1, 0)))
M(r(S1, g, '100k', 'VREF_2V5', 'OTP_REF'), 152.4, 187.96, 90, wired=[1, 2])
D1.append(('wire', [(148.59, 187.96), (146.05, 187.96)]))
D1.append(('label', 'VREF_2V5', 146.05, 187.96, (-1, 0)))
D1.append(('wire', [(156.21, 187.96), (162.56, 187.96), (165.1, 187.96), (165.1, 182.88), (167.64, 182.88)]))
D1.append(('junc', 162.56, 187.96))
M(r(S1, g, '9k31', 'OTP_REF', 'GND', note='OTP threshold ~100 C'), 162.56, 195.58, wired=[1])
D1.append(('wire', [(162.56, 187.96), (162.56, 191.77)]))
D1.append(('text', 'OVP: trips at 2.5 V x (249k+10k)/10k = 64.7 V', 60.96, 215.16))
D1.append(('text', 'OTP: NTC 10k B3950 at ~100 C = 0.21 V < OTP_REF', 147.32, 215.16))
g = 'Comparator supply'
d.add(S1, g, 'Comparator:LM393', 'LM393', SOIC8, {8: '+5V', 4: 'GND'}, 'U', unit=3, ref=cmp_.ref)
c(S1, g, '100n', '+5V', 'GND')

# =========================== FOGLIO 2: CANALI ===========================
dac_out = ['DAC_A', 'DAC_B', 'DAC_C', 'DAC_D']
ina_a0 = ['GND', '+3V3', 'I2C_SDA', 'I2C_SCL']
opa = {}
d.draw[S2] = []
D = d.draw[S2]
for n in range(1, 5):
    ox = 5.08 if n in (1, 3) else 205.74
    y0 = 55.88 if n in (1, 2) else 125.73
    g = 'Channel %d' % n
    D.append(('title', 'Channel %d  -  0-5 A, 75 W  -  INA228 @0x%02X' % (n, 0x3F + n), ox + 12, y0 - 24))
    vset, fb, out, gate, src, shp, shn = ['%s%d' % (s_, n) for s_ in ('VSET', 'FB', 'OPOUT', 'GATE', 'SRC', 'SHP', 'SHN')]
    X = lambda v: ox + v
    # setpoint
    D.append(('label', dac_out[n - 1], X(17.78), y0, (-1, 0)))
    D.append(('wire', [(X(17.78), y0), (X(19.05), y0)]))
    r(S2, g, '24k 0.1%', dac_out[n - 1], vset, note='25:1 divider: 2.5 V -> 100 mV = 5 A').__dict__.update(pos=(X(22.86), y0), rot=90, wired={'1', '2'})
    D.append(('wire', [(X(26.67), y0), (X(31.75), y0), (X(46.99), y0), (X(54.61), y0), (X(68.58), y0)]))
    for xx in (31.75, 46.99, 54.61):
        D.append(('junc', X(xx), y0))
    r(S2, g, '1k 0.1%', vset, shn).__dict__.update(pos=(X(31.75), y0 + 7.62), wired={'1'})
    c(S2, g, '10n C0G', vset, shn, note='Setpoint filter 16.6 kHz (rev 0.2)').__dict__.update(pos=(X(46.99), y0 + 7.62), wired={'1'})
    D.append(('wire', [(X(31.75), y0), (X(31.75), y0 + 3.81)]))
    D.append(('wire', [(X(46.99), y0), (X(46.99), y0 + 3.81)]))
    D.append(('wire', [(X(54.61), y0), (X(54.61), y0 - 5.08)]))
    D.append(('label', vset, X(54.61), y0 - 5.08, (0, -1)))
    # op-amp
    unit = 1 if n % 2 else 2
    pmap = {3: vset, 2: fb, 1: out} if unit == 1 else {5: vset, 6: fb, 7: out}
    kw = dict(pos=(X(76.2), y0 + 2.54), wired=set(map(str, pmap)))
    if unit == 1:
        u = d.add(S2, g, 'Amplifier_Operational:OPA2196xD', 'OPA2196', SOIC8, pmap, 'U', unit=1, mpn='OPA2196IDR', **kw)
        opa[n] = u.ref
    else:
        d.add(S2, g, 'Amplifier_Operational:OPA2196xD', 'OPA2196', SOIC8, pmap, 'U', unit=2, ref=opa[n - 1], **kw)
    D.append(('wire', [(X(68.58), y0 + 5.08), (X(63.5), y0 + 5.08), (X(63.5), y0 + 12.7)]))
    r(S2, g, '1k', shp, fb).__dict__.update(pos=(X(58.42), y0 + 12.7), rot=90, wired={'1', '2'})
    D.append(('wire', [(X(62.23), y0 + 12.7), (X(63.5), y0 + 12.7), (X(69.85), y0 + 12.7)]))
    D.append(('junc', X(63.5), y0 + 12.7))
    D.append(('wire', [(X(54.61), y0 + 12.7), (X(54.61), y0 + 17.78)]))
    D.append(('label', shp, X(54.61), y0 + 17.78, (0, 1)))
    c(S2, g, '1n C0G', fb, out, note='Loop compensation rev 0.2: PM ~80 deg, BW 6-15 kHz').__dict__.update(pos=(X(73.66), y0 + 12.7), rot=90, wired={'1', '2'})
    D.append(('wire', [(X(77.47), y0 + 12.7), (X(86.36), y0 + 12.7), (X(86.36), y0 + 2.54)]))
    D.append(('wire', [(X(83.82), y0 + 2.54), (X(86.36), y0 + 2.54), (X(87.63), y0 + 2.54)]))
    D.append(('junc', X(86.36), y0 + 2.54))
    r(S2, g, '100R', out, gate).__dict__.update(pos=(X(91.44), y0 + 2.54), rot=90, wired={'1', '2'})
    D.append(('wire', [(X(95.25), y0 + 2.54), (X(99.06), y0 + 2.54), (X(101.6), y0 + 2.54)]))
    D.append(('junc', X(99.06), y0 + 2.54))
    r(S2, g, '10k', gate, 'GND').__dict__.update(textleft=True, pos=(X(99.06), y0 + 8.89), wired={'1'})
    D.append(('wire', [(X(99.06), y0 + 2.54), (X(99.06), y0 + 5.08)]))
    d.add(S2, g, 'eload:Q_NMOS_GDS', 'IXTH75N10L2', 'Package_TO_SOT_THT:TO-247-3_Horizontal_TabUp', {1: gate, 2: 'VLOAD', 3: src}, 'Q',
          mpn='IXTH75N10L2', note='Linear L2 MOSFET 100 V, under the PCB screwed to the spreader (common drain)',
          pos=(X(106.68), y0 + 2.54), wired={'1', '3'})
    D.append(('wire', [(X(109.22), y0 + 7.62), (X(109.22), y0 + 10.16)]))
    d.add(S2, g, 'Device:R_Shunt', '20m 1%', 'Resistor_SMD:R_Shunt_Vishay_WSK2512_6332Metric_T1.19mm',
          {1: src, 2: shp, 3: shn, 4: 'GND'}, 'R', mpn='WSK2512R0200FEA', note='4-terminal Kelvin shunt',
          pos=(X(109.22), y0 + 15.24), wired={'1', '2', '3'})
    D.append(('wire', [(X(111.76), y0 + 12.7), (X(120.65), y0 + 12.7), (X(127), y0 + 12.7)]))
    D.append(('label', shp, X(120.65), y0 + 12.7, (0, -1)))
    D.append(('wire', [(X(111.76), y0 + 17.78), (X(116.84), y0 + 17.78), (X(120.65), y0 + 17.78), (X(120.65), y0 + 15.24), (X(127), y0 + 15.24)]))
    D.append(('label', shn, X(120.65), y0 + 17.78, (0, 1)))
    d.add(S2, g, 'eload:INA228', 'INA228', 'Package_SO:MSOP-10_3x3mm_P0.5mm',
          {1: 'GND', 2: ina_a0[n - 1], 3: 'ARM', 4: 'I2C_SDA', 5: 'I2C_SCL', 6: '+3V3', 7: 'GND', 8: 'VSENSE', 9: shn, 10: shp},
          'U', mpn='INA228AIDGSR', note='ALERT open-drain on ARM (over-current / over-power)',
          pos=(X(137.16), y0 + 10.16), wired={'9', '10'})
    c(S2, g, '100n', '+3V3', 'GND').__dict__.update(pos=(X(175.26), y0 + 10.16))
g = 'Op-amp supply'
for n in (1, 3):
    d.add(S2, g, 'Amplifier_Operational:OPA2196xD', 'OPA2196', SOIC8, {8: '+12V', 4: 'GND'}, 'U', unit=3, ref=opa[n])
    c(S2, g, '100n 50V', '+12V', 'GND')
c(S2, g, '10u 25V', '+12V', 'GND')

# =========================== FOGLIO 3: CONTROLLO ===========================
g = 'WiFi module Wemos D1 mini Pro (ESP8266) on socket strips'
d.add(S3, g, 'Connector_Generic:Conn_01x08', 'D1mini L', 'Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
      {2: 'NTC1', 3: 'ARM_FB', 4: 'SPI_SCK', 5: 'ARM_DRV', 6: 'SPI_MOSI', 7: 'DAC_SYNC', 8: '+3V3'}, 'J',
      nc=('1',), note='RST A0 D0(GPIO16) D5(14) D6(12) D7(13) D8(15) 3V3; the module 3V3 powers the logic')
d.add(S3, g, 'Connector_Generic:Conn_01x08', 'D1mini R', 'Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
      {2: 'WEMOS_RX', 3: 'I2C_SCL', 4: 'I2C_SDA', 5: 'EXP_INT', 6: 'FAN_PWM_MCU', 7: 'GND', 8: '+5V_WIFI'}, 'J',
      nc=('1',), note='TX RX(GPIO3) D1(5) D2(4) D3(0)=expander INT D4(2) G 5V; GPIO0/2/15 = strapping')
r(S3, g, '1k', 'WEMOS_RX', 'FAN_TACH', note='Tach on RX: unplug the fan when programming over USB')
c(S3, g, '100n', '+3V3', 'GND')
c(S3, g, '10u 25V', '+3V3', 'GND')
r(S3, g, '2k2', '+3V3', 'I2C_SDA', note='Bus extended to the front panel (rev 0.3)')
r(S3, g, '2k2', '+3V3', 'I2C_SCL')

g = 'Front panel: I2C OLED, push encoder, OUTPUT button (rev 0.3)'
d.add(S3, g, 'Interface_Expansion:PCF8574T', 'PCF8574T', 'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm',
      {1: 'GND', 2: 'GND', 3: 'GND', 4: 'FP_ENC_A', 5: 'FP_ENC_B', 6: 'FP_ENC_SW', 7: 'FP_BTN_OUT', 8: 'GND',
       9: 'PCF_LED', 13: 'EXP_INT', 14: 'I2C_SCL', 15: 'I2C_SDA', 16: '+3V3'}, 'U', mpn='PCF8574T/3',
      nc=('10', '11', '12'), note='I2C expander @0x20; INT on GPIO0 (D3)')
c(S3, g, '100n', '+3V3', 'GND')
for net in ('FP_ENC_A', 'FP_ENC_B', 'FP_ENC_SW', 'FP_BTN_OUT'):
    r(S3, g, '10k', '+3V3', net)
    c(S3, g, '10n', net, 'GND', note='Debounce 100 us')
r(S3, g, '470R', 'PCF_LED', 'FP_LED', note='OUTPUT LED on the panel: anode to 3V3, cathode here')
d.add(S3, g, 'Connector_Generic:Conn_02x05_Odd_Even', 'FRONT PANEL', 'Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical',
      {1: '+3V3', 2: 'GND', 3: 'I2C_SDA', 4: 'GND', 5: 'I2C_SCL', 6: 'FP_ENC_A', 7: 'FP_ENC_B', 8: 'FP_ENC_SW',
       9: 'FP_BTN_OUT', 10: 'FP_LED'}, 'J', note='10-wire ribbon to the front panel: OLED SSD1309/SH1106 0x3C, EC11 encoder, OUTPUT button')
c(S3, g, '10u 25V', '+3V3', 'GND', note='OLED decoupling')
c(S3, g, '100n', '+3V3', 'GND')

g = 'Quad 16-bit DAC (internal 2.5 V reference)'
d.add(S3, g, 'Analog_DAC:DAC8565', 'DAC8565', 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm',
      {1: 'DAC_A', 2: 'DAC_B', 7: 'DAC_C', 8: 'DAC_D', 3: 'DAC_VREF', 4: '+5V', 5: 'GND', 6: 'GND', 9: 'DAC_SYNC', 10: 'SPI_SCK',
       11: 'SPI_MOSI', 12: '+3V3', 13: 'DAC_RST', 14: 'GND', 15: 'GND', 16: 'GND'}, 'U', mpn='DAC8565IAPW',
      note='RSTSEL=0: reset to zero scale; LDAC=0: synchronous update')
r(S3, g, '10k', '+3V3', 'DAC_RST')
c(S3, g, '100n', 'DAC_VREF', 'GND')
c(S3, g, '100n', '+5V', 'GND')
c(S3, g, '1u', '+5V', 'GND')
c(S3, g, '100n', '+3V3', 'GND')

g = 'ARM'
D3 = d.draw[S3] = []
D3.append(('title', 'ARM / CLAMP logic  (fail-safe: load off if the MCU is missing, in reset or faulty)', 22, 34))
D3.append(('label', 'ARM_DRV', 25.4, 63.5, (-1, 0)))
D3.append(('wire', [(25.4, 63.5), (27.94, 63.5)]))
M(r(S3, g, '1k', 'ARM_DRV', 'ARM'), 31.75, 63.5, 90, wired=[1, 2])
D3.append(('wire', [(35.56, 63.5), (43.18, 63.5), (50.8, 63.5), (58.42, 63.5), (81.28, 63.5)]))
for xx in (43.18, 50.8, 58.42):
    D3.append(('junc', xx, 63.5))
D3.append(('wire', [(43.18, 63.5), (43.18, 67.31)]))
D3.append(('wire', [(58.42, 63.5), (58.42, 67.31)]))
D3.append(('wire', [(50.8, 63.5), (50.8, 55.88)]))
D3.append(('label', 'ARM', 50.8, 55.88, (0, -1)))
M(r(S3, g, '10k', 'ARM', 'GND', note='Pull-down: ARM low = load disabled'), 43.18, 71.12, wired=[1])
M(r(S3, g, '100k', 'ARM', 'ARM_FB', note='ARM read-back: 100k, a GPIO driven at boot cannot arm the load'), 58.42, 71.12, wired=[1])
qa = M(d.add(S3, g, 'Transistor_FET:FDS9926A', 'FDS9926A', SOIC8, {2: 'ARM', 7: 'CLAMP', 8: 'CLAMP', 1: 'GND'}, 'Q', unit=1,
             mpn='FDS9926A', note='ARM -> CLAMP inverter'), 86.36, 63.5, wired=[2, 7, 8])
D3.append(('wire', [(88.9, 58.42), (88.9, 50.8), (96.52, 50.8), (104.14, 50.8)]))
D3.append(('junc', 96.52, 50.8))
D3.append(('label', 'CLAMP', 104.14, 50.8, (1, 0)))
M(r(S3, g, '10k', '+5V', 'CLAMP'), 96.52, 44.45, wired=[2])
D3.append(('wire', [(96.52, 48.26), (96.52, 50.8)]))
M(d.add(S3, g, 'Transistor_FET:FDS9926A', 'FDS9926A', SOIC8, {4: 'CLAMP', 5: 'VSET1', 6: 'VSET1', 3: 'GND'}, 'Q', unit=2, ref=qa.ref),
  132.08, 63.5)
qb = M(d.add(S3, g, 'Transistor_FET:FDS9926A', 'FDS9926A', SOIC8, {2: 'CLAMP', 7: 'VSET2', 8: 'VSET2', 1: 'GND'}, 'Q', unit=1,
             mpn='FDS9926A'), 157.48, 63.5)
M(d.add(S3, g, 'Transistor_FET:FDS9926A', 'FDS9926A', SOIC8, {4: 'CLAMP', 5: 'VSET3', 6: 'VSET3', 3: 'GND'}, 'Q', unit=2, ref=qb.ref),
  182.88, 63.5)
qc = M(d.add(S3, g, 'Transistor_FET:FDS9926A', 'FDS9926A', SOIC8, {2: 'CLAMP', 7: 'VSET4', 8: 'VSET4', 1: 'GND'}, 'Q', unit=1,
             mpn='FDS9926A'), 208.28, 63.5)
D3.append(('text', 'CLAMP high -> setpoints VSET1..4 shorted to ground', 124.46, 80))

g = '4-wire PWM fan and NTC sensors on the spreader'
d.add(S3, g, 'Transistor_FET:FDS9926A', 'FDS9926A', SOIC8, {4: 'FAN_PWM_G', 5: 'FAN_PWM', 6: 'FAN_PWM', 3: 'GND'}, 'Q', unit=2,
      ref=qc.ref, note='Open-drain fan PWM (inverted logic in firmware)')
r(S3, g, '100R', 'FAN_PWM_MCU', 'FAN_PWM_G')
r(S3, g, '100k', 'FAN_PWM_G', 'GND')
r(S3, g, '10k', '+3V3', 'FAN_TACH')
d.add(S3, g, 'Connector_Generic:Conn_01x04', 'FAN', 'Connector_Molex:Molex_KK-254_AE-6410-04A_1x04_P2.54mm_Vertical',
      {1: 'GND', 2: '+12V', 3: 'FAN_TACH', 4: 'FAN_PWM'}, 'J', note='12 V 4-wire fan (SP3/TR4 cooler)')
d.add(S3, g, 'Connector_Generic:Conn_01x04', 'NTC', 'Connector_Molex:Molex_KK-254_AE-6410-04A_1x04_P2.54mm_Vertical',
      {1: 'NTC1', 2: 'GND', 3: 'NTC2', 4: 'GND'}, 'J', note='2x NTC 10k B3950 glued to the spreader')
r(S3, g, '10k 0.1%', '+3V3', 'NTC1')
r(S3, g, '10k 0.1%', '+3V3', 'NTC2', note='NTC2 spare: the D1 mini has a single ADC (A0 = NTC1)')
c(S3, g, '100n', 'NTC1', 'GND')
c(S3, g, '100n', 'NTC2', 'GND')

# =========================== FOGLIO 4: ALIMENTAZIONE E USB ===========================
D4 = d.draw[S4] = []
g = 'Aux'
D4.append(('title', '12 V auxiliary input (dedicated isolated adaptor) and regulators', 22, 34))
M(d.add(S4, g, 'Connector:Barrel_Jack', '12V DC', 'Connector_BarrelJack:BarrelJack_Horizontal', {1: 'AUX_IN', 2: 'GND'}, 'J'),
  27.94, 50.8, wired=[1])
M(d.add(S4, g, 'Device:D_Schottky', 'SS34', 'Diode_SMD:D_SMA', {1: 'AUX_D', 2: 'AUX_IN'}, 'D', mpn='SS34'), 45.72, 48.26, 180, wired=[1, 2])
M(d.add(S4, g, 'Device:Polyfuse', '1.5A', 'Fuse:Fuse_1206_3216Metric', {1: 'AUX_D', 2: '+12V'}, 'F', note='PTC 1206, 1.5 A hold (WiFi buck + fan)'),
  57.15, 48.26, 90, wired=[1, 2])
D4.append(('wire', [(35.56, 48.26), (41.91, 48.26)]))
D4.append(('wire', [(49.53, 48.26), (53.34, 48.26)]))
D4.append(('wire', [(60.96, 48.26), (63.5, 48.26), (68.58, 48.26), (73.66, 48.26), (78.74, 48.26), (88.9, 48.26)]))
D4.append(('flag', 63.5, 48.26))
D4.append(('pwr', '+12V', 73.66, 48.26))
for xx in (68.58, 78.74):
    D4.append(('junc', xx, 48.26))
    D4.append(('wire', [(xx, 48.26), (xx, 52.07)]))
M(c(S4, g, '10u 25V', '+12V', 'GND'), 68.58, 55.88, wired=[1])
M(c(S4, g, '100n', '+12V', 'GND'), 78.74, 55.88, wired=[1])
M(d.add(S4, g, 'Regulator_Linear:L78L05_SO8', 'L78L05', SOIC8, {8: '+12V', 1: '+5V', 2: 'GND', 3: 'GND', 6: 'GND', 7: 'GND'}, 'U',
        mpn='L78L05ACD13TR'), 96.52, 48.26, wired=[8, 1])
D4.append(('wire', [(104.14, 48.26), (109.22, 48.26), (111.76, 48.26)]))
D4.append(('pwr', '+5V', 109.22, 48.26))
D4.append(('junc', 111.76, 48.26))
D4.append(('wire', [(111.76, 48.26), (111.76, 52.07)]))
M(c(S4, g, '1u', '+5V', 'GND'), 111.76, 55.88, wired=[1])
D4.append(('text', '+3V3 supplied by the Wemos module regulator (3V3 pin)', 121.92, 40.64))
D4.append(('pwr', '+3V3', 149.86, 48.26))
D4.append(('wire', [(149.86, 48.26), (154.94, 48.26), (165.1, 48.26)]))
D4.append(('junc', 154.94, 48.26))
D4.append(('wire', [(154.94, 48.26), (154.94, 52.07)]))
D4.append(('wire', [(165.1, 48.26), (165.1, 52.07)]))
M(c(S4, g, '10u 25V', '+3V3', 'GND'), 154.94, 55.88, wired=[1])
M(r(S4, g, '1k5', '+3V3', 'LED_PWR'), 165.1, 55.88, wired=[1, 2])
D4.append(('wire', [(165.1, 59.69), (165.1, 63.5)]))
M(d.add(S4, g, 'Device:LED', 'green', 'LED_SMD:LED_1206_3216Metric', {1: 'GND', 2: 'LED_PWR'}, 'D'), 165.1, 67.31, 90, wired=[2])
d.flags[S4] = ['GND', '+3V3']

g = 'Buck 12 V -> 5 V (AP63205) for the Wemos only: analog 5 V stays on the 78L05'
d.add(S4, g, 'Regulator_Switching:AP63205WU', 'AP63205WU', 'Package_TO_SOT_SMD:TSOT-23-6',
      {3: '+12V', 2: 'BUCK_EN', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST', 1: '+5V_WIFI'}, 'U', mpn='AP63205WU-7',
      note='FB tied to the 5 V output (fixed-output version)')
r(S4, g, '100k', '+12V', 'BUCK_EN')
c(S4, g, '10u 25V', '+12V', 'GND')
c(S4, g, '100n 50V', '+12V', 'GND')
c(S4, g, '100n 50V', 'BUCK_BST', 'BUCK_SW')
d.add(S4, g, 'Device:L', '6u8', 'Inductor_SMD:L_Bourns-SRN4018', {1: 'BUCK_SW', 2: '+5V_WIFI'}, 'L', mpn='SRN4018-6R8M')
c(S4, g, '22u 10V', '+5V_WIFI', 'GND')
c(S4, g, '22u 10V', '+5V_WIFI', 'GND')

d.origins[S3] = {'WiFi module Wemos D1 mini Pro (ESP8266) on socket strips': (20, 95, 235),
                 'Front panel: I2C OLED, push encoder, OUTPUT button (rev 0.3)': (20, 300, 390),
                 'Quad 16-bit DAC (internal 2.5 V reference)': (262, 95, 150),
                 '4-wire PWM fan and NTC sensors on the spreader': (20, 212, 390)}
d.origins[S1] = {'Comparator supply': (230, 142, 150)}
d.origins[S4] = {'Buck 12 V -> 5 V (AP63205) for the Wemos only: analog 5 V stays on the 78L05': (22, 100, 260)}

NOTES = [
    '#4-channel electronic load - 60 V / 20 A / 300 W',
    'Each channel: 0-5 A, max 75 W per MOSFET. Above 15 V the limit is power (300 W / V), enforced by firmware + INA228 ALERT.',
    'Setpoint: DAC8565 0-2.5 V -> 25:1 divider -> 0-100 mV on 20 mOhm shunt = 0-5 A. The divider is referenced to the cold Kelvin pad of the shunt (SHNx).',
    'ARM (active high, 10k pull-down) enables the load. LM393 (OVP 64.7 V, OTP ~100 C) and the INA228 ALERTs pull it low in hardware.',
    'ARM low -> CLAMP high -> clamp FETs short VSET1..4 to ground. MCU in reset = load off.',
    'Single GND = DUT- (star point at stud J2). Control over WiFi only; the Wemos USB is NOT isolated: use it only for programming with the DUT disconnected.',
    'ESP8266 firmware: after SPI.begin() re-assign GPIO12 as output (ARM_DRV); GPIO16 = ARM_FB; A0 = NTC1 (D1 mini internal 220k/100k divider).',
    'Front panel (rev 0.3): PCF8574 @0x20 (encoder A/B/SW, OUTPUT button, LED), INT on GPIO0; OLED @0x3C on the same bus. OUTPUT ON enables ARM, never automatic.',
    '#Exceptions to the SMD SOIC/SOP + 1206 passives rule',
    'TO-247 power MOSFETs (mounted on the spreader), WSK2512 Kelvin shunts, D2PAK reverse-polarity diode, SMC/SMA TVS,',
    'INA228 in VSSOP-10 (0.5 mm pitch), DAC8565 in TSSOP-16, AP63205 in TSOT-23-6, SRN4018 inductor, THT connectors.',
    '#To verify on the bench',
    'Wemos antenna off the board edge and away from the cooler (or external antenna on U.FL); CC loop stability analysed (C 1n C0G / R 1k / Rg 100R, rev 0.2), to confirm on the bench; D1 I2t vs F1; IXTH75N10L2 FBSOA at 60 V and Tc 90 C.',
]

if __name__ == '__main__':
    gl = build(d, '/home/claude/out/eload_4ch', 'Electronic Load 4ch 60V 20A 300W', '0.3', '2026-10-25', NOTES)
    print('parts', len(d.parts), 'global nets', sorted(gl))
