# 07 - Power input, protection and "back-EMF protection"

Why you care: most dead motor controllers die from their *power supply side*:
a reversed battery, a hot-plug spark, or the motor pumping the bus voltage
above the MOSFET rating while braking.

---

## 1. The power entry chain

```
 Battery ──[connector]──[fuse?]──[reverse protection?]──┬──[TVS]──┬── DC bus ──► bridge
                                                       │         │
                                                   [bulk caps]  [MLCC bank]
                                                       │
                                                       └──► buck ──► 5 V / 3.3 V logic
```

The clone boards (DM: box 2-3, 3GIMD: box 5-7, GIM: box 6-7) all show the
same pattern: **XT30 connector -> a large bank of MLCCs (+ a TVS on the 3GIMD)**.
They have **two XT30s** (DM board) to daisy-chain power between joints.

---

## 2. Connectors

- **XT30**: ~15 A continuous, higher short peaks. XT60 for more. The Amass
  connectors on all three clone boards are XT30 (2-pin right-angle PCB type).
- Keyed connectors are your first reverse-polarity protection.
- Signal connectors: JST GH (1.25 mm, locking) is the robotics standard for
  CAN/UART/encoder. The clone boards use GH/ZH-style white connectors.

---

## 3. Reverse-polarity protection - and the regen trap

| Method | Loss at 20 A | Regen can flow back? | Notes |
|--------|--------------|----------------------|-------|
| Series diode | 0.5-0.8 V × 20 A = 10-16 W | **No** | Never for the motor bus. |
| P-MOSFET high-side | I²R, small | Yes (MOSFET conducts both ways when on) | Simple, gate from GND via resistor + Zener clamp to protect Vgs. |
| N-MOSFET low-side (in the GND return) | I²R, small | Yes | Gate from +V via resistor + Zener; cheapest effective method. Ground of board ≠ battery negative by a few mV. |
| **Ideal-diode controller** (LM74700, LM74610) + N-FET | Tiny | **No** - blocks reverse current | Great for logic rails, **bad for a motor bus** because regen current cannot return to the battery -> bus pumps up. |
| Back-to-back FETs with a controller (LM74800, LM5069 hot-swap) | Small | Configurable | Also gives inrush control and eFuse behaviour. Most complex. |
| None (rely on keyed connector) | 0 | Yes | What many compact actuators do (all the clone boards appear to). |

**Key lesson**: a reverse-polarity "diode" (real or ideal) in the motor bus
stops regenerative braking energy from going back to the battery. Either use
a MOSFET that conducts both ways when on (P-FET / N-FET in GND), or accept a
keyed connector only.

A simple, very robust choice for a first board: **N-MOSFET in the ground
return**, gate pulled to +24 V through ~100 kΩ, **Zener 12-15 V from gate to
source** to keep Vgs safe. Reverse battery -> gate is negative -> FET off.

---

## 4. Zener vs TVS - what "zener diodes" are really for here

- **Zener** (e.g. BZT52 series, ~0.3-0.5 W): clamps *small* currents.
  Uses on your board: protecting MOSFET gates (Vgs clamp in the
  reverse-polarity circuit), clamping analog inputs, simple references.
  Cannot absorb power spikes.
- **TVS** (Hello, I want to create my own actuator based on bldc motor. For reference I will start with 8110 frameless motor 24V. I want to design my own controll board for it based on esp32-s3. For this, at first, I need to learn what does great robotic actuator control board have on it. Including controll mosfets, communication intarfaces, temperature sensors, magnetic encoder, power protecting units(zener diods, etc), back emf protection, maybe cooling, current sensing, test pads, led indicators, component place manegment, noise protection, etc. For this in PACB/Learning create me some files teaching all that stuff(including how does individual components behave, e.g. I might do not knwo specific of how mosfets behave at high frequencies, or something like that, or even dont knwo basics of how current measurement works). Additionally to text learning you can make some simple interactive tutorials/demonstration for some electrical behavior, motor behaviour, etc, but keep it simple stupid :)
Dont touch other folders for now(dont add anything o them). You can look at specification for framless motor I am planning to use at @CAD/References/WK8110-2D-Drawing.pdf and some opensource pcb design for something that looks like actuator controller for bldc motor at @PCB/References/IRAMX-drv-v3.3brd.pdf @PCB/References/IRAMX-drv-v3.3sch.pdf 
Also I was able to land some hands physically on soe sort of SteadyWin clones and I have photos of their PCBs in @PCB/References/ 
Ideally, after tutorials and before making my own I should fully understand what are on nthat pcb and why it there and what it does. You can copy those images and draw over them(highlight components) or use them in similar way to explain something. 

