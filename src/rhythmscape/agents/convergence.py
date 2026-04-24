"""Three-agent convergence detection — skeleton.

Day 3 provides a minimal Jaccard-based similarity computation over the
lemmatized bags-of-tokens of each agent's output. Day 4 extends with
question-topic KL divergence and a convergence heuristic.

Intended use: after ``call_agents_for_flag`` returns 2-3 responses for
one ``critique_flag`` row, call ``compute_pairwise_jaccard`` to quantify
how similar the theorists' framings are. High similarity across
theorists with different text lineages suggests the pattern is strong
enough to cut through school-specific vocabulary (a *convergent
reading*). Low similarity suggests the pattern is heavy-lifted by one
school and the other school's independent reading is worth attending to.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Minimal Korean/English tokenization. Day 4 will plug in a proper
# morphological analyzer (khaiii / MeCab / konlpy).
_TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z]{2,}")


def tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_PATTERN.findall(text)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class PairwiseSimilarity:
    theorist_a: str
    theorist_b: str
    jaccard: float
    shared_tokens: int
    a_only_tokens: int
    b_only_tokens: int


def compute_pairwise_jaccard(responses: list) -> list[PairwiseSimilarity]:
    """For a list of ``AgentResponse`` objects, compute pairwise Jaccard."""
    tokenized = [(r.theorist, tokenize(r.text)) for r in responses]
    pairs: list[PairwiseSimilarity] = []
    for i in range(len(tokenized)):
        for j in range(i + 1, len(tokenized)):
            ta, sa = tokenized[i]
            tb, sb = tokenized[j]
            pairs.append(
                PairwiseSimilarity(
                    theorist_a=ta,
                    theorist_b=tb,
                    jaccard=round(jaccard(sa, sb), 4),
                    shared_tokens=len(sa & sb),
                    a_only_tokens=len(sa - sb),
                    b_only_tokens=len(sb - sa),
                )
            )
    return pairs


# Day 4 TODO:
# - question-topic extraction (regex or classifier on '?'-terminated lines)
# - KL divergence between question-topic distributions
# - heuristic threshold J(a,b) ≥ T → "convergent reading" flag, recorded
#   alongside the agent outputs in the HTML report
