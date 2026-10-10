# 14 - Your board: from learning to a spec

This turns modules 00-13 into a concrete **starting specification** for an
ESP32-S3 controller for the WK8110 at 24 V. It is a proposal to argue with,
not a final design - measure your motor first and adjust.

---

## 1. Things to find out before drawing anything

| Item | How | Why |
|------|-----|-----|
| Pole pairs | Count magnets / DC-hold test (module 02 §1) | Firmware + encoder needs |
| Phase resistance, inductance | Bench supply 4-wire / LCR meter | Current loop tuning, ripple, PWM frequency |
| Kv / Kt | Spin with a drill, scope the back-EMF | Torque per amp, max speed at 24 V |
| Peak / continuous current target | From your torque requirements and the motor's thermal limit | Sizes FETs, shunts, copper, caps |
| Supply | Battery (6S/7S?) or PSU | Regen handling, TVS choice |
| Mechanical envelope | From CAD: board diameter, height, screw positions, **magnet position**, connector exits, housing contact area | Placement |
| Gearbox + output encoder? | Mechanical design | Second encoder connector |

---

## 2. Proposed architecture (rev A)

```
 24 V (XT30) ─► reverse-protection N-FET (GND side) ─► TVS (~SMCJ30A class) ─► bulk + MLCC bank ─► 3 half-bridges (6× 60 V PDFN5x6, ~1.5-3 mΩ)
                                                                                    │
                                                         3× low-side shunts (1-2 mΩ, 2512, Kelvin)
                                                                                    │
                                     DRV8323RS-class smart gate driver (CSAs, VDS OCP, SPI, nFAULT)
                                                                                    │
 ESP32-S3-MINI-1(U) / WROOM-1(U) ◄──────── PWM (MCPWM), SPI, nFAULT->MCPWM fault, EN ┘
     │  ADC1: Ia, Ib, Ic, Vbus, NTC_FET, NTC_motor
     │  SPI:  motor encoder (on-axis magnetic, e.g. MT6835 / AS5047P / MA732) on the board's motor side
     │  Connector: 2nd (output) encoder - 3V3, GND, SPI or I²C
     │  TWAI ─► CAN transceiver (TCAN1042/TJA1051-class) ─► 2× JST-GH (daisy-chain) + switchable 120 Ω + ESD
     │  USB Serial/JTAG (GPIO19/20) ─► USB-C (5.1 k on CC1 and CC2, ESD, VBUS OR-ing)
     │  UART0 pads, BOOT + RESET buttons, status + fault LEDs, debug GPIO pad
     └  Optional footprint: external simultaneous-sampling SPI ADC (module 10 §3, option C)

 Logic power: 24 V ─► buck (≥ 60 V input rated) ─► 5 V ─┬─► CAN transceiver
                                         USB VBUS ─(OR)─┴─► 3.3 V LDO or buck ─► ESP32-S3, encoder (via ferrite + LDO for quiet AVDD)
```

Why these choices (short version):

- **DRV8323RS-class driver**: CSAs, protection and fault reporting for free,
  massive community knowledge (MIT Cheetah controller, many open-source
  boards). Check the max voltage (60 V class) vs your regen margin; the
  DRV8353RS (100 V) is the higher-margin sibling.
- **Low-side shunts**: work with the driver's CSAs, simple, proven. (Inline +
  INA240 is the upgrade path for top current quality.)
- **60 V FETs on 24 V**: margin for regen and spikes.
- **CAN**: robot-actuator standard; ESP32-S3 TWAI + transceiver.
- **USB-C with native USB Serial/JTAG**: flashing, serial and JTAG over one
  cable, no bridge chip.

---

## 3. Requirements checklist

### Power
- [ ] Bus voltage range defined (e.g. 18-30 V operating, 40 V abs max on everything)
- [ ] Reverse polarity protection that still allows regen (or a conscious decision to rely on the keyed connector)
- [ ] TVS: V_WM above max battery voltage, V_C below FET/driver/buck max
- [ ] Bulk capacitance with DC-bias derating considered; ≥ 2 MLCCs at each half-bridge
- [ ] One damping electrolytic/polymer cap against hot-plug ringing
- [ ] Regen strategy: battery + firmware Vbus limit (+ optional brake chopper footprint)
- [ ] Logic buck rated ≥ 60 V input; 3.3 V ≥ 500 mA
- [ ] USB VBUS OR-ed with on-board 5 V, no back-feed

### Power stage
- [ ] 6 × 60 V N-MOSFETs, Rds(on) chosen for loss budget at hot temperature
- [ ] Gate resistors (or IDRIVE setting) + gate pull-downs; footprint for turn-off diodes
- [ ] Bootstrap caps sized; max duty limited in firmware
- [ ] Optional RC snubber footprints across low-side FETs

### Sensing
- [ ] 2-3 phase current channels, Kelvin routed, filtered, on ADC1 pins
- [ ] Vbus divider on ADC1
- [ ] NTC on FET copper + motor NTC connector
- [ ] Motor encoder on axis with keep-out zone; magnet holder design agreed with CAD
- [ ] Second-encoder connector
- [ ] Optional external SPI ADC footprint

### Control / MCU
- [ ] Pin map spreadsheet done, strapping/flash/PSRAM pins avoided
- [ ] Pull-downs on all PWM and EN lines
- [ ] nFAULT -> MCPWM fault input and GPIO interrupt
- [ ] BOOT + RESET buttons, EN RC delay

### Comms
- [ ] CAN transceiver + 2 connectors + switchable 120 Ω + ESD
- [ ] USB-C: CC1/CC2 5.1 kΩ each, ESD array, 90 Ω pair, connector reachable in the housing
- [ ] UART0 pads

### Debug / production
- [ ] Test pads: Vbus, 5 V, 3V3, GND×n, PWM×6, CSA outputs, SPI, CAN, UART, nFAULT, debug GPIO
- [ ] LEDs: power, status, fault
- [ ] Silkscreen: polarity, phases, pin names, board name + revision
- [ ] Fiducials, assembly-friendly parts (JLCPCB/PCBWay basic parts list helps)

### Layout / thermal (module 11 checklist)
- [ ] 4-layer minimum, solid GND on L2, 2 oz outer if possible
- [ ] Power on the housing-contact side, thermal vias, insulated thermal pad
- [ ] Power far from encoder and CSAs; logic buck away from analog

---

## 4. Suggested learning-by-doing path before the real board

1. **Buy a dev board + cheap driver** (e.g. a SimpleFOC Mini/Shield or any
   DRV8313/DRV8323 breakout) and run your WK8110 open-loop, then with an
   encoder, from an ESP32-S3 DevKitC. You will learn the firmware side and
   validate pole pairs/encoder/magnet setup while you design.
2. Scope your switch nodes and CSA outputs on that setup - see the theory
   from modules 03-05 in real life.
3. Draw your schematic in blocks matching module 00, review it against this
   checklist and against the reference boards.
4. Order rev A with **extra footprints** (snubbers, turn-off diodes, external
   ADC, test pads). Populating optional parts is cheap; adding missing
   footprints means a new board.

Good open-source designs to read next: moteus r4 (hardware docs), MIT
Mini Cheetah motor controller (Ben Katz), ODrive v3.6 schematics, SimpleFOC
boards, and the TI DRV8323 evaluation module (DRV8323RS-EVM) user guide.
