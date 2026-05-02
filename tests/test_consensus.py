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


# ── Bug-fix regression tests ──────────────────────────────────────────────────

def test_no_keyerror_when_winner_key_merged_away():
    """Regression: groups[best_key] raised KeyError when the winner key was
    later in insertion order and got merged into an earlier key.

    Before the fix, run() stored best_key from the pre-merge groups but then
    accessed the post-merge groups dict, causing KeyError on the final lookup.
    """
    from consensus_engine import ConsensusEngine, Proposal

    # 'abc' is inserted first, 'abcd' second.  _merge_similar merges keys[j]
    # into keys[i], so 'abcd' (j=1) merges into 'abc' (i=0).  With only 1
    # round and threshold 0.99, no consensus is reached, but best_key='abcd'
    # points at a key that no longer exists in the post-merge groups dict.
    engine = ConsensusEngine(min_threshold=0.99, max_rounds=1)
    proposals = [
        Proposal(agent="x1", content="abc", score=0.50),
        Proposal(agent="x2", content="abcd", score=0.80),
        Proposal(agent="x3", content="abcd", score=0.90),
        Proposal(agent="x4", content="abcd", score=0.70),
    ]
    # Should not raise KeyError
    result = engine.run(topic="keyerror test", proposals=proposals)
    assert result.winning_proposal == "abcd"
    assert not result.consensus_reached


def test_merge_similar_transitive_closure():
    """Regression: _merge_similar did not follow transitive chains, leaving
    intermediate keys as orphaned groups in the output.

    Example: A is inserted first (i=0), B second (i=1), C third (i=2).
    A~B and B~C but A≁C.  Without transitive closure, C maps to B, which
    creates a new group 'B' even though B itself was merged into A.  With the
    fix, C follows the chain B→A and ends up in A's group.
    """
    from consensus_engine.consensus import ConsensusEngine, Proposal

    engine = ConsensusEngine(min_threshold=0.99, max_rounds=3)

    # 'xyz' (A), 'xya' (B), 'aya' (C) — A~B, B~C, but A≁C
    groups = {
        "xyz": [Proposal("p1", "xyz", 0.5)],
        "xya": [Proposal("p2", "xya", 0.6), Proposal("p3", "xya", 0.8)],
        "aya": [Proposal("p4", "aya", 0.7)],
    }
    new_groups = engine._merge_similar(groups, sim_threshold=0.5)
    # 'xyz' and 'xya' should merge (both ~0.67 ratio); 'aya' should follow the
    # chain to 'xyz' as well (via xya→xyz).  Only 'xyz' should remain.
    assert len(new_groups) == 1, f"Expected 1 group, got {list(new_groups.keys())}"
    root_key = next(iter(new_groups))
    assert len(new_groups[root_key]) == 4, "All 4 proposals should be in the root group"


def test_empty_proposals():
    from consensus_engine import ConsensusEngine
    engine = ConsensusEngine()
    result = engine.run(topic="empty", proposals=[])
    assert not result.consensus_reached
    assert result.winning_proposal is None
    assert result.rounds_taken == 0


def test_single_proposal_always_reaches_consensus():
    from consensus_engine import ConsensusEngine, Proposal
    engine = ConsensusEngine(min_threshold=0.99, max_rounds=1)
    proposals = [Proposal(agent="solo", content="Only option", score=0.9)]
    result = engine.run(topic="solo", proposals=proposals)
    assert result.consensus_reached
    assert result.winning_proposal == "Only option"
    assert result.confidence == pytest.approx(1.0)


def test_invalid_threshold_raises():
    from consensus_engine import ConsensusEngine
    with pytest.raises(ValueError):
        ConsensusEngine(min_threshold=0.0)
    with pytest.raises(ValueError):
        ConsensusEngine(min_threshold=1.1)


def test_main_help(capsys):
    """CLI entry point must be importable and run --help without error."""
    import sys
    from consensus_engine.consensus import main

    with pytest.raises(SystemExit) as exc_info:
        sys.argv = ["consensus", "--help"]
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--topic" in captured.out
    assert "--threshold" in captured.out

