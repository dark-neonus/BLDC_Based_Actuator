# 03 - MOSFETs and the half-bridge

Why you care: six MOSFETs carry every amp your motor ever sees. They are the
parts that die first, get hot first, and make most of the electrical noise.
Understanding what they do in the **20-50 nanoseconds** of each switching
edge is the difference between a robust board and one that pops.

---

## 1. The half-bridge (one per motor phase)

```
   +Vbus (24 V) ──────────┬───────────
                          │
                     ┌────┴────┐
       gate HS ─────►│ Q_high  │   (high-side N-MOSFET)
                     └────┬────┘
                          │
                          ├──────────────► to motor phase U   ("switch node")
                          │
                     ┌────┴────┐
       gate LS ─────►│ Q_low   │   (low-side N-MOSFET)
                     └────┬────┘
                          │
                       [shunt]  (optional low-side current sense)
                          │
   GND ───────────────────┴───────────
```

- High ON / low OFF -> phase pulled to +Vbus.
- High OFF / low ON -> phase pulled to GND.
- **Both ON -> dead short across the bus = "shoot-through"**. Hundreds of amps,
  dead MOSFETs. Prevented by **dead time** (section 6).
- Three of these = 3-phase inverter. The PWM duty cycle sets the *average*
  voltage of each phase; the motor's inductance turns that into a smooth-ish
  current.

Why N-channel on the high side too? N-MOSFETs have ~2-3× lower resistance than
P-MOSFETs of the same size and cost. The price: the high-side gate must be
driven ~10 V **above the switch node**, which sits at +24 V when on -> needs a
gate driver with a **bootstrap** supply (module 04).

---

## 2. MOSFET basics: a voltage-controlled switch

Three pins: **Gate, Drain, Source**. Apply voltage Vgs between gate and source:

- Vgs < Vgs(th) (threshold, ~1.5-4 V): OFF.
- Vgs around threshold: partially on - behaves like a resistor that heats up
  massively. **Never stay here.**
- Vgs = 10 V (or 4.5 V for "logic level" parts): fully ON, resistance =
  **Rds(on)**, a few mΩ for good parts.

The gate is insulated: at DC it draws no current. But it is a **capacitor**
(several nF). To switch, you must push charge in and out quickly - that takes
**amps** of peak gate current for a few tens of ns. An MCU pin (~20 mA) cannot
do that -> that is the gate driver's job.

### Datasheet parameters that matter (and what they mean in practice)

| Parameter | Typical for a 60 V actuator FET | Meaning |
|-----------|------------------------------|---------|
| V_DS(max) | 40 / 60 / 80 V | Absolute max drain-source voltage. **Choose ≥ 2× bus** for a 24 V bus -> 60 V parts are the common choice. Spikes + regen eat the margin. |
| R_DS(on) @ Vgs=10 V | 1-5 mΩ | Conduction loss I²R. **Rises ~1.5-1.8× at 100-125 °C** - use the hot value. |
| I_D | "300 A" | Mostly marketing (package/bond-wire limit at a 25 °C case). Thermal design decides real current. |
| Q_g (total gate charge) | 20-100 nC | Charge the driver must move per switch. Gate drive power = Qg × Vgs × f. |
| Q_gd (Miller charge) | 5-20 nC | Charge during the voltage transition. **Mostly sets switching speed and loss.** |
| C_iss, C_oss, C_rss | nF / nF / pF | Input, output, reverse-transfer capacitance. Crss = Cgd (the Miller cap). |
| V_GS(th) | 2-4 V | Threshold. Low threshold = easier to falsely turn on by noise. |
| Q_rr, t_rr | 10s-100s nC | Body diode reverse recovery: a current spike when the opposite FET turns on. |
| R_θJC | 0.5-1.5 °C/W | Junction-to-case thermal resistance. Combined with your PCB/housing path -> temperature. |
| Body diode V_F | ~0.8-1 V | Loss during dead time. |

---

## 3. What happens during a turn-on (the four phases)

This is the "MOSFETs at high frequency" part. Drive the gate through a gate
resistor Rg with a step from 0 to 12 V. Gate voltage vs time is **not** a
simple RC curve:

```
 Vgs
  12V ┤                                 ________________
      │                              __/
      │                           __/          (4) gate keeps charging,
   ~5V┤          ________________/                 Rds_on drops to minimum
      │         /  (3) MILLER PLATEAU:
  Vth ┤      __/       Vds falls from 24 V to ~0 here;
      │   __/ (2)      gate current all goes into Cgd.
      │__/ (1)         Vgs stays flat!
      └─────────────────────────────────────────── time
 Vds 24V ─────────────────\
                           \___________________________
 Id   0  ________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
```

1. **Delay**: gate charges Cgs from 0 to Vth. Nothing happens to the power
   path yet.
2. **Current rise**: Vgs passes threshold, drain current rises to the full
   load current. Vds still ≈ 24 V. **Both V and I are high -> loss.**
3. **Miller plateau**: drain voltage falls. Falling drain voltage means the
   gate-drain capacitance Cgd must be discharged *through the gate*. All the
   driver's current goes into Cgd, so Vgs stays flat. Duration ≈ Qgd / I_gate.
   **V and I both significant -> most of the switching loss is here.**
4. **Enhancement**: gate charges to full drive voltage, Rds(on) reaches its
   minimum.

Turn-off is the same in reverse. Practical consequences:

- **Gate current controls switching speed.** Bigger gate resistor -> longer
  plateau -> slower edges -> more switching loss but less ringing/EMI.
