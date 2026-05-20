
# SerDes and Lanes

This section explains how an NPU connects to the outside world at the physical level — the serialization of data for high-speed transmission, the lane and port architecture, and the signaling standards that define per-lane rates.

## Why Serial Links

Inside an NPU, data moves on wide parallel buses — hundreds of bits transferred simultaneously across short on-chip interconnects. This works within the chip because trace lengths are millimeters and skew is negligible. However, the moment data must leave the chip, parallel signaling breaks down. At multi-gigabit rates, ensuring that dozens of parallel wires arrive in precise time alignment over centimeters of board trace becomes impractical. Signal skew, crosstalk between adjacent traces, and connector pin count all become limiting factors.

The solution is **serialization**: converting the wide parallel bus into a small number of narrow, high-speed serial streams. A serial link drastically reduces pin count and routing complexity while enabling very high per-wire data rates.

## Differential Signaling

High-speed serial links use **differential pairs** to carry data. Instead of sending a voltage on a single wire measured against ground (single-ended signaling), a differential pair carries the signal as the voltage difference between two complementary conductors. The transmitter drives one conductor high while simultaneously driving the other low; the receiver measures only the difference between them. The two conductors are denoted TX+ / TX− for the transmit direction and RX+ / RX− for the receive direction.

This matters because at multi-gigabit rates, a ground reference becomes unreliable — power-supply fluctuations, return-path inductance, and nearby switching circuits all corrupt the baseline voltage. A differential pair sidesteps the problem entirely: both conductors travel together through the same PCB traces, connectors, and cables, so any external interference — electromagnetic coupling, power-rail bounce, thermal noise — affects both wires equally and cancels out when the receiver takes the difference.

