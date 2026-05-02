"""Smoke tests for consensus-engine."""
import pytest


def test_import():
    from consensus_engine import ConsensusEngine, Proposal
    assert ConsensusEngine
    assert Proposal


def test_clear_consensus():
    from consensus_engine import ConsensusEngine, Proposal
    engine = ConsensusEngine(min_threshold=0.60, max_rounds=3)
    proposals = [
        Proposal(agent="a", content="Use X", score=0.90),
        Proposal(agent="b", content="Use X", score=0.85),
        Proposal(agent="c", content="Use X", score=0.80),
    ]
    result = engine.run(topic="test", proposals=proposals)
    assert result.consensus_reached
    assert result.winning_proposal == "Use X"


def test_no_consensus_preserves_minority():
    from consensus_engine import ConsensusEngine, Proposal
    engine = ConsensusEngine(min_threshold=0.95, max_rounds=1)
    proposals = [
        Proposal(agent="a", content="Option A", score=0.70),
        Proposal(agent="b", content="Option B", score=0.65),
    ]
    result = engine.run(topic="test", proposals=proposals)
    assert not result.consensus_reached
    assert result.minority_report is not None