For context: I am interested in best way to controll motor with great precision, so FOC or PID, or otehr will be used and good feedback is needed, so maybe a few types of feedback will be used simultaniously.  Additionally, I want ability to flash my esp32 from type-c(along with outputtting to serial throught that usb) and that type-c port should be on controller.

SMBJ = 600 W, SMCJ = 1500 W, SMDJ = 3000 W *peak* for a 10/1000 µs
  pulse): designed to absorb **short** energy spikes - hot-plug overshoot,
  ESD, cable inductive kicks. The big diode next to the 3GIMD power input
  (box 6) is this.

TVS numbers for a 24 V bus (example class: SMCJ28A or SMCJ30A):

| Parameter | Approx | Meaning |
|-----------|--------|---------|
| V_WM (standoff) | 28-30 V | Must be above your max normal bus (a "24 V" 6S LiPo is 25.2 V full; 7S = 29.4 V!). |
| V_BR (breakdown) | 31-35 V | Starts conducting. |
| V_C (clamping) | 45-50 V | Voltage during a big surge. **Must be below MOSFET V_DS(max)** -> this is why 60 V FETs. |

A TVS is **not** a regen solution: if the motor dumps energy continuously, the
TVS overheats and fails (usually short -> then the fuse/battery decides what
happens). It only handles microsecond-millisecond events.

---

## 5. Back-EMF / regenerative braking ("bus pumping")

When the motor decelerates (or the robot pushes the joint), the motor acts as
a generator. FOC with negative torque at positive speed sends energy **into**
the DC bus.

- **Battery supply**: the battery absorbs it (usually fine, within its charge
  current limits). Make sure nothing in the path blocks reverse current (§3).
- **Lab power supply**: most cannot sink current -> the energy charges your
  bus capacitors -> voltage rises fast.

How fast? Capacitor energy: E = ½ C V². Raising 100 µF from 24 V to 40 V takes
only ½ × 100 µF × (40² - 24²) = **0.05 J**. A small actuator rotor + gearbox
spinning at speed easily stores 0.5-5 J. -> **The bus would go way past 60 V
and kill the FETs** in milliseconds.

Solutions (from most to least robust):

1. **Run from a battery** (or a PSU with a sink/shunt regulator).
2. **Brake chopper**: a power resistor + MOSFET across the bus, switched on
   by the MCU (or a comparator) when Vbus > threshold. This is what ODrive's
   "brake resistor" does. Needs a resistor that can take the energy.
3. **Firmware regen limit**: measure Vbus every cycle; limit negative power
   (reduce braking torque) as Vbus rises; trip/disable at an over-voltage
   threshold. Some firmwares dissipate energy in the motor itself by injecting
   extra Id current (heats windings instead of pumping the bus).
4. **TVS** as the last line of defence for fast spikes.

> Demo: [interactive/06_regen_bus_pump.html](interactive/06_regen_bus_pump.html)

Note: the "BRAKE" outputs on the STMBL board (Q3, IRLML6344 + flyback diode)
and the "Brake" pads on the 3GIMD board are for a **holding brake** (an
electromagnetic brake that mechanically locks the shaft when unpowered), not
a braking resistor. Different thing, same word! A holding brake coil is an
inductor -> its switch needs a **flyback diode** (D3/D4 on STMBL) - the same
inductive-kick physics as module 01.

---

## 6. Inrush and hot-plugging