- Switching loss per FET ≈ **½ × Vbus × I × (t_rise + t_fall) × f_PWM**.
  Example: 24 V, 20 A, 40 ns + 40 ns, 20 kHz -> 0.5 × 24 × 20 × 80 ns × 20 kHz ≈
  **0.38 W**.
- Conduction loss ≈ **I_rms² × Rds(on,hot) × (fraction of time on)**. Example:
  20 A, 3 mΩ hot -> 1.2 W per FET at 100 % duty. At low speed/high torque
  (typical for actuators: holding a load) conduction loss dominates.
- Raising PWM frequency multiplies switching loss but lowers current ripple.
  20-40 kHz is the usual compromise for actuators.

> Demo: [interactive/02_mosfet_switching.html](interactive/02_mosfet_switching.html)
> - change Rg, Qgd, load current and stray inductance; watch the plateau, the
> ringing, and the loss numbers.

---

## 4. Danger: dV/dt induced turn-on (the Miller effect, again)

When the **high-side** FET turns on, the switch node jumps 0 -> 24 V in maybe
20 ns (1.2 V/ns!). The **low-side** FET is supposed to be off, but its Cgd
couples that jump into its gate: I = Cgd × dV/dt. If the gate driver's
pull-down path is weak (high resistance, long trace), the low-side gate is
pushed above threshold -> brief shoot-through -> heat, noise, failure.

Defences:

- Strong, low-impedance **turn-off path**: separate (smaller) turn-off resistor,
  often a **diode across the gate resistor** so turn-off bypasses Rg. You can
  see those diodes (D2-D7, six of them = one per FET) on the GIM board
  (box 14).
- Short gate loops (driver close to FETs).
- FETs with low Crss/Ciss ratio and not-too-low Vth.
- Gate drivers with "active Miller clamp" or strong sink current.
- Do not make the edges faster than needed.

---

## 5. Ringing and spikes (loop inductance strikes)

The commutation loop: bulk/MLCC cap -> high-side FET -> low-side FET -> back to
cap. Its stray inductance (Lloop) and the FETs' output capacitance (Coss) form
an LC circuit. Every edge "rings" at f = 1 / (2π √(L·C)), typically
50-300 MHz, with an overshoot ~ I × √(L/C) on top of the bus voltage.

Example: Lloop = 10 nH, Coss = 1 nF, switching 20 A -> overshoot ≈ 20 × √(10n/1n)
≈ 63 V... in theory (damping reduces it a lot in practice), but it shows why:

1. **Minimise the loop**: MLCCs (0805-1210, 100 nF-10 µF) placed **right
   across each half-bridge**, high-side drain to low-side source, on the same
   layer or with the return directly underneath on the next layer. Look how
   the 3GIMD and DM boards place caps around the FETs.
2. Use 60 V FETs on 24 V.
3. Slow the edges a little with Rg if needed.
4. Optional **RC snubber** across each low-side FET (e.g. a few Ω + 1-4.7 nF) to
   damp ringing. Leave footprints, populate if the scope says so.

---

## 6. Dead time and the body diode

The driver turns one FET off and waits **dead time** (typ. 100-500 ns) before
turning the other on, because turn-off is not instant. During dead time the
motor current (an inductor - it does not stop!) has to go somewhere: it flows
through the **body diode** of one FET (the parasitic diode from source to
drain inside every MOSFET).

Consequences:

- Body-diode conduction: loss ≈ Vf × I × 2 × t_dead × f. Keep dead time just
  long enough.
- **Reverse recovery**: when the opposite FET turns on, the conducting body
  diode needs some time and charge (Qrr) to stop conducting -> a current spike
  through both FETs + ringing. Fast/soft body diode FETs help.
- **Dead-time distortion**: the real phase voltage differs from the commanded
  one by a dead-time-dependent amount whose sign depends on current direction
  -> small torque ripple near zero current. FOC firmware can compensate.
- The ESP32-S3's MCPWM peripheral generates complementary PWM with
  programmable dead time in hardware (module 10). Many gate drivers also
  enforce a minimum dead time themselves - a second safety net.

> Demo: [interactive/03_dead_time.html](interactive/03_dead_time.html)

---

## 7. Choosing MOSFETs for a 24 V, ~20-40 A actuator

- V_DS: **60 V** (40 V is possible with a stiff battery and good TVS, but less
  margin for regen).
- Rds(on): 1-3 mΩ @ 10 V.
- Package: **PDFN 5×6 / SuperSO8** (the 3GIMD board, box 8) is the sweet spot
  for small actuators; **TOLL / TO-263** (bigger, DM board box 4) for higher
  current. Both have a big exposed drain pad that dumps heat into the PCB
  copper - which must then reach the housing (module 09).
- Gate charge moderate (Qg < ~80 nC) so the gate driver can keep up.
- Check the **SOA** and **avalanche rating** - avalanche ratings matter for
  surviving spikes.
- Prefer FETs with a "fast/soft body diode" if available; check Qrr.
- Popular examples to read datasheets of (not a recommendation of exact part):
  Infineon BSC014N06NS / BSC016N06NS, Toshiba TPH1R306P1, onsemi NVMFS5C628N,
  Vishay SiR680ADP. Compare their tables with section 2 - that is a great
  exercise.

Paralleling FETs: possible (Rds(on) has a positive tempco, so current
self-balances in conduction), but each needs its own gate resistor and the
layout must be symmetrical. For your size, one FET per position is usually
enough.

Next: [04 Gate drivers](04_Gate_Drivers.md)