The result is superior noise immunity (enabling reliable signaling at 25–100+ Gb/s), lower radiated emissions (the equal-and-opposite currents cancel each other's far-field radiation), and no dependence on a clean shared ground between transmitter and receiver.

## SerDes (Serializer / Deserializer)

A **SerDes** is the analog/mixed-signal circuit block on the NPU that performs this parallel-to-serial (and serial-to-parallel) conversion. Every high-speed port on a switch ASIC is driven by one or more SerDes circuits.

- **Transmit (Serializer):** Takes a wide parallel data word from the ASIC's internal fabric, applies block encoding (e.g., 64b/66b with scrambling), serializes it into a single high-speed bitstream, applies line coding (NRZ or PAM4) to map bits to voltage levels, shapes the waveform with a TX FIR filter, and drives it out on one differential pair (TX+ / TX−).

- **Receive (Deserializer):** Accepts the incoming serial bitstream on a differential pair (RX+ / RX−), equalizes and recovers the data, and reconstructs the original parallel word for the ASIC's internal logic.

The diagram below shows the internal stages of a SerDes:

<img src="../pics/serdes_full.png" alt="SerDes block diagram" width="750">

On transmit:

    ASIC → Block Encoding → Serializer → Line Coding → TX FIR → Driver → TX+/TX−

On receive:

    RX+/RX− → CTLE → CDR → Sampler → DFE → Deserializer → Decoder → ASIC

On the transmit side, **block encoding** (e.g., 64b/66b with scrambling) adds framing, DC balance, and control characters to the parallel data. The **serializer** converts the wide parallel word into a single high-speed serial bitstream. **Line coding** maps serial bits to voltage levels — two levels for NRZ, four for PAM4. The **TX FIR** filter pre-shapes the waveform to compensate for predictable channel loss. The **driver** pushes the final signal onto the differential pair.

On the receive side, **CTLE** boosts high frequencies attenuated by the channel, partially restoring the signal so downstream stages can recover the data. **CDR** recovers the clock embedded in the data transitions. The **sampler** captures the signal at the optimal point using that clock. **DFE** cancels residual inter-symbol interference using previous decisions. The **deserializer** converts the recovered serial bitstream back into a wide parallel word. The **decoder** reverses block encoding — descrambling, removing sync headers, and extracting control characters — to recover the original data.

> The diagram omits [FEC encoding](03_signal_basics.md#forward-error-correction-fec), which sits between block encoding and the serializer on transmit, and between the deserializer and decoder on receive. For a detailed discussion of encoding stages and FEC, see [Digital Signal Fundamentals](03_signal_basics.md). For equalization and link training, see [Link Equalization](04_signal_training.md).

## Lanes, Ports, and Port Macros

Each SerDes instance operates independently and constitutes one **lane** — four conductors in total: a TX differential pair (TX+/TX−) carrying data outbound and an RX differential pair (RX+/RX−) carrying data inbound, simultaneously. A 25G lane means 25 Gb/s in each direction; the per-lane rate always refers to one direction.

The total number of lanes an ASIC contains defines its **I/O budget**: the hard upper limit on aggregate bandwidth the chip can deliver to the outside world.

A physical Ethernet **port** is composed of one or more lanes bonded together. The port's total speed is the arithmetic sum of its lane speeds:

    Port speed = Per-lane rate × Number of lanes

For example, a 100G port bonds four 25G lanes (4 × 25G = 100G), while an 800G port bonds eight 100G lanes (8 × 100G = 800G). Lower-speed ports such as 10GbE or 25GbE typically use a single lane.

A **port macro** (also called a port block or port group) is a hardware unit on the ASIC that manages a fixed cluster of SerDes lanes and maps them to one physical front-panel cage. The port macro handles lane-to-port binding, breakout configuration, and the MAC/PCS layer for its lane group.


## SerDes Generations (OIF CEI)

The Optical Internetworking Forum (OIF) defines the Common Electrical Interface (CEI) specifications that standardize SerDes signaling rates across the industry:

| OIF Standard | Per-Lane Rate | Modulation | Example Form Factors Using It       |
| ------------ | ------------- | ---------- | ----------------------------------- |
| CEI-10G      | 10 Gb/s       | NRZ        | SFP+, QSFP+                         |
| CEI-25G      | 25 Gb/s       | NRZ        | SFP28, QSFP28                       |
| CEI-56G      | 50 Gb/s       | PAM4       | SFP56, QSFP56, QSFP-DD (gen 1)      |
| CEI-112G     | 100 Gb/s      | PAM4       | SFP112, QSFP112, OSFP, QSFP-DD 800G |
| CEI-224G     | 200 Gb/s      | PAM4       | SFP224, QSFP224, OSFP-XD            |

Each ASIC generation implements a specific CEI rate across all its lanes. The product of (lane count) × (per-lane rate) determines the chip's total I/O bandwidth. For example, the Broadcom Tomahawk (BCM56960) implements 128 lanes at CEI-25G, yielding 128 × 25G = 3.2 Tbps total switching capacity.


## Port Breakout

Breakout (also called channel splitting or fan-out) is the practice of reconfiguring a single high-speed **physical port** into multiple lower-speed **logical ports** by changing how SerDes lanes within a port macro are grouped. In the default configuration, all lanes in a port macro are bonded into a single interface. In breakout mode, those lanes are split into independent sub-ports, each operating as a separate logical interface with its own MAC address, IP configuration, and forwarding behavior.

**Why breakout exists:** Not every connected device operates at the full speed of the switch port. A switch with 400G physical ports may need to connect servers with 100G NICs. Without breakout, a high-speed port would be underutilized serving a single lower-speed device. With breakout, one physical cage can serve multiple endpoints, maximizing the switch's I/O budget utilization.

<img src="../pics/breakout.png" alt="segment" width="700">

The port macro's lane group is subdivided. A logical port's speed equals the number of lanes assigned to it multiplied by the per-lane rate. For a port macro with N lanes at rate R:

- All N lanes bonded → one port at N × R
- N/2 lanes each → two ports at (N/2) × R
- 1 lane each → N ports at 1 × R

The notation `MxS` describes a breakout configuration: M logical ports each at speed S.

For example, `4x25G` means four logical ports at 25G each.

**Requirements and constraints:**

- Breakout is an ASIC capability. The port macro hardware must support the requested lane grouping; not all ASICs support all possible subdivisions.
- Within a single port macro, all lanes typically must operate at the same base signaling rate. Mixed-rate lanes within one cage are generally not supported.
- Each port macro is independently configurable. One cage can run at full speed while an adjacent cage is broken out, because they are separate hardware blocks.
- Breakout changes require the physical cabling to match. A breakout cable (fan-out cable) splits the high-density connector into multiple lower-density connectors — for example, one QSFP28 to four SFP28, or one OSFP to eight QSFP28.
- The total aggregate bandwidth of the switch does not change under breakout. Lanes are redistributed, not added.
