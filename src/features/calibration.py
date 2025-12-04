"""Confidence calibration for RAG answers.

Adds evidence coverage, source agreement, and hallucination risk metrics
so traders can trust the AI-generated synthesis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class CalibrationMetrics:
    """Calibration metrics for a RAG response."""

    evidence_coverage: float
    source_agreement_score: float
    hallucination_risk: str
    confidence_level: str


class AnswerCalibrator:
    """Estimates confidence/calibration for RAG-generated answers."""

    def calibrate(
        self,
        answer: str,
        source_docs: List[str],
        source_sentiments: Optional[List[float]] = None,
    ) -> CalibrationMetrics:
        evidence_coverage = self._compute_evidence_coverage(answer, source_docs)
        source_agreement = self._compute_source_agreement(source_sentiments)
        hallucination_risk = self._estimate_hallucination_risk(evidence_coverage)
        confidence_level = self._overall_confidence(evidence_coverage, source_agreement)

        return CalibrationMetrics(
            evidence_coverage=round(evidence_coverage, 2),
            source_agreement_score=round(source_agreement, 2),
            hallucination_risk=hallucination_risk,
            confidence_level=confidence_level,
        )

    def _compute_evidence_coverage(self, answer: str, sources: List[str]) -> float:
        if not answer or not sources:
            return 0.0

        answer_tokens = set(self._tokenize(answer))
        if not answer_tokens:
            return 0.0

        source_tokens = set()
        for src in sources:
            source_tokens.update(self._tokenize(src))

        overlap = answer_tokens & source_tokens
        coverage = len(overlap) / len(answer_tokens)
        return min(1.0, coverage)

    def _compute_source_agreement(self, sentiments: Optional[List[float]]) -> float:
        if not sentiments or len(sentiments) < 2:
            return 1.0

        avg = sum(sentiments) / len(sentiments)
        variance = sum((s - avg) ** 2 for s in sentiments) / len(sentiments)
        std = variance**0.5
        agreement = max(0.0, 1.0 - std)
        return agreement

    def _estimate_hallucination_risk(self, coverage: float) -> str:
        if coverage >= 0.7:
            return "low"
        if coverage >= 0.4:
            return "medium"
        return "high"

    def _overall_confidence(self, coverage: float, agreement: float) -> str:
        score = (coverage * 0.6) + (agreement * 0.4)
        if score >= 0.75:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b\w{3,}\b", text)]


_calibrator: Optional[AnswerCalibrator] = None


def get_calibrator() -> AnswerCalibrator:
    global _calibrator
    if _calibrator is None:
        _calibrator = AnswerCalibrator()
    return _calibrator
