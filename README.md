# Tiny Tapeout CLI

Design, test, and harden ASIC projects for [Tiny Tapeout](https://tinytapeout.com).

## Installation

```bash
pip install tinytapeout-cli
```

## Quick Start

```bash
# Check your environment
tt doctor

# Validate your project
tt check

# Harden your design
tt gds build

# View GDS statistics
tt gds stats
```

## Commands

| Command           | Description                                       |
|-------------------|---------------------------------------------------|
| `tt doctor`       | Check system readiness (Python, Docker, Git, PDK) |
| `tt check`        | Validate info.yaml and docs/info.md               |
| `tt gds build`    | Harden the project (generate GDS)                 |
| `tt gds stats`    | Print design statistics                           |
| `tt gds validate` | Run DRC precheck                                  |
| `tt gds view`     | View the hardened GDS layout                      |

## Development

Requires [Hatch](https://hatch.pypa.io/):

```bash
pip install hatch
hatch test              # run tests
hatch run tt -- doctor  # run the CLI
```

## License

Apache 2.0
