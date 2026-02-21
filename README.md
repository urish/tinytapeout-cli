# Tiny Tapeout CLI

Design, test, and harden ASIC projects for [Tiny Tapeout](https://tinytapeout.com).

## Installation

```bash
pip install tinytapeout-cli
```

## Quick Start

```bash
# Create a new project
tt init

# Check your environment
tt doctor

# Validate your project
tt check

# Run simulation tests
tt test

# Harden your design
tt gds build

# Run gate-level tests
tt test --gl

# View GDS statistics
tt gds stats
```

## Commands

| Command              | Description                                       |
|----------------------|---------------------------------------------------|
| `tt init`            | Create a new project from a template              |
| `tt doctor`          | Check system readiness (Python, Docker, Git, PDK) |
| `tt check`           | Validate info.yaml and docs/info.md               |
| `tt test`            | Run RTL simulation tests                          |
| `tt test --gl`       | Run gate-level simulation tests                   |
| `tt gds build`       | Harden the project (generate GDS)                 |
| `tt gds stats`       | Print design statistics                           |
| `tt gds validate`    | Run DRC precheck                                  |
| `tt gds view`        | View the hardened GDS layout (default: 2D PNG)    |
| `tt gds view 2d`     | Render and open a 2D PNG of the layout            |
| `tt gds view 3d`     | Open the 3D GDS viewer in your browser            |
| `tt gds view klayout`| Open the layout in KLayout                        |

## Development

Requires [Hatch](https://hatch.pypa.io/):

```bash
pip install hatch
hatch test              # run tests
hatch run tt -- doctor  # run the CLI
```

## License

Apache 2.0
