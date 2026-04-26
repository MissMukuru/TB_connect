from __future__ import annotations

from app.schemas.risk import ContributingFactor, RiskScoreRequest, RiskScoreResponse


class RiskService:
    SCORE_WEIGHTS: dict[str, int] = {
        "HIV": 22,
        "cd4_below_200": 18,
        "household_contact": 15,
        "haematological_malignancy": 15,
        "organ_transplant": 15,
        "pregnancy": 12,
        "SLE": 10,
        "TNF_inhibitor_use": 10,
        "CKD": 8,
        "diabetes": 7,
    }

    def score(self, payload: RiskScoreRequest) -> RiskScoreResponse:
        conds = set([c.strip() for c in payload.conditions if c and c.strip()])
        symptoms = [s.strip() for s in payload.symptoms if s and s.strip()]

        factors: list[ContributingFactor] = []
        score = 0

        for c in sorted(conds):
            pts = self.SCORE_WEIGHTS.get(c, 0)
            if pts:
                score += pts
                factors.append(ContributingFactor(factor=c, points=pts))

        if "HIV" in conds and payload.cd4 is not None and payload.cd4 < 200:
            pts = self.SCORE_WEIGHTS["cd4_below_200"]
            score += pts
            factors.append(ContributingFactor(factor="cd4_below_200", points=pts))

        if payload.household_contact:
            pts = self.SCORE_WEIGHTS["household_contact"]
            score += pts
            factors.append(ContributingFactor(factor="household_contact", points=pts))

        symptom_points = min(len(symptoms) * 3, 15)
        if symptom_points:
            score += symptom_points
            factors.append(ContributingFactor(factor="symptoms", points=symptom_points))

        if score >= 61:
            level = "critical"
        elif score >= 41:
            level = "high"
        elif score >= 21:
            level = "medium"
        else:
            level = "low"

        score_capped = min(score, 100)
        normalized = round(score_capped / 100.0, 4)

        return RiskScoreResponse(
            score=score_capped,
            score_normalized=normalized,
            risk_level=level,
            contributing_factors=factors,
        )

