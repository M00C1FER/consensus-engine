# Reference Projects

Projects studied during the audit cycle to inform design patterns and best
practices for this repo.

## Peer Projects

### 1. [langchain-ai/langchain](https://github.com/langchain-ai/langchain) — MIT, 90k+ ★

**Pattern adopted:** Dataclass-based result types with `field(default_factory=…)`
for mutable defaults. `ConsensusResult.all_proposals` uses this pattern to avoid
the mutable-default-argument pitfall common in Python data containers.

### 2. [microsoft/autogen](https://github.com/microsoft/autogen) — MIT, 30k+ ★

**Pattern adopted:** Agent identity as a plain string field on the message/proposal
object rather than a full object reference. This keeps `Proposal` serialisable
without circular imports and makes YAML round-tripping trivial.

### 3. [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) — MIT, 18k+ ★

**Pattern adopted:** Threshold-gated iteration with an explicit `max_rounds` hard
stop. DSPy's optimizer loops use the same pattern to prevent infinite refinement
loops — we adopted it in `ConsensusEngine.run()`.

### 4. [explosion/spaCy](https://github.com/explosion/spaCy) — MIT, 29k+ ★

**Pattern adopted:** XDG-compliant default storage paths (`~/.local/share/…`)
instead of hard-coded system directories, ensuring the tool works identically on
Debian, Alpine, WSL2, and Termux without privilege escalation.

### 5. [astral-sh/ruff](https://github.com/astral-sh/ruff) — MIT, 32k+ ★

**Pattern adopted:** `pyproject.toml`-first packaging with `[project.scripts]`
entry points and `[tool.setuptools.packages.find]` so the package is installable
via a plain `pip install .` on any platform — no `setup.py` required.
