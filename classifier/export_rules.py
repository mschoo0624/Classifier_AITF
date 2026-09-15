"""화면용 데이터 생성. web/rules.json 생성


"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from assess import assess
from models import (
    Branch,
    DocType,
    Document,
    Exemption,
    ExemptionType,
    Person,
    PostponeReason,
    Postponement,
    RejectReason,
    REJECT_GUIDE,
    TrainingOutcome,
    VerifyReason,
    accept,
)
from rules import (
    BASIC_HOURS,
    EXEMPTION_RULES,
    MAKEUP_CUTOFF_MONTH,
    MOBILIZATION_HOURS,
    NON_DESIGNATED_ARMY_HOURS,
    NON_DESIGNATED_NAVY_HOURS,
    OPS_HOURS,
    OVERSEAS_EXEMPTION_DAYS,
    OVERSEAS_REGRANT_DAYS,
    POSTPONEMENTS,
    REPEAT_POSTPONE_THRESHOLD,
    SEAFARER_GRACE_MONTHS,
    base_training,
)

YEAR = 2026
AS_OF = date(YEAR, 5, 1)
TRAINING = date(YEAR, 5, 20)
OUT = Path("web")

# 보류 규칙별 필요 서류를 만들어 주기 위한 대응표
DOC_SAMPLE = {
    DocType.EMPLOYMENT: "재직증명서", DocType.ENROLLMENT: "재학증명서",
    DocType.EXIT_ENTRY: "출귀국자명부", DocType.BOARDING: "승선증명서",
}


def rule_rows() -> list[dict]:
    return [{
        "code": r.code,
        "kind": r.kind.value,
        "name": r.name,
        "legal_basis": r.legal_basis,
        "occupations": sorted(r.occupations),
        "docs": [d.value for d in r.required_docs],
        "mobilization": r.mobilization.value,
        "education": r.education.value,
        "education_hours": r.education_hours,
        "recheck_months": r.recheck_months,
        "handler": r.handler,
    } for r in EXEMPTION_RULES]


def postpone_rows() -> list[dict]:
    return [{
        "code": r.code,
        "name": r.name,
        "reason": r.reason.value,
        "docs": [d.value for d in r.docs],
        "apply_before": r.apply_before,
        "retroactive": r.retroactive,
        "duration": r.duration,
    } for r in POSTPONEMENTS]


def year_table() -> list[dict]:
    rows = []
    for ry in range(0, 9):
        for des in (True, False):
            for br in (Branch.ARMY, Branch.NAVY):
                t, h = base_training(ry, des, br)
                rows.append({"resource_year": ry, "designated": des,
                             "branch": br.value, "training": t.value, "hours": h})
    return rows


def _person(ry: int, designated: bool, branch: Branch, rule_code: str | None):
    p = Person(f"22-{76010000 + ry:08d}", "시뮬", YEAR - ry, branch,
               mobilization_designated=designated)
    if rule_code:
        rule = next(r for r in EXEMPTION_RULES if r.code == rule_code)
        p.exemptions = [Exemption(rule_code, AS_OF - timedelta(days=400),
                                  recheck_due=AS_OF + timedelta(days=200))]
        for dt in rule.required_docs:
            d = Document(dt, AS_OF - timedelta(days=20))
            accept(d, "SIM")
            p.documents.append(d)
    return p


def _add_postpone(p: Person) -> None:
    d = Document(DocType.EXAM, TRAINING - timedelta(days=14))
    accept(d, "SIM")
    p.postponements = [Postponement(PostponeReason.EXAM, TRAINING - timedelta(days=9),
                                    [d], approved=True)]


def combos() -> list[dict]:
    """모든 조합을 미리 계산합니다. 화면은 이 표를 조회만 합니다."""
    out = []
    codes = [None] + [r.code for r in EXEMPTION_RULES if r.handler is None]
    for ry in range(0, 9):
        for designated in (True, False):
            for branch in (Branch.ARMY, Branch.NAVY):
                for code in codes:
                    for postponed in (False, True):
                        p = _person(ry, designated, branch, code)
                        if postponed:
                            _add_postpone(p)
                        a = assess(p, AS_OF, TRAINING)
                        out.append({
                            "key": f"{ry}|{int(designated)}|{branch.value}|{code or '-'}|{int(postponed)}",
                            "resource_year": ry,
                            "label": a.label,
                            "exemption_type": a.exemption_type.value if a.exemption_type else None,
                            "rule": a.exemption_rule,
                            "base_training": a.base_training.value,
                            "base_hours": a.base_hours,
                            "mobilization": a.mobilization.value,
                            "training": a.training.value,
                            "hours": a.hours,
                            "makeup": a.makeup_hours,
                            "carryover": a.carryover,
                            "total": a.total_hours,
                            "reasons": a.reasons,
                            "alerts": a.alerts,
                        })
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    data = {
        "year": YEAR,
        "as_of": AS_OF.isoformat(),
        "training_date": TRAINING.isoformat(),
        "constants": {
            "동원훈련": MOBILIZATION_HOURS,
            "동미참_육군": NON_DESIGNATED_ARMY_HOURS,
            "동미참_해공군": NON_DESIGNATED_NAVY_HOURS,
            "기본훈련": BASIC_HOURS,
            "작계훈련": OPS_HOURS,
            "국외보류_기준일수": OVERSEAS_EXEMPTION_DAYS,
            "국외_재출국_소급일수": OVERSEAS_REGRANT_DAYS,
            "외항선원_유예개월": SEAFARER_GRACE_MONTHS,
            "보충훈련_재편성_기준월": MAKEUP_CUTOFF_MONTH,
            "상습연기_기준횟수": REPEAT_POSTPONE_THRESHOLD,
        },
        "exemption_kinds": [k.value for k in ExemptionType],
        "exemption_rules": rule_rows(),
        "postponement_rules": postpone_rows(),
        "year_table": year_table(),
        "outcomes": [{"value": o.value, "carries_over": o.carries_over}
                     for o in TrainingOutcome],
        "reject_reasons": [{"label": r.value, "can_resubmit": REJECT_GUIDE[r][0],
                            "message": REJECT_GUIDE[r][1]} for r in RejectReason],
        "verify_reasons": [r.value for r in VerifyReason],
        "combos": combos(),
    }
    path = OUT / "rules.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"{path}  ({path.stat().st_size/1024:.0f} KB)")
    print(f"  보류규칙 {len(data['exemption_rules'])} / 연기규칙 {len(data['postponement_rules'])}"
          f" / 미리계산 조합 {len(data['combos'])}건")


if __name__ == "__main__":
    main()
