# 12 - Test pads, debugging, LEDs and safe bring-up

Why you care: your first board *will* have mistakes. What decides whether you
find them in an hour or a week is how observable the board is, and whether
you test it in an order that doesn't destroy it.

---

## 1. Test pads / test points

A test pad is a small exposed copper pad (round, ~1-1.5 mm) on a net, where a
probe, pogo pin or wire can touch. Labelled "TP1", "TP3"... (GIM box 18 is TP3;
the STMBL schematic has TP1-TP21).

What deserves a test pad:

| Net | Why |
|-----|-----|
| Vbus, 12 V/VDRV, 5 V, 3.3 V, GND (several) | First thing to check at power-up |
| 6 gate signals (driver inputs), or at least the PWM lines | Verify dead time and timing on a scope |
| Switch nodes U, V, W | (usually accessible on the motor pads) |
| CSA outputs | See current waveforms, check offsets and sampling instant |
| Encoder SPI (CLK, MISO, CS) | Logic-analyser decoding |
| CAN_H / CAN_L, UART TX/RX | Bus debugging |
| nFAULT, EN | Why did it shut down? |
| A spare GPIO "debug pin" | Toggle it in firmware to measure ISR timing on a scope - extremely useful |
| GND next to every group | Short scope ground connection |

Tips:

- Put pads on the side accessible when the board is installed.
- A row of pads with 2.54 mm or 1.27 mm pitch lets you use a pogo-pin jig or
  a "Tag-Connect" style cable for programming (the 4 gold dots on the 3GIMD,
  box 15, and on the DM board, box 12, are programming/debug pads).
- Every probing point needs a nearby **ground** for a short scope ground
  spring - long ground leads on a scope show fake ringing.

---

## 2. Programming and debug access on your ESP32-S3 board

- **USB-C** (USB Serial/JTAG) - main path for flashing, logs and JTAG debugging
  (OpenOCD/GDB can debug the S3 through the same USB cable).
- **UART0 pads** (GPIO43 TX, GPIO44 RX, GND, 3V3) - backup.
- **BOOT (GPIO0) and RESET (EN) buttons** - or at least pads you can short
  with tweezers. Buttons are worth it on rev A.

---

## 3. LED indicators

Cheap, and they tell you a lot without a computer.

| LED | Meaning |
|-----|---------|
| Power (on 3.3 V, via resistor) | Logic power is present |
| Status (MCU GPIO) | Heartbeat blink = firmware alive; patterns for states |
| Fault (MCU GPIO or driver nFAULT) | Red = fault / disabled |
| Optional: CAN activity | Blink on traffic |

- The DM board has a small LED, the GIM has D6 (box 17), the 3GIMD has small
  LEDs near the connectors, and the STMBL has green/red/yellow on both sides.
- A single **WS2812/SK6812 RGB LED** on one GPIO gives many colours/states -
  but it needs 5 V (or a 3.3 V-tolerant variant) and timing-critical driving
  (RMT peripheral on the S3 handles that).
- Series resistor for a normal LED: R = (3.3 V - Vf) / I; for 2 mA with a
  green LED (Vf ~ 2.2 V) -> ~560 Ω. Modern LEDs are bright at 1-2 mA.

---

## 4. Configuration inputs

- **DIP switch / solder jumpers** for CAN ID and termination (DM box 10, 3GIMD
  box 3). Alternative: store the ID in flash and set it over USB - saves board
  space.

---

## 5. Safe bring-up procedure (do it in this order!)

Equipment: a **current-limited bench supply**, multimeter, oscilloscope
(even a cheap one), optionally a logic analyser. Wear eye protection for the
first power stage tests - MOSFETs and caps can burst.

1. **Visual inspection** under magnification: solder bridges on fine-pitch
   parts, rotated diodes/ICs, missing parts.
2. **Resistance checks unpowered**: Vbus-GND, 3V3-GND, 5V-GND not shorted
   (a few hundred Ω to kΩ is normal with ICs; < 10 Ω is a problem).
3. **Logic only**: power from USB-C (or a 5 V input), FET bus disconnected if
   possible. Check 3.3 V, flash a blink + serial "hello". Read the encoder
   (rotate magnet by hand, print angle). Read the gate driver's SPI registers.
   Check CAN loopback.
4. **Bus power with current limit ~100-200 mA**, motor **disconnected**, PWM
   disabled. Check current draw (should be small), check all rails, check the
   gate driver reports no fault.
5. **PWM, no motor**: enable PWM at 50 % duty. Scope the switch nodes: clean
   square waves 0-Vbus? Check dead time on gate signals. Measure CSA outputs
   (should be at the bias voltage ~1.65 V with no current).
6. **Motor connected, low current limit (0.5-1 A)**, open-loop: apply a slowly
   rotating voltage vector (low amplitude). Motor should turn smoothly.
   Verify encoder direction and pole pairs.
7. **Current sensing**: compare CSA readings with the bench supply current and
   with a clamp meter if available. Check sign and phase order.
8. **Closed-loop current (torque) control** at low limits; then velocity; then
   position.
9. **Raise limits gradually**, watch temperatures (thermal camera or
   thermocouple), watch Vbus during braking (regen!). Only then use a battery
   or high-current supply.

Rules during testing:

- Use a **bench supply that can't sink current** + regen = over-voltage. Start
  with gentle decelerations and watch Vbus, or add a large capacitor / brake
  resistor on the bench.
- Keep the motor mechanically free (no load, no gearbox) until the control
  loops are stable. A runaway position loop with a gearbox can break things or
  fingers.
- Have a **physical kill switch** on the 24 V line.

Next: [13 Reference boards explained](13_Reference_Boards_Explained.md)
