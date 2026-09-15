"""실행.

    python run.py                      # 검증 + 통계
    python run.py --explain 22-76010001
    python run.py --csv
"""
from __future__ import annotations

import csv
import sys
from collections import Counter

from assess import assess, assess_all
from dataset import AS_OF, EDGE, TRAINING, build_all
from models import DocStatus, ExemptionType, TrainingType


def verify() -> int:
    print(f"엣지케이스  (기준일 {AS_OF} / 훈련일 {TRAINING})")
    print("-" * 92)
    print(f"{'':5s} {'군번':13s} {'성명':14s} {'연차':4s} {'분류':10s} {'훈련':16s} "
          f"{'부과':>5s} {'보충':>5s} {'이월':>5s}")
    print("-" * 92)
    failed = 0
    for code, person, want_label, want_training, want_hours in EDGE:
        a = assess(person, AS_OF, TRAINING)
        ok = (a.label == want_label and a.training == want_training
              and abs(a.hours - want_hours) < 0.01)
        if not ok:
            failed += 1
        print(f"{'OK ' if ok else 'FAIL'} {code:4s} {person.person_id:13s} {person.name:14s} "
              f"{a.resource_year:2d}년차 {a.label:10s} {a.training.value:16s} "
              f"{a.hours:5.0f} {a.makeup_hours:5.0f} {a.carryover:5.0f}")
        if not ok:
            print(f"       기대: {want_label} / {want_training.value} / {want_hours:g}h")
            for r in a.reasons:
                print(f"         · {r}")
        for x in a.alerts:
            print(f"       ! {x}")
    print("-" * 92)
    print(f"{len(EDGE) - failed}/{len(EDGE)} 통과")
    return failed


def stats(people) -> None:
    res = assess_all(people, AS_OF, TRAINING)
    print(f"\n분류 (n={len(people)})")
    print("-" * 60)
    for label, n in Counter(a.label for a in res).most_common():
        print(f"  {label:10s} {n:4d}  {'#' * round(n / len(res) * 45)}")

    print("\n보류 종류")
    for k in ExemptionType:
        n = sum(1 for a in res if a.exemption_type == k)
        if n:
            print(f"  {k.value:10s} {n:4d}")

    print("\n연차별 부과 훈련")
    print(f"  {'연차':4s} {'인원':>4s} {'훈련유형별':<44s} {'총시간':>7s}")
    for ry in range(0, 9):
        grp = [a for a in res if a.resource_year == ry]
        if not grp:
            continue
        types = Counter(a.training.value for a in grp)
        tot = sum(a.hours for a in grp)
        desc = ", ".join(f"{t} {c}" for t, c in types.most_common())
        print(f"  {ry:2d}년차 {len(grp):4d}  {desc:<44s} {tot:7.0f}h")

    print("\n동원훈련 처리")
    for m, n in Counter(a.mobilization.value for a in res).most_common():
        print(f"  {m:18s} {n:4d}")

    print(f"\n총 부과 {sum(a.hours for a in res):,.0f}h"
          f"   보충 {sum(a.makeup_hours for a in res):,.0f}h"
          f"   이월 {sum(a.carryover for a in res):,.0f}h")

    print("\n서류 검토 현황")
    st = Counter()
    for p in people:
        for dc in p.documents:
            st[dc.status] += 1
        for req in p.postponements:
            for dc in req.documents:
                st[dc.status] += 1
    for s, n in st.most_common():
        print(f"  {s.value:10s} {n:4d}")

    alerts = Counter()
    for a in res:
        for x in a.alerts:
            alerts[x.split("—")[0].strip().split("(")[0].strip()] += 1
    if alerts:
        print("\n알람 (실무자 확인 필요)")
        for x, n in alerts.most_common(8):
            print(f"  {n:4d}  {x}")


def explain(people, pid: str) -> None:
    p = next((x for x in people if x.person_id == pid), None)
    if not p:
        print(f"{pid} 없음")
        return
    a = assess(p, AS_OF, TRAINING)
    print(f"\n{p.person_id}  {p.name} ({p.occupation or '직업 미상'}) · {p.branch.value}")
    print(f"  전역 {p.discharge_year}년 → {a.resource_year}년차"
          f" · 동원지정 {'O' if p.mobilization_designated else 'X'}")
    print(f"  기본 부과 : {a.base_training.value} {a.base_hours:g}시간")
    print(f"  최종 판정 : {a.label}"
          + (f" [{a.exemption_rule}]" if a.exemption_rule else ""))
    print(f"  동원훈련  : {a.mobilization.value}")
    print(f"  교육훈련  : {a.training.value} {a.hours:g}시간"
          + (f"  보충 {a.makeup_hours:g}시간" if a.makeup_hours else "")
          + (f"  이월 {a.carryover:g}시간" if a.carryover else ""))
    print(f"  합계      : {a.total_hours:g}시간")
    print("  판정 근거 :")
    for r in a.reasons:
        print(f"    · {r}")
    for x in a.alerts:
        print(f"  ! {x}")
    docs = list(p.documents) + [dc for req in p.postponements for dc in req.documents]
    if docs:
        print("  제출 서류 :")
        for dc in docs:
            extra = ""
            if dc.reject_reason:
                extra = f" ({dc.reject_reason.value})"
            elif dc.verify_reason:
                extra = f" ({dc.verify_reason.value})"
            print(f"    {dc.doc_type.value:14s} 발급 {dc.issued_date}  {dc.status.value}{extra}")
            if dc.medical and not dc.medical.complete:
                print(f"        진단서 누락: {', '.join(dc.medical.missing())}")
    if p.training_records:
        print("  이수 기록 :")
        for rec in sorted(p.training_records, key=lambda x: x.year):
            print(f"    {rec.year}  {rec.training_type.value:16s} "
                  f"부과 {rec.assigned_hours:4.0f}h  이수 {rec.completed_hours:4.0f}h  "
                  f"{rec.outcome.value}"
                  + (f"  미이수 {rec.unfinished:.0f}h" if rec.unfinished else ""))
    if p.exemptions:
        print("  보류 기록 :")
        for e in p.exemptions:
            state = ("유효" if e.is_active_on(AS_OF)
                     else ("기간만료" if e.expired_on(AS_OF) else "해소"))
            why = f", {e.release_reason.value}" if e.release_reason else ""
            print(f"    {e.rule_code:16s} {e.start}~{e.end or '무기한'}  {state}{why}")


def to_csv(people) -> None:
    res = assess_all(people, AS_OF, TRAINING)
    with open("results.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["군번", "성명", "군별", "전역연도", "연차", "동원지정", "분류",
                    "보류규칙", "동원훈련", "교육훈련", "부과시간", "보충시간",
                    "이월시간", "합계", "알람", "사유"])
        for p, a in zip(people, res):
            w.writerow([p.person_id, p.name, p.branch.value, p.discharge_year,
                        a.resource_year, "O" if p.mobilization_designated else "X",
                        a.label, a.exemption_rule or "", a.mobilization.value,
                        a.training.value, f"{a.hours:g}", f"{a.makeup_hours:g}", f"{a.carryover:g}",
                        f"{a.total_hours:g}", " / ".join(a.alerts),
                        a.reasons[-1] if a.reasons else ""])
    print(f"\nresults.csv 생성 ({len(people)}명)")


if __name__ == "__main__":
    args = sys.argv[1:]
    people, _ = build_all(200)
    if args and args[0] == "--explain":
        explain(people, args[1])
    elif args and args[0] == "--csv":
        to_csv(people)
    else:
        f = verify()
        stats(people)
        sys.exit(1 if f else 0)
