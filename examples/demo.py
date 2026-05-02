"""Demo: three agents vote on a technical decision."""
from consensus_engine import ConsensusEngine, Proposal

engine = ConsensusEngine(min_threshold=0.70, max_rounds=3)

proposals = [
    Proposal(agent="architect", content="Use event-driven microservices", score=0.88),
    Proposal(agent="engineer",  content="Use event-driven microservices", score=0.82),
    Proposal(agent="sre",       content="Use a monolith for now",         score=0.55),
]

result = engine.run(topic="Service architecture for MVP", proposals=proposals)

print(f"Consensus reached : {result.consensus_reached}")
print(f"Winning proposal  : {result.winning_proposal}")
print(f"Confidence        : {result.confidence:.0%}")
print(f"Rounds taken      : {result.rounds_taken}")
if result.minority_report:
    print(f"Minority report   : {result.minority_report.agent} — {result.minority_report.content}")
