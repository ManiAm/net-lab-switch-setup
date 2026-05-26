
# Switch SerDes and Signaling

High-speed serial signaling in data center switches — SerDes architecture, line coding, signal integrity, and link training.

## Documentation

- **[Background: Switch Architecture](docs/01_README_npu.md):** Brief overview of control/data plane separation and why NPUs exist — context for understanding where SerDes fits in a switch.
- **[SerDes and Lanes](docs/02_README_serdes.md):** How an NPU connects to the outside world — serialization, lane and port architecture, and port breakout.
- **[Digital Signal Fundamentals](docs/03_signal_basics.md):** Encoding schemes, signal integrity, eye diagrams, and impairments like ISI and crosstalk at multi-gigabit rates.
- **[Link Equalization and Training](docs/04_signal_training.md):** Pre-emphasis, CTLE, DFE, and the auto-negotiation and training protocols that make links work at 25G+ per lane.
