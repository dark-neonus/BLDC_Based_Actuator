# 08 - Communication interfaces and USB-C

Why you care: an actuator in a robot lives on a bus with many others, near
noisy motors, on long cables. The interface must survive that, and you also
want painless flashing/debugging through USB-C.

---

## 1. Why differential buses

A single-ended signal (UART TX referenced to GND) gets corrupted when the
ground at the two ends differs - and in a robot, motor currents in the
ground wires guarantee that. **Differential** buses (CAN, RS-485, USB) send
the signal as the *difference* between two wires; noise coupled equally into
both cancels out. Twisted pair wiring makes the coupling equal.

---

## 2. CAN bus (the robot-actuator standard)

- Two wires: CAN_H, CAN_L (+ GND, usually + power in the same cable).
- Multi-drop: all actuators on the same two wires, each with an ID.
  Built-in arbitration, CRC, automatic retransmission, error confinement.
- Classic CAN: up to **1 Mbit/s**, 8 data bytes per frame.
  **CAN-FD**: up to 5-8 Mbit/s data phase, 64 bytes per frame.
- **ESP32-S3 has a CAN controller called TWAI - classic CAN 2.0 only (no FD).**
  1 Mbit/s with 8-byte frames is enough for MIT-mode commands to ~8-12
  actuators at 1 kHz. If you need CAN-FD later, an external SPI controller
  (MCP2518FD) can be added.

### Hardware needed

```
 ESP32-S3 TWAI_TX/RX ──► [CAN transceiver] ──► CAN_H / CAN_L ──► connector(s)
                              │                    │
                         3.3 V / 5 V         [120 Ω termination, switchable]
                                              [ESD diode array]
                                              [optional common-mode choke]
```

- **Transceiver**: converts logic to the differential bus. Examples:
  TJA1051T/3 or TJA1057 (5 V supply, 3.3 V logic via VIO pin), TCAN1042/
  TCAN1044 (FD-capable, also fine for classic), SN65HVD230 (3.3 V only).
  SOIC-8 is the classic package - see DM board box 9, 3GIMD box 2, GIM box 3.
- **Termination**: the bus needs **exactly two 120 Ω resistors, at the two
  physical ends**. An actuator does not know if it's at the end, so good
  boards make termination **selectable**: solder jumper (3GIMD box 3:
  "120Ω CAN" / "485" jumpers), DIP switch (DM board box 10 - likely ID and/or
  termination), or a software-controlled switch. Better variant: **split
  termination** (2 × 60 Ω with 4.7 nF to GND at the midpoint) for less EMI.
- **ESD protection**: a dual TVS array on CAN_H/CAN_L (PESD2CAN, NUP2105L).
- **Two connectors** wired in parallel for daisy-chaining (DM board box 1).
- Optional common-mode choke for EMC.

### Protocol must-haves (firmware, but plan for them)

- Unique node ID (from DIP switch or stored in flash).
- **Command timeout watchdog**: no command for N ms -> go to a safe state
  (zero torque or hold).
- Status/telemetry frames: position, velocity, torque, temperature, faults.

---

## 3. RS-485

- Also differential (A/B lines), multi-drop, up to 10-20+ Mbit/s on short
  cables. It's just a **UART** with a differential transceiver - no protocol
  built in, you define it.
- Half-duplex: the transceiver has DE (driver enable) / RE (receiver enable)
  pins the MCU toggles. The ESP32-S3 UART has an RS-485 half-duplex mode that
  drives the RTS pin as DE automatically.
- Transceivers: MAX3485/SP3485, THVD1450, SIT3088. The 8-pin parts labelled
  "DO RE DE DI" on the STMBL schematic are these.
- Also needs 120 Ω termination at both ends.
- The GIM board shares one connector between CAN and RS-485 ("H/A", "L/B" on J1,
  box 9) - one footprint/firmware build chooses which.

**Recommendation for you: CAN as the main robot bus** (it's what SteadyWin,
DaMiao, CubeMars, MIT-style actuators speak), with RS-485 as an optional
footprint if board space allows.

---

## 4. UART / debug serial

- A plain 3.3 V UART on a small header or test pads (GIM board J2: VBUS, TX,
  RX, GND, box 8). Useful for logging, a backup flashing path, and connecting
  a USB-UART adapter if USB is broken.
