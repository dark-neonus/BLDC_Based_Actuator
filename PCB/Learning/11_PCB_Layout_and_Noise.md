# 11 - PCB layout, component placement and noise

Why you care: with the same schematic, a good layout gives clean current
readings and cool MOSFETs; a bad one gives resets, ringing and smoke. In
motor controllers **layout is part of the design**, not a drawing task.

---

## 1. Placement first, routing second

Order of placement for an actuator board:

1. **Mechanical constraints**: board outline (round, to fit the housing),
   mounting holes, the **encoder IC position (on the motor axis!)**, connector
   positions (power, CAN, USB-C must reach openings), height limits, where the
   board touches the housing for cooling.
2. **Power stage**: 3 half-bridges + their MLCCs + shunts, as a tight group at
   the board area that touches the housing. Motor phase pads right next to it.
3. **Power input**: connector -> TVS -> bulk caps -> bridges: a short, wide path.
4. **Gate driver** next to the FETs (≤ 10-15 mm to each gate).
5. **Current-sense amplifiers** right at the shunts (or the driver's CSAs if
   it's near enough).
6. **MCU** between the gate driver and the comms/USB side.
7. **Logic power** (buck/LDO) - near where its power enters, away from the
   encoder and CSAs.
8. **Comms connectors + transceivers** at the board edge, with ESD parts right
   at the connector.

Look at the clone photos: every one follows **power on one side, logic on the
other**, with the gate driver as the bridge in between.

```
   +------------------------------------------------+
   |  [XT30]   [TVS][bulk caps]                     |
   |                                                |
   |  [CAN/485 + ESD] [conn]        [HB U][HB V][HB W]  <- FETs + MLCCs + shunts
   |                                  [gate driver] |
   |   [USB-C]   [ESP32-S3]   [CSAs]  -------------- |
   |   [BOOT][RST]            [encoder IC on axis]  |  <- often bottom side
   |  [buck][LDO]  [LEDs] [test pads]   [NTC]       |
   +------------------------------------------------+
```

---

## 2. The three loops that matter

### Loop 1: power commutation loop (highest priority)

Bus MLCC -> high-side FET -> low-side FET (-> shunt) -> back to the MLCC ground.
This loop carries the fast dI/dt edges. **Make its area as small as possible**:

- MLCCs placed directly across each half-bridge.
- Best: "vertical loop" - FETs on the top layer, the return path on layer 2 (a
  solid ground plane right under them, separated by a thin prepreg).
- Many vias in parallel for every layer change.

### Loop 2: gate loops (6 of them)

Driver output -> gate resistor -> FET gate -> FET source -> back to the driver's
return pin (SHx for high side, GND/SLx for low side).

- Route gate and return **together, side by side or stacked on adjacent
  layers**.
- Short (a few mm to ~15 mm), 0.3-0.5 mm wide.

### Loop 3: measurement loops

Shunt Kelvin traces -> filter -> CSA -> ADC. Small, differential, away from
switch nodes, over solid ground. Encoder SPI near the MCU, away from phase
copper.

---

## 3. Layer stack

For a motor controller **4 layers** is the realistic minimum for good results
(2 layers works for low-current hobby boards but is much harder to make quiet).

| Layer | Use |
|-------|-----|
| L1 (top) | Components, power copper (thick, 2 oz if possible), short signals |
| L2 | **Solid GND plane** (do not cut it up) |
| L3 | Power (Vbus pour under the bridge, 3.3 V, 5 V) + some routing |
| L4 (bottom) | Encoder IC (facing the magnet), power copper/thermal pad to housing, routing |

6 layers with 2 oz outer layers is common on commercial actuator boards
(more copper for current and heat). Ask the fab for available stack-ups and
copper weights.

---

## 4. Copper sizing for high current

- Use **pours (polygons) on multiple layers** in parallel for Vbus, GND and each
  phase - not thin traces.
- Use a **trace width calculator** (IPC-2152). Rough: for 20 A continuous with
  a 20 °C rise, outer 2 oz copper needs ~5-7 mm width. Inner layers need more
  (they cool worse).
- **Via arrays**: ~1-2 A per 0.3 mm via; 20 A -> 15-20 vias between layers.
- **Exposed copper + solder** (solder-mask opening, then extra solder or
  copper bars): the tinned stripes on the DM board back side (photo 2, box 3)
  and 3GIMD (box 18) increase the current capacity of a track.

---

## 5. Ground: one plane, smart placement

- Use **one continuous ground plane**; avoid splitting into "AGND/PGND" islands
  unless you really know why. Instead, **place** so that the high-current
  return paths do not pass under the analog/encoder section.
- Return current follows the path of least **impedance**: at high frequency
  that's directly under the signal trace. Never route a signal over a gap in
  the plane.
- Connect the **star point for analog references** (CSA reference, ADC VREF)
  close to the shunt's ground side / the MCU's ground pins as recommended in
  the driver datasheet.
- **Stitching vias** around the board edge and between ground pours on
  different layers (the dense dot fields on the clone boards, photo 2 box 8)
  keep all layers' grounds at the same potential and reduce radiation.

---

## 6. Noise sources and victims

| Aggressor | Mechanism | Victim | Fix |
|-----------|-----------|--------|-----|
| Switch nodes (phase copper) | dV/dt -> capacitive coupling | CSA inputs, encoder SPI, ADC traces | Small switch-node area; ground between; distance |
| Commutation loops | dI/dt -> magnetic coupling | Any loop nearby, encoder IC | Tight loops; ground plane under |
| Buck converter | dI/dt + dV/dt | ADC, encoder, crystal | Tight buck layout, keep away from analog |
| Phase/bus current in traces | Magnetic field | **Magnetic encoder** | Keep high current away from the encoder; route forward/return currents together so fields cancel |
| Motor cables | Radiated, common-mode | CAN bus, USB | ESD/CM chokes at connectors; twisted cables |
| Gate drive edges | dV/dt | Nearby signals | Short gate loops |

Classic symptoms: ESP32 resets when the motor starts (supply/ground bounce),
current readings jumping at specific duty cycles (sampling during an edge),
encoder angle "jumping" at high current (magnetic field or SPI noise).

---

## 7. Other placement rules worth knowing

- **Decoupling caps** on the same side as the IC, closest to its pins, vias
  directly to the planes.
- **Crystal** (if bare chip) close to the MCU, with ground around it, nothing
  else routed underneath.
- **Thermal**: hot parts (FETs, shunts) near the housing contact; NTC on the
  same copper as the FETs; electrolytic caps away from heat (heat kills them).
- **Creepage/clearance**: at 24-60 V it's easy (0.2-0.5 mm), but keep more
  between Vbus and logic for robustness. (The STMBL board shows the extreme
  case: a physical **isolation gap** between low and high voltage halves,
  box 9.)
- **Test pads** for every important net (module 12), accessible when the
  board is mounted, if possible.
- **Silkscreen**: label connectors' pins, polarity (+/-), phases (U V W),
  board name/revision/date. The clone boards do this well ("15-60V", "485 120Ω
  CAN", "DIO GND DCK 3V3").
- **Fiducials** and panelisation if you will use a PCB assembly service.

---

## 8. A layout checklist you can actually tick

- [ ] Each half-bridge has ≥ 2 MLCCs directly across it, loop < ~10 mm²
- [ ] Solid GND plane on L2, no cuts under the power stage or analog
- [ ] Gate traces paired with their return, < 15 mm
- [ ] Shunt sense lines Kelvin-connected, routed as a pair to the CSA
- [ ] No high current within ~10 mm of the encoder IC
- [ ] Encoder IC exactly on the motor axis (mechanical dims from CAD)
- [ ] USB D+/D- as a 90 Ω pair, ESD at connector
- [ ] Buck converter compact and away from analog
- [ ] Thermal vias under every FET; bottom copper area for the housing pad
- [ ] Pull-downs on all PWM/EN lines
- [ ] Test pads on Vbus, 3V3, 5V, gate signals, CSA outputs, SPI, CAN, UART
- [ ] Silkscreen: pin labels, polarity, revision

Next: [12 Test, debug, indicators](12_Test_Debug_Indicators.md)