Plugging an XT30 into a charged battery with tens of µF of MLCCs:

- Huge inrush current (sparks, connector pitting).
- The cable inductance + MLCCs form an LC tank with almost no damping -> the
  bus can **ring up to ~2× the battery voltage** (24 V -> ~48 V peak!).

Mitigation:

- **One electrolytic/polymer cap with some ESR** on the bus (e.g. 100-470 µF
  35-50 V) damps the LC ringing. That's often its main job, not the µF.
- TVS clamp.
- Anti-spark connectors (XT90-S) or a **precharge/eFuse/hot-swap controller**
  that ramps the bus slowly. Optional for a first board, but plan for the
  TVS + damping cap.

---

## 7. Bulk capacitance: how much?

The DC-bus caps supply the **ripple current** that the battery wires cannot
(due to inductance). Rough sizing:

- Ripple current RMS ≈ 0.5 × phase current (worst case at ~50 % modulation).
  20 A phase -> ~10 A RMS ripple. Spread across many caps: each MLCC 1210 can
  take a few A RMS, electrolytics ~1-2 A each (check datasheet).
- Voltage ripple ΔV ≈ I / (8 × C × f) ballpark. With 20 A, 20 kHz, 50 µF
  *effective* (after DC-bias derating!) -> ~2.5 V... add more C or accept it.
- Typical small actuator: **8-15 × 10 µF/50 V MLCC (1206/1210)** spread across
  the half-bridges + optionally 1-2 × 100-220 µF polymer/electrolytic near the
  input. Compare: DM board ~25 MLCCs (box 3), GIM ~10 large MLCCs (box 6).

Placement: a few MLCCs **right at each half-bridge** (loop inductance!), the
rest near the input.

---

## 8. Logic power tree

What needs power on your board:

| Rail | Consumer | Typical current |
|------|----------|-----------------|
| 10-12 V (VDRV) | Gate driver (some drivers make it themselves with a charge pump from VM) | 10-50 mA |
| 5 V | CAN transceiver (many need 5 V), USB VBUS input | 50-100 mA |
| 3.3 V | ESP32-S3 (**peaks ~350-500 mA during Wi-Fi TX**), encoder, CSA bias, LEDs | 150-600 mA |

Rules:

- **Don't drop 24 V -> 3.3 V with an LDO**: at 200 mA that's 4 W of heat. Use a
  **buck converter** (24 V -> 5 V or directly -> 3.3 V), then optionally an LDO
  for a cleaner analog 3.3 V. The GIM board does exactly this (L1 "150" + D1
  Schottky = buck, box 5; L2 another stage, box 4).
- Choose a buck rated for **≥ 40-60 V input** (regen and spikes reach the
  buck too).
- A buck converter is itself a switching noise source: keep its hot loop small
  (input cap - switch - diode) and away from analog sensing.
- **Ferrite bead + LDO** to make a quiet "AVDD" for the encoder and ADC reference.
- **USB power OR-ing**: let VBUS (5 V from the USB-C cable) power the logic so
  you can flash/debug without 24 V. Use a Schottky diode (or an ideal-diode IC)
  from VBUS and another from the on-board 5 V into the 3.3 V regulator input,
  so neither can back-feed the other. Module 08 has the details.

---

## 9. Over-voltage, under-voltage, over-current: who reacts and how fast

| Event | First responder | Speed |
|-------|-----------------|-------|
| Phase short / FET short | Gate driver VDS monitor -> disables gates | ~µs |
| Over-current (soft) | Firmware on ADC current | per PWM cycle (50 µs) |
| Bus over-voltage spike | TVS | ns |
| Sustained bus over-voltage (regen) | Firmware Vbus check -> brake chopper / reduce torque / trip | per cycle |
| Under-voltage (battery sag) | Gate driver UVLO + firmware | µs / ms |
| Over-temperature | NTCs -> firmware derating | seconds |
| Wiring short to ground outside | Fuse | ms |

Next: [08 Communication + USB-C](08_Communication_and_USB.md)
