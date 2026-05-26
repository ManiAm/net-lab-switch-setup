
# Switch Hardware and Setup

This project documents a hands-on exploration of data center switch internals — from ASIC architecture and high-speed signaling down to transceiver management registers — using the Celestica Seastone DX010 as a concrete reference platform running SONiC.

## Documentation and Learning Path

The technologies inside a modern data center switch span multiple engineering disciplines: digital logic, high-speed analog signaling, optics, firmware, and systems software. The following guides build knowledge progressively, starting with how a switch processes packets and ending with physical setup and operation.

- **[Switch Architecture](docs/01_README_npu.md):** How network switches are designed internally — control plane vs. data plane separation, packet forwarding pipelines, and why specialized NPUs are used alongside general-purpose CPUs.
- **[SerDes and Lanes](docs/02_README_serdes.md):** How an NPU connects to the outside world at the physical level — serialization, lane and port architecture, and port breakout.
- **[Digital Signal Fundamentals](docs/03_signal_basics.md):** The analog reality beneath digital signaling — encoding schemes, signal integrity, eye diagrams, and how impairments like ISI and crosstalk degrade high-speed links.
- **[Link Equalization and Training](docs/04_signal_training.md):** How transmitters and receivers negotiate signal conditioning — pre-emphasis, CTLE, DFE, and the auto-negotiation and training protocols that make links work at 25G+ per lane.
- **[The Pluggable Transceiver Model](docs/05_README_module.md):** The three-layer pluggable architecture (port, module, cable), form factor families (SFP through OSFP), the QSFP28 electrical interface, fiber optics, and cabling options (DAC, AOC, structured fiber).
- **[Transceiver Management Interface](docs/06_README_module_mgmt.md):** How the host identifies, monitors, and controls transceivers over I²C — the evolution from static EEPROMs (MSA/INF-8074) through DDM (SFF-8472), multi-lane paging (SFF-8636), to firmware-managed modules (CMIS).
- **[Celestica Seastone DX010](docs/07_README_dx010.md):** Deep dive into the DX010 hardware — Broadcom Tomahawk ASIC, PCB architecture, port layout, SerDes configuration, Intel Atom management CPU, power subsystem, and SONiC compatibility.
- **[DX010 Cooling](docs/08_README_dx010_cooling.md):** Thermal design of the 1U chassis — airflow architecture, fan modules, thermal sensors, and CPLD-driven fan speed control.
- **[DX010: Physical Setup and Initial Access](docs/09_README_dx010_setup.md):** Step-by-step guide to racking, cabling, serial console access, SONiC boot verification, image upgrade, transceiver installation, and port breakout configuration.