- On the ESP32-S3, **UART0 is GPIO43 (TX) / GPIO44 (RX)** - the ROM bootloader
  also listens there. Bring them to pads.

---

## 5. USB-C on the ESP32-S3 (flashing + serial over the same port)

The ESP32-S3 has a built-in **USB Serial/JTAG controller** on **GPIO19 (D-)
and GPIO20 (D+)**. Plug a USB-C cable into the PC and the chip shows up as a
serial port (CDC-ACM) **and** a JTAG debugger - **no USB-UART bridge chip
needed**. esptool/idf.py/Arduino/PlatformIO can flash it and reset it into the
bootloader automatically over this interface.

### USB-C connector schematic (USB 2.0 only, device)

```
 USB-C receptacle (16-pin USB2.0 type)
   VBUS (A4,B4,A9,B9) ──[ESD/TVS]──[Schottky or ideal diode]──► 5 V logic input (OR-ed)
   CC1 (A5) ──[5.1 kΩ]── GND      ┐ each CC pin gets its OWN 5.1 kΩ pull-down.
   CC2 (B5) ──[5.1 kΩ]── GND      ┘ Without them, C-to-C cables give 0 V on VBUS!
   D+  (A6 and B6 tied) ──┬──[ESD array, e.g. USBLC6-2SC6]── GPIO20
   D-  (A7 and B7 tied) ──┘                               ── GPIO19
   GND (A1,B1,A12,B12) ── GND
   SHIELD ── GND (direct, or via 1 MΩ || 4.7 nF for EMC)
```

Rules:

- **Tie A6/B6 together and A7/B7 together** (the connector is reversible).
- **Two separate 5.1 kΩ resistors** on CC1 and CC2. (A single shared resistor
  is a classic bug that makes the board not power up from C-to-C cables.)
- Route D+/D- as a **90 Ω differential pair**, short, matched length, over
  solid ground, no stubs; the ESD array right at the connector.
- Optionally 22 Ω series resistors close to the ESP32 (the S3 datasheet
  reference designs have options for this).
- VBUS: ESD/TVS (e.g. 5 V TVS or the USBLC6's VBUS pin) and **OR-ing** with the
  board's own 5 V so: USB alone powers the logic (flash without 24 V), the
  24 V supply powers it without USB, and **neither back-feeds the other**
  (never push 5 V into a PC's USB port).
- Place the connector at the **board edge** where the housing allows a cable
  in. On a round actuator board, think about this early!

### Always keep a manual way into the bootloader

Auto-reset via USB Serial/JTAG works only while running firmware doesn't break
the USB peripheral (e.g. if your code reassigns GPIO19/20, crashes very early,
or puts the chip in deep sleep). So add:

- **BOOT button (or 2 pads) on GPIO0** to GND, with a 10 kΩ pull-up.
- **RESET button (or pads) on EN (CHIP_PU)** with 10 kΩ pull-up + 1 µF to GND
  (power-on delay, per the ESP32-S3 hardware design guidelines).

Recovery: hold BOOT, tap RESET, release BOOT -> the ROM bootloader runs, and
the USB serial port appears even with broken firmware.

### Ground-loop warning (important for motor controllers)

USB connects your **PC's ground** to the board's ground. With the motor
running, large currents and fast voltage swings exist in the board ground. If
the 24 V supply and the PC also share a ground elsewhere (e.g. through mains
earth or a scope), current can flow through the USB cable's ground -> USB
disconnects, noisy readings, and in a fault, a fried USB port.

- During development, use a cheap **USB isolator dongle** (ADuM3160/ADuM4160
  based, full-speed 12 Mbit/s - fine for the S3's USB Serial/JTAG).
- On the PCB, keep the USB connector and its ground connection near the
  logic section, far from the power stage.

---

## 6. Wi-Fi / Bluetooth on the ESP32-S3

Available, handy for configuration and telemetry, but:

- Inside an aluminium actuator housing the antenna barely works.
- Radio activity causes 3.3 V current spikes (~350-500 mA) and can disturb
  ADC readings and real-time timing -> keep it **off during precise control**,
  or use it only on a test bench.
- If you use a module (ESP32-S3-WROOM-1), respect the antenna **keep-out
  area** (no copper under/near the antenna) or pick the "-1U" variant with
  an external antenna connector.

Next: [09 Temperature and cooling](09_Temperature_and_Cooling.md)
