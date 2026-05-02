# Consensus Engine

> Delphi-style iterative consensus for multi-agent AI deliberation — converge on high-confidence answers through structured voting rounds.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20WSL%20%7C%20Termux-lightgrey)](install.sh)

## What It Does

AI agents frequently disagree. The Consensus Engine runs a structured Delphi process: agents submit scored proposals, outliers are identified and challenged, then agents refine their positions in subsequent rounds until the group converges or the round cap is reached. A minority report is preserved when full consensus is not possible.

**Key capabilities:**
- Multi-round Delphi voting with configurable thresholds
- Outlier detection with challenge generation
- Weighted confidence scoring per participant
- Minority report preservation (never silently discard dissent)
- Plugin API for custom voting strategies

## Quick Start

```bash
bash install.sh
consensus --help
consensus --topic "Should we use PostgreSQL or SQLite?" \
          --agents agent1.yaml agent2.yaml agent3.yaml
```

## Installation

| Platform | Method |
|----------|--------|
| Linux / WSL | `bash install.sh` |
| Termux (Android) | `bash install.sh` (no sudo) |
| Alpine Linux | `bash install.sh` (requires `sudo apk`) |
| pip | `pip install .` |

```bash
git clone https://github.com/M00C1FER/consensus-engine
cd consensus-engine
bash install.sh
```

## Usage

```python
from consensus_engine import ConsensusEngine, Proposal

engine = ConsensusEngine(min_threshold=0.75, max_rounds=5)

proposals = [
    Proposal(agent="agent-a", content="Use PostgreSQL", score=0.85),
    Proposal(agent="agent-b", content="Use SQLite", score=0.60),
    Proposal(agent="agent-c", content="Use PostgreSQL", score=0.90),
]

result = engine.run(topic="Database selection", proposals=proposals)

print(result.consensus_reached)    # True
print(result.winning_proposal)     # "Use PostgreSQL"
print(result.confidence)           # 1.0  (all proposals merged to winner by round 2)
print(result.minority_report)      # None (no dissenters remain after Delphi merge)
print(result.rounds_taken)         # 2
```

## Architecture (MOSA)

```
consensus-engine/
├── src/consensus_engine/
│   ├── consensus.py       # Delphi voting engine
│   └── __init__.py
├── install.sh             # Cross-platform wizard
├── examples/demo.py       # Three-agent debate demo
└── TOOLS.md
```

## Voting Strategies

| Strategy | Description |
|----------|-------------|
| `delphi` (default) | Iterative rounds; outliers receive written challenges |
| `simple_majority` | First-round plurality wins |
| `weighted` | Scores weighted by agent confidence history |
| `unanimous` | All agents must converge; minority auto-escalates |

## Cross-Platform Notes

Works on Linux (Debian/Ubuntu/Arch/Fedora/Alpine), WSL2, and Termux with no
platform-specific dependencies. All data is stored under `~/.local/share/` (XDG
compliant) — no `/sys/firmware/efi` or system-path assumptions.

| Platform | Status | Notes |
|----------|--------|-------|
| Debian 12/13, Ubuntu 22.04/24.04 | ✅ Tier 1 | `apt-get` path |
| Arch / Manjaro | ✅ Tier 2 | `pacman` path |
| Fedora / RHEL / Rocky | ✅ Tier 2 | `dnf` path |
| Alpine | ✅ Best-effort | `apk add python3 py3-pip git` |
| WSL2 (Ubuntu base) | ✅ Tier 1 | no EFI path assumptions |
| Termux (Android arm64) | ✅ Best-effort | no sudo; `pkg install python git` |

## License

[MIT](LICENSE)
