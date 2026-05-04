"""
Consensus Engine — standalone multi-agent voting and deliberation.

Agents submit proposals; the engine runs rounds of voting until a position
reaches the endorsement threshold or the round limit is exhausted.
Supports minority-report preservation when consensus is not reached.

Architecture (MOSA):
  Proposal          — a position from one agent
  ConsensusResult   — outcome of a deliberation run
  ConsensusEngine   — orchestrator (threshold-based voting + Delphi iteration)
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("consensus_engine")


def _version() -> str:
    """Return the installed package version, falling back to '1.0.0'."""
    try:
        from importlib.metadata import version
        return version("consensus-engine")
    except Exception:
        return "1.0.0"

# ── Public data types ─────────────────────────────────────────────────────────

@dataclass
class Proposal:
    """A position submitted by an agent."""
    agent: str
    content: str
    score: float = 0.0          # self-assessed quality (0.0–1.0)


@dataclass
class ConsensusResult:
    """Outcome of a deliberation run."""
    consensus_reached: bool
    winning_proposal: Optional[str]
    confidence: float               # endorsement ratio 0.0–1.0
    rounds_taken: int
    minority_report: Optional[Proposal] = None
    all_proposals: List[Proposal] = field(default_factory=list)


# ── Engine ────────────────────────────────────────────────────────────────────

class ConsensusEngine:
    """
    Threshold-based consensus with Delphi-style refinement rounds.

    Args:
        min_threshold: fraction of proposals that must endorse the winner
                       (e.g. 0.70 means ≥70% must agree).
        max_rounds:    maximum refinement iterations before giving up.
    """

    def __init__(self, min_threshold: float = 0.66, max_rounds: int = 3) -> None:
        if not 0.0 < min_threshold <= 1.0:
            raise ValueError("min_threshold must be in (0, 1]")
        self.min_threshold = min_threshold
        self.max_rounds = max_rounds

    def run(self, topic: str, proposals: List[Proposal]) -> ConsensusResult:
        """
        Run deliberation over the given proposals.

        Returns:
            ConsensusResult with winning proposal (or None if no consensus).
        """
        if not proposals:
            return ConsensusResult(
                consensus_reached=False,
                winning_proposal=None,
                confidence=0.0,
                rounds_taken=0,
            )

        groups: Dict[str, List[Proposal]] = {}
        for p in proposals:
            key = self._normalize(p.content)
            groups.setdefault(key, []).append(p)

        best_key: Optional[str] = None
        best_confidence = 0.0
        # Track the groups snapshot that corresponds to best_key so that a
        # subsequent _merge_similar call (which may rename keys) cannot cause
        # a KeyError when we later look up groups[best_key].
        best_groups = groups
        rounds = 0

        for round_num in range(1, self.max_rounds + 1):
            rounds = round_num
            winner_key, confidence = self._vote(groups, len(proposals))
            if confidence >= self.min_threshold:
                best_key = winner_key
                best_confidence = confidence
                best_groups = groups
                break
            best_key, best_confidence, best_groups = winner_key, confidence, groups
            groups = self._merge_similar(groups)

        consensus_reached = best_confidence >= self.min_threshold
        winning_proposal: Optional[str] = None
        minority: Optional[Proposal] = None

        if best_key is not None:
            winning_proposal = best_groups[best_key][0].content
            if not consensus_reached:
                # Use original proposals list so merge-similar grouping doesn't
                # hide the minority (post-merge groups may have collapsed all
                # dissenting proposals into the winning group's key).
                dissenters = [
                    p for p in proposals if self._normalize(p.content) != best_key
                ]
                if dissenters:
                    minority = max(dissenters, key=lambda p: p.score)

        return ConsensusResult(
            consensus_reached=consensus_reached,
            winning_proposal=winning_proposal,
            confidence=best_confidence,
            rounds_taken=rounds,
            minority_report=minority,
            all_proposals=list(proposals),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _normalize(self, text: str) -> str:
        """Reduce text to a stable key for grouping similar proposals."""
        return text.strip().lower()[:120]

    def _vote(
        self, groups: Dict[str, List[Proposal]], total: int
    ) -> Tuple[Optional[str], float]:
        if not groups:
            return None, 0.0
        winner_key = max(groups, key=lambda k: len(groups[k]))
        confidence = len(groups[winner_key]) / total if total else 0.0
        return winner_key, confidence

    def _merge_similar(
        self, groups: Dict[str, List[Proposal]], sim_threshold: float = 0.55
    ) -> Dict[str, List[Proposal]]:
        """Delphi step: merge groups whose representative content is similar.

        Direct mappings are built first (keys[j] → keys[i] for i < j), then
        transitive chains are resolved so that A→B→C collapses to A→C,
        preventing orphaned intermediate groups in the output.
        """
        keys = list(groups.keys())
        merged: Dict[str, str] = {}
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ratio = SequenceMatcher(None, keys[i], keys[j]).ratio()
                if ratio >= sim_threshold and keys[j] not in merged:
                    merged[keys[j]] = keys[i]

        def _follow(k: str) -> str:
            """Follow the merge chain to the canonical root key."""
            while k in merged:
                k = merged[k]
            return k

        new_groups: Dict[str, List[Proposal]] = {}
        for k, proposals in groups.items():
            target = _follow(k)
            new_groups.setdefault(target, []).extend(proposals)
        return new_groups


# ── Persistence (optional SQLite backend) ─────────────────────────────────────

class ConsensusPersistence:
    """
    Optional SQLite persistence for cross-session deliberation history.

    db_path defaults to ``~/.local/share/consensus_engine/deliberations.db``
    (XDG-compliant, no hard-coded system paths).
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS deliberations (
        id TEXT PRIMARY KEY,
        topic TEXT NOT NULL,
        consensus_reached INTEGER DEFAULT 0,
        winning_proposal TEXT,
        confidence REAL DEFAULT 0.0,
        rounds_taken INTEGER DEFAULT 0,
        created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deliberation_id TEXT NOT NULL,
        agent TEXT NOT NULL,
        content TEXT NOT NULL,
        score REAL DEFAULT 0.0,
        FOREIGN KEY (deliberation_id) REFERENCES deliberations(id)
    );
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = os.environ.get(
                "XDG_DATA_HOME",
                os.path.join(os.path.expanduser("~"), ".local", "share"),
            )
            db_dir = os.path.join(data_dir, "consensus_engine")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "deliberations.db")
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=5.0)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(self._SCHEMA)
        return self._conn

    def save(self, topic: str, result: ConsensusResult) -> str:
        deliberation_id = hashlib.sha256(
            f"{topic}:{time.time()}".encode()
        ).hexdigest()[:16]
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO deliberations "
            "(id, topic, consensus_reached, winning_proposal, confidence, "
            "rounds_taken, created_at) VALUES (?,?,?,?,?,?,?)",
            (deliberation_id, topic, int(result.consensus_reached),
             result.winning_proposal, result.confidence,
             result.rounds_taken, time.time()),
        )
        for p in result.all_proposals:
            conn.execute(
                "INSERT INTO proposals (deliberation_id, agent, content, score) "
                "VALUES (?,?,?,?)",
                (deliberation_id, p.agent, p.content[:2000], p.score),
            )
        conn.commit()
        return deliberation_id

    def load(self, deliberation_id: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT topic, consensus_reached, winning_proposal, confidence, "
            "rounds_taken, created_at FROM deliberations WHERE id = ?",
            (deliberation_id,),
        ).fetchone()
        if row is None:
            return None
        proposals = conn.execute(
            "SELECT agent, content, score FROM proposals WHERE deliberation_id = ?",
            (deliberation_id,),
        ).fetchall()
        return {
            "id": deliberation_id,
            "topic": row[0],
            "consensus_reached": bool(row[1]),
            "winning_proposal": row[2],
            "confidence": row[3],
            "rounds_taken": row[4],
            "created_at": row[5],
            "proposals": [{"agent": p[0], "content": p[1], "score": p[2]}
                          for p in proposals],
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    """Command-line entry point for consensus-engine.

    Reads agent proposal files (YAML) and runs a Delphi-style consensus round.

    Each YAML file must contain at minimum:
        agent:   <agent-name>
        content: <proposal text>
        score:   <float 0.0–1.0>   # optional, default 0.5
    """
    import argparse
    import sys

    import yaml  # already in project dependencies

    parser = argparse.ArgumentParser(
        prog="consensus",
        description="Delphi-style multi-agent consensus engine.",
    )
    parser.add_argument(
        "--version", action="version", version=f"consensus-engine {_version()}"
    )
    parser.add_argument("--topic", help="Deliberation topic")
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.environ.get("CONSENSUS_MIN_THRESHOLD", "0.66")),
        metavar="FLOAT",
        help="Minimum endorsement threshold 0–1 (default: 0.66)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=int(os.environ.get("CONSENSUS_MAX_ROUNDS", "3")),
        metavar="N",
        help="Maximum deliberation rounds (default: 3)",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        metavar="YAML",
        help="One or more agent YAML proposal files",
    )

    args = parser.parse_args()

    if not args.topic:
        parser.print_help()
        sys.exit(0)

    if not args.agents:
        parser.error("--agents is required when --topic is specified")

    proposals: List[Proposal] = []
    for path in args.agents:
        try:
            with open(path) as fh:
                data = yaml.safe_load(fh) or {}
        except (OSError, yaml.YAMLError) as exc:
            print(f"[ERR] Cannot read {path}: {exc}", file=sys.stderr)
            sys.exit(1)
        try:
            score = float(data.get("score", 0.5))
        except (ValueError, TypeError):
            score = 0.5
        proposals.append(
            Proposal(
                agent=str(data.get("agent", os.path.basename(path))),
                content=str(data.get("content", "")),
                score=score,
            )
        )

    try:
        engine = ConsensusEngine(min_threshold=args.threshold, max_rounds=args.rounds)
    except ValueError as exc:
        parser.error(str(exc))

    result = engine.run(topic=args.topic, proposals=proposals)

    try:
        from rich.console import Console

        console = Console()
        console.print(f"[bold]Topic    :[/bold] {args.topic}")
        console.print(
            f"[bold]Consensus:[/bold] {'[green]✓ yes[/green]' if result.consensus_reached else '[yellow]✗ no[/yellow]'}"
        )
        if result.winning_proposal:
            console.print(f"[bold]Winner   :[/bold] {result.winning_proposal}")
        console.print(f"[bold]Confidence:[/bold] {result.confidence:.0%}")
        console.print(f"[bold]Rounds   :[/bold] {result.rounds_taken}")
        if result.minority_report:
            mr = result.minority_report
            console.print(f"[bold]Minority :[/bold] {mr.agent} — {mr.content}")
    except ImportError:
        print(f"Topic    : {args.topic}")
        print(f"Consensus: {'yes' if result.consensus_reached else 'no'}")
        if result.winning_proposal:
            print(f"Winner   : {result.winning_proposal}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Rounds   : {result.rounds_taken}")
        if result.minority_report:
            mr = result.minority_report
            print(f"Minority : {mr.agent} — {mr.content}")
