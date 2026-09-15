"""데이터셋.

EDGE_CASES 는 기대 결과가 붙어 있어 회귀 테스트 역할을 합니다.
기대값은 (분류라벨, 훈련유형, 시간) 세 가지를 전부 봅니다 — 라벨만
맞고 시간이 틀리면 실무에서 쓸 수 없기 때문입니다.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from models import (
    Branch,
    DocStatus,
    DocType as D,
    Document,
    Exemption,
    MedicalCheck,
    Person,
    PostponeReason as PR,
    Postponement,
    RejectReason as RR,
    ReleaseReason as RL,
    Seafarer,
    TrainingOutcome,
    TrainingRecord,
    TrainingType as T,
    set_diagnosis,
    Trip,
    VerifyReason as VR,
    accept,
    needs_verify,
    reject,
)

AS_OF = date(2026, 5, 1)
TRAINING = date(2026, 5, 20)
YEAR = AS_OF.year
REVIEWER = "OP-31-001"

_seq = {"n": 0}


def sn(yy: int = 22) -> str:
    _seq["n"] += 1
    return f"{yy:02d}-{76010000 + _seq['n']:08d}"


def d(offset: int) -> date:
    return AS_OF + timedelta(days=offset)


def doc(t: D, issued: int, valid: int | None = None, *,
        status: DocStatus = DocStatus.ACCEPTED, reject_reason=None,
        verify_reason=None, verify_number="", diagnosis="", medical=None) -> Document:
    dc = Document(t, d(issued), d(valid) if valid is not None else None,
                  file_name=f"{t.value}.pdf", file_path=f"pdfs/{t.name.lower()}.pdf",
                  verify_number=verify_number, medical=medical)
    if diagnosis:
        set_diagnosis(dc, diagnosis)
    if status == DocStatus.ACCEPTED:
        accept(dc, REVIEWER)
    elif status == DocStatus.REJECTED:
        reject(dc, REVIEWER, reject_reason or RR.ILLEGIBLE)
    elif status == DocStatus.NEEDS_VERIFY:
        needs_verify(dc, REVIEWER, verify_reason or VR.FORGERY)
    return dc


def full_medical() -> MedicalCheck:
    return MedicalCheck(True, True, True, True, True, True, True)


# (코드, Person, 기대라벨, 기대훈련, 기대시간)
EDGE: list[tuple[str, Person, str, T, float]] = []


def case(code, person, label, training, hours) -> Person:
    EDGE.append((code, person, label, training, hours))
    return person


def P(name, discharge_year, *, occ=None, branch=Branch.ARMY,
      designated=False, carryover=0.0, note="", yy=22) -> Person:
    return Person(sn(yy), name, discharge_year, branch, occ,
                  mobilization_designated=designated, carryover_hours=carryover, note=note)


# ======================= 연차별 기본 부과 =======================
case("Y00", P("전역당해", 2026, note="0년차 — 편성만"), "일반", T.NONE, 0)

p = case("Y01", P("1년차동원", 2025, designated=True), "일반", T.MOBILIZATION, 28)
p = case("Y04", P("4년차동원", 2022, designated=True), "일반", T.MOBILIZATION, 28)
p = case("Y03A", P("3년차육군미지정", 2023, branch=Branch.ARMY), "일반", T.NON_DESIGNATED, 32)
p = case("Y03N", P("3년차해군미지정", 2023, branch=Branch.NAVY), "일반", T.NON_DESIGNATED, 28)
p = case("Y05", P("5년차", 2021), "일반", T.BASIC_OPS, 20)
p = case("Y06", P("6년차", 2020), "일반", T.BASIC_OPS, 20)
p = case("Y07", P("7년차이월", 2019, carryover=28, note="신규 없음, 이월만"), "일반", T.CARRYOVER, 0)
p = case("Y08", P("8년차이월없음", 2018), "일반", T.CARRYOVER, 0)

# ======================= 법규보류 =======================
p = case("L01", P("경찰관", 2023, occ="경찰관", designated=True,
                  note="동원 비대상 + 교육 면제"), "법규보류", T.NONE, 0)
p.exemptions = [Exemption("ST-PUBLIC", d(-400), recheck_due=d(200))]
p.documents = [doc(D.EMPLOYMENT, -20, verify_number="1734-5821-9043-2216")]

p = case("L02", P("국회의원", 2021, occ="국회의원"), "법규보류", T.NONE, 0)
p.exemptions = [Exemption("ST-PUBLIC", d(-300), recheck_due=d(100))]
p.documents = [doc(D.EMPLOYMENT, -10)]

p = case("L03", P("소방관서류만료", 2023, occ="소방관", designated=True,
                  note="보류 기록은 유효하나 근거 서류 만료 → 알람"), "법규보류", T.NONE, 0)
p.exemptions = [Exemption("ST-PUBLIC", d(-400), recheck_due=d(100))]
p.documents = [doc(D.EMPLOYMENT, -300, valid=-60)]

p = case("L04", P("교도관재확인", 2023, occ="교도관", designated=True,
                  note="재확인 기한 경과 — 자동 해소하지 않고 알람"), "법규보류", T.NONE, 0)
p.exemptions = [Exemption("ST-PUBLIC", d(-500), recheck_due=d(-30))]
p.documents = [doc(D.EMPLOYMENT, -20)]

# ======================= 방침보류 =======================
p = case("P01", P("우편집배원", 2023, occ="우편집배원", designated=True,
                  note="손실보충부대 + 8시간"), "방침보류", T.BASIC_OPS, 8)
p.exemptions = [Exemption("PL-POSTAL", d(-200), recheck_due=d(150))]
p.documents = [doc(D.EMPLOYMENT, -15)]

p = case("P02", P("대학생", 2024, occ="대학생"), "방침보류", T.BASIC_OPS, 8)
p.exemptions = [Exemption("PL-STUDENT", d(-300), recheck_due=d(60))]
p.documents = [doc(D.ENROLLMENT, -30)]

p = case("P03", P("교사5년차", 2021, occ="교사", note="20시간 대상인데 8시간으로"),
         "방침보류", T.BASIC_OPS, 8)
p.exemptions = [Exemption("PL-TEACHER", d(-200), recheck_due=d(150))]
p.documents = [doc(D.EMPLOYMENT, -10)]

p = case("P04", P("소방간부후보", 2024, occ="소방학교간부후보생",
                  note="방침보류 중 유일한 면제"), "방침보류", T.NONE, 0)
p.exemptions = [Exemption("PL-FIRE-CADET", d(-100), recheck_due=d(250))]
p.documents = [doc(D.ENROLLMENT, -20)]

p = case("P05", P("특수경비원", 2023, occ="특수경비원", designated=True),
         "방침보류", T.BASIC_OPS, 8)
p.exemptions = [Exemption("PL-SECURITY", d(-150), recheck_due=d(200))]
p.documents = [doc(D.EMPLOYMENT, -25)]

p = case("P06", P("직업훈련생", 2024, occ="직업훈련생"), "방침보류", T.BASIC_OPS, 8)
p.exemptions = [Exemption("PL-VOCATIONAL", d(-90), recheck_due=d(90))]
p.documents = [doc(D.ENROLLMENT, -15)]

# ======================= 후순위조정 =======================
p = case("A01", P("동원업무공무원", 2023, occ="전시동원업무공무원", designated=True,
                  note="동원 비대상이지만 동미참훈련 32시간 받음"),
         "후순위조정", T.NON_DESIGNATED, 32)
p.exemptions = [Exemption("PA-WARTIME", d(-300), recheck_due=d(100))]
p.documents = [doc(D.EMPLOYMENT, -20)]

p = case("A02", P("동원업체필수요원", 2022, occ="동원업체필수요원", designated=True,
                  branch=Branch.NAVY, note="해군이라 28시간"),
         "후순위조정", T.NON_DESIGNATED, 28)
p.exemptions = [Exemption("PA-ESSENTIAL", d(-250), recheck_due=d(120))]
p.documents = [doc(D.EMPLOYMENT, -20)]

p = case("A03", P("예비군지휘자", 2021, occ="예비군지휘관",
                  note="5년차라 기본+작계 20시간"), "후순위조정", T.BASIC_OPS, 20)
p.exemptions = [Exemption("PA-LEADER", d(-400), recheck_due=d(100))]
p.documents = [doc(D.EMPLOYMENT, -20)]

# ======================= 보류 해소 =======================
p = case("R01", P("기간만료", 2023, occ="대학생", designated=True,
                  note="보류 기간 끝남 → 일반"), "일반", T.MOBILIZATION, 28)
p.exemptions = [Exemption("PL-STUDENT", d(-500), end=d(-60))]
p.documents = [doc(D.ENROLLMENT, -30)]

p = case("R02", P("졸업해소", 2023, occ="대학생", designated=True,
                  note="기간은 남았으나 졸업으로 해소. 재학증명서는 아직 유효"),
         "일반", T.MOBILIZATION, 28)
p.exemptions = [Exemption("PL-STUDENT", d(-500), end=d(200),
                          released=d(-70), release_reason=RL.GRADUATION)]
p.documents = [doc(D.ENROLLMENT, -30)]

p = case("R03", P("퇴직해소", 2023, occ="경찰관", designated=True), "일반", T.MOBILIZATION, 28)
p.exemptions = [Exemption("ST-PUBLIC", d(-600), released=d(-40), release_reason=RL.RESIGNATION)]
p.documents = [doc(D.EMPLOYMENT, -20)]

p = case("R04", P("해소후재등록", 2023, occ="대학생", designated=True,
                  note="휴학 해소 후 복학으로 재등록"), "방침보류", T.BASIC_OPS, 8)
p.exemptions = [
    Exemption("PL-STUDENT", d(-600), released=d(-200), release_reason=RL.LEAVE),
    Exemption("PL-STUDENT", d(-90), recheck_due=d(90)),
]
p.documents = [doc(D.ENROLLMENT, -20)]

p = case("R05", P("보류시작전", 2023, occ="경찰관", designated=True,
                  note="보류 시작일이 기준일보다 미래"), "일반", T.MOBILIZATION, 28)
p.exemptions = [Exemption("ST-PUBLIC", d(30))]
p.documents = [doc(D.EMPLOYMENT, -20)]

# ======================= 국외 체류 =======================
p = case("O01", P("국외400일", 2023, designated=True,
                  note="1년 이상 → 법규보류"), "법규보류", T.NONE, 0)
p.trips = [Trip(d(-400))]
p.documents = [doc(D.EXIT_ENTRY, -10)]

p = case("O02", P("국외200일", 2023, designated=True,
                  note="1년 미만 → 연기 (전에는 일반으로 틀리게 나왔음)"),
         "연기", T.MOBILIZATION, 0)
p.trips = [Trip(d(-200))]
p.documents = [doc(D.EXIT_ENTRY, -10)]

p = case("O03", P("귀국10일후재출국", 2023, designated=True,
                  note="핵심: 최초 출국일로 소급 → 390일"), "법규보류", T.NONE, 0)
p.trips = [Trip(d(-400), d(-200)), Trip(d(-190))]
p.documents = [doc(D.EXIT_ENTRY, -10)]

p = case("O04", P("귀국30일후재출국", 2023, designated=True,
                  note="14일 초과 → 소급 안 됨, 170일이라 연기"), "연기", T.MOBILIZATION, 0)
p.trips = [Trip(d(-400), d(-200)), Trip(d(-170))]
p.documents = [doc(D.EXIT_ENTRY, -10)]

p = case("O05", P("귀국완료", 2023, designated=True,
                  note="귀국 다음날부터 훈련 부과"), "일반", T.MOBILIZATION, 28)
p.trips = [Trip(d(-500), d(-60))]
p.documents = [doc(D.EXIT_ENTRY, -10)]

p = case("O06", P("귀국5일차", 2023, designated=True,
                  note="아직 14일 안 지남 — 재출국 가능성 알람"), "일반", T.MOBILIZATION, 28)
p.trips = [Trip(d(-500), d(-5))]
p.documents = [doc(D.EXIT_ENTRY, -10)]

p = case("O07", P("명부미제출", 2023, designated=True,
                  note="체류 요건은 되나 근거 서류 없음 — 해외에 있으므로 최소 연기"),
         "연기", T.MOBILIZATION, 0)
p.trips = [Trip(d(-400))]

# ======================= 외항선원 =======================
p = case("S01", P("승선중", 2023, occ="선원", designated=True), "법규보류", T.NONE, 0)
p.seafarer = Seafarer(onboard=True)
p.documents = [doc(D.EMPLOYMENT, -30), doc(D.BOARDING, -30)]

p = case("S02", P("하선2개월", 2023, occ="선원", designated=True,
                  note="3개월 이내 → 연기"), "연기", T.MOBILIZATION, 0)
p.seafarer = Seafarer(onboard=False, disembark_date=d(-60))
p.documents = [doc(D.EMPLOYMENT, -100), doc(D.DISEMBARK, -60)]

p = case("S03", P("하선4개월", 2023, occ="선원", designated=True,
                  note="3개월 경과 → 보류 해소"), "일반", T.MOBILIZATION, 28)
p.seafarer = Seafarer(onboard=False, disembark_date=d(-120))
p.documents = [doc(D.EMPLOYMENT, -200), doc(D.DISEMBARK, -120)]

# ======================= 연기 =======================
p = case("N01", P("질병사후신청", 2023, designated=True), "연기", T.MOBILIZATION, 0)
p.postponements = [Postponement(PR.ILLNESS, TRAINING + timedelta(days=3),
                                [doc(D.MEDICAL, -2, medical=full_medical(), diagnosis="요추 추간판탈출증")],
                                approved=True, approver="중대장")]

p = case("N02", P("질병늦은신청", 2023, designated=True,
                  note="사후 10일 — 허용 5일 초과"), "일반", T.MOBILIZATION, 28)
p.postponements = [Postponement(PR.ILLNESS, TRAINING + timedelta(days=10),
                                [doc(D.MEDICAL, -2, medical=full_medical())], approved=True)]

p = case("N03", P("시험응시", 2023, designated=True), "연기", T.MOBILIZATION, 0)
p.postponements = [Postponement(PR.EXAM, d(10), [doc(D.EXAM, 5)], approved=True)]

p = case("N04", P("결재미승인", 2023, designated=True), "일반", T.MOBILIZATION, 28)
p.postponements = [Postponement(PR.DISASTER, d(5), [doc(D.DISASTER, 0)], approved=False)]

p = case("N05", P("진단서만료", 2023, designated=True), "일반", T.MOBILIZATION, 28)
p.postponements = [Postponement(PR.ILLNESS, d(5),
                                [doc(D.MEDICAL, -90, valid=-60, medical=full_medical())],
                                approved=True)]

p = case("N06", P("진단서항목누락", 2023, designated=True,
                  note="연기는 되지만 도장 누락 알람"), "연기", T.MOBILIZATION, 0)
p.postponements = [Postponement(PR.ILLNESS, d(5),
                                [doc(D.MEDICAL, -2,
                                     medical=MedicalCheck(True, True, True, False, False, True, True))],
                                approved=True)]

p = case("N07", P("상습연기자", 2023, designated=True,
                  note="동일 병명 3회 — 알람"), "연기", T.MOBILIZATION, 0)
p.postponements = [
    Postponement(PR.ILLNESS, d(-400), [doc(D.MEDICAL, -400, diagnosis="요추 추간판탈출증", medical=full_medical())], approved=True),
    Postponement(PR.ILLNESS, d(-200), [doc(D.MEDICAL, -200, diagnosis="요추 추간판탈출증", medical=full_medical())], approved=True),
    Postponement(PR.ILLNESS, d(5), [doc(D.MEDICAL, -2, diagnosis="요추 추간판탈출증", medical=full_medical())], approved=True),
]

p = case("N08", P("서류검토대기", 2023, designated=True), "일반", T.MOBILIZATION, 28)
p.postponements = [Postponement(PR.EXAM, d(8),
                                [doc(D.EXAM, 4, status=DocStatus.PENDING)], approved=True)]

# ======================= 보류 우선 =======================
p = case("X01", P("보류연기동시", 2023, occ="경찰관", designated=True,
                  note="보류가 먼저 적용되어 교육 면제"), "법규보류", T.NONE, 0)
p.exemptions = [Exemption("ST-PUBLIC", d(-300), recheck_due=d(100))]
p.documents = [doc(D.EMPLOYMENT, -10)]
p.postponements = [Postponement(PR.EXAM, d(5), [doc(D.EXAM, 5)], approved=True)]

p = case("X02", P("방침보류연기", 2023, occ="교사", designated=True,
                  note="8시간 부과 상태에서 연기 → 8시간 이월"), "연기", T.BASIC_OPS, 0)
p.exemptions = [Exemption("PL-TEACHER", d(-200), recheck_due=d(150))]
p.documents = [doc(D.EMPLOYMENT, -10)]
p.postponements = [Postponement(PR.EXAM, d(5), [doc(D.EXAM, 5)], approved=True)]

# ======================= 일반 =======================
case("G01", P("일반3년차", 2023, occ="회사원", designated=True), "일반", T.MOBILIZATION, 28)

p = case("G02", P("자료미확인", 2023, occ="회사원", designated=True,
                  note="출입국 자료 미연동 — 판정 불완전 알람"), "일반", T.MOBILIZATION, 28)
p.unverified = {"trips"}


# ======================= 이수 기록 / 이월 =======================
p = case("C01", P("작년미이수", 2022, designated=True,
                  note="작년 28시간 중 12시간만 이수 → 16시간 이월"),
         "일반", T.MOBILIZATION, 28)
p.training_records = [
    TrainingRecord(YEAR - 1, T.MOBILIZATION, 28, 12, TrainingOutcome.PARTIAL)]

p = case("C02", P("보류면제이력", 2022, occ="경찰관", designated=True,
                  note="작년 보류면제는 이월되지 않음"), "법규보류", T.NONE, 0)
p.exemptions = [Exemption("ST-PUBLIC", d(-500), recheck_due=d(200))]
p.documents = [doc(D.EMPLOYMENT, -20)]
p.training_records = [
    TrainingRecord(YEAR - 1, T.NONE, 28, 0, TrainingOutcome.EXEMPTED)]

p = case("C03", P("누적이월", 2019, carryover=0, designated=False,
                  note="7년차 — 3년치 미이수 누적"), "일반", T.CARRYOVER, 0)
p.training_records = [
    TrainingRecord(YEAR - 3, T.MOBILIZATION, 28, 0, TrainingOutcome.ABSENT),
    TrainingRecord(YEAR - 2, T.BASIC_OPS, 20, 8, TrainingOutcome.PARTIAL),
    TrainingRecord(YEAR - 1, T.BASIC_OPS, 20, 20, TrainingOutcome.COMPLETED)]

# ======================= 보충훈련 재편성 =======================
p = case("M01", P("연기보충", 2023, designated=True,
                  note="5월 훈련 연기 → 당해 연도 보충훈련으로 재편성"),
         "연기", T.MOBILIZATION, 0)
p.postponements = [Postponement(PR.EXAM, d(5), [doc(D.EXAM, 4)], approved=True)]

# ======================= 보류 기록 중복 =======================
p = case("V01", P("보류중복", 2023, occ="경찰관", designated=True,
                  note="같은 규칙 보류가 기간 겹침 — 알람"), "법규보류", T.NONE, 0)
p.exemptions = [Exemption("ST-PUBLIC", d(-400), recheck_due=d(100)),
                Exemption("ST-PUBLIC", d(-200), recheck_due=d(200))]
p.documents = [doc(D.EMPLOYMENT, -20)]

# ======================= BULK =======================
_SUR = "김이박최정강조윤장임한오서신권황안송류전홍"
_GIV = ["민준", "서연", "도윤", "지우", "하준", "수빈", "예준", "지호", "시우", "주원"]

_EX_POOL = [
    ("ST-PUBLIC", ["경찰관", "소방관", "교도관", "군무원", "철도종사원"], D.EMPLOYMENT),
    ("PL-POSTAL", ["우편집배원"], D.EMPLOYMENT),
    ("PL-STUDENT", ["대학생"], D.ENROLLMENT),
    ("PL-TEACHER", ["교사", "교수"], D.EMPLOYMENT),
    ("PL-VOCATIONAL", ["직업훈련생"], D.ENROLLMENT),
    ("PL-SECURITY", ["특수경비원"], D.EMPLOYMENT),
    ("PA-WARTIME", ["전시동원업무공무원"], D.EMPLOYMENT),
    ("PA-LEADER", ["예비군지휘관"], D.EMPLOYMENT),
]
_PO_DOC = {PR.ILLNESS: D.MEDICAL, PR.EXAM: D.EXAM, PR.DISASTER: D.DISASTER,
           PR.COMPETITION: D.COMPETITION, PR.WEDDING: D.WEDDING,
           PR.CLASS: D.ATTENDANCE, PR.FARMING: D.FARMING, PR.DUTY: D.BUSINESS}
_REJ = [RR.ILLEGIBLE, RR.WRONG_TYPE, RR.EXPIRED, RR.MISMATCH, RR.INCOMPLETE, RR.NO_SEAL]
_DIAG = ["요추 추간판탈출증", "족관절 염좌", "위염", "기관지염", "슬관절 인대손상"]


def _vnum(rng):
    return "" if rng.random() < 0.25 else "-".join(str(rng.randint(1000, 9999)) for _ in range(4))


def _status(rng):
    r = rng.random()
    if r < 0.70:
        return DocStatus.ACCEPTED, None, None
    if r < 0.87:
        return DocStatus.PENDING, None, None
    if r < 0.96:
        return DocStatus.REJECTED, rng.choice(_REJ), None
    return DocStatus.NEEDS_VERIFY, None, rng.choice([VR.FORGERY, VR.ISSUER_CHECK])


def build_bulk(n: int = 200, seed: int = 31) -> list[Person]:
    rng = random.Random(seed)
    out: list[Person] = []
    for _ in range(n):
        dy = rng.randint(YEAR - 8, YEAR)
        ry = YEAR - dy
        p = Person(sn(rng.randint(18, 26)), rng.choice(_SUR) + rng.choice(_GIV), dy,
                   rng.choices([Branch.ARMY, Branch.NAVY, Branch.AIR_FORCE, Branch.MARINE],
                               [0.78, 0.09, 0.09, 0.04])[0],
                   occupation="회사원",
                   mobilization_designated=(1 <= ry <= 4 and rng.random() < 0.55),
                   carryover_hours=rng.choice([0, 0, 0, 8, 12, 28]) if ry >= 5 else 0)

        if rng.random() < 0.32:
            code, occs, need = rng.choice(_EX_POOL)
            p.occupation = rng.choice(occs)
            st, rj, vf = _status(rng)
            p.documents.append(doc(need, -rng.randint(1, 70), status=st,
                                   reject_reason=rj, verify_reason=vf,
                                   verify_number=_vnum(rng)))
            roll = rng.random()
            if roll < 0.72:      # 유효
                p.exemptions.append(Exemption(code, d(-rng.randint(60, 700)),
                                              recheck_due=d(rng.randint(-60, 300))))
            elif roll < 0.86:    # 기간만료
                p.exemptions.append(Exemption(code, d(-rng.randint(400, 900)),
                                              end=d(-rng.randint(5, 120))))
            else:                # 사유 해소
                p.exemptions.append(Exemption(
                    code, d(-rng.randint(400, 900)), released=d(-rng.randint(5, 150)),
                    release_reason=rng.choice([RL.GRADUATION, RL.RESIGNATION, RL.LEAVE])))

        if rng.random() < 0.05:
            p.documents.append(doc(D.EXIT_ENTRY, -rng.randint(5, 60), verify_number=_vnum(rng)))
            if rng.random() < 0.5:
                p.trips.append(Trip(d(-rng.randint(150, 600))))
            else:
                out_d = -rng.randint(400, 500)
                back = out_d + rng.randint(150, 220)
                p.trips += [Trip(d(out_d), d(back)),
                            Trip(d(back + rng.choice([5, 10, 13, 20, 40])))]

        if rng.random() < 0.03:
            p.occupation = "선원"
            on = rng.random() < 0.5
            p.seafarer = Seafarer(on, None if on else d(-rng.randint(10, 160)))
            p.documents += [doc(D.EMPLOYMENT, -25), doc(D.BOARDING, -25), doc(D.DISEMBARK, -25)]

        if rng.random() < 0.20:
            reason = rng.choice(list(_PO_DOC))
            late = rng.random() < 0.15
            when = (TRAINING + timedelta(days=rng.randint(1, 8))) if late else d(rng.randint(1, 15))
            docs = []
            if rng.random() < 0.85:
                st, rj, vf = _status(rng)
                docs = [doc(_PO_DOC[reason], -rng.randint(0, 20), status=st,
                            reject_reason=rj, verify_reason=vf, verify_number=_vnum(rng),
                            diagnosis=rng.choice(_DIAG) if reason == PR.ILLNESS else "",
                            medical=full_medical() if reason == PR.ILLNESS and rng.random() < 0.8 else
                                    (MedicalCheck(True, True, True, rng.random() < .5, rng.random() < .5, True, True)
                                     if reason == PR.ILLNESS else None))]
            p.postponements.append(Postponement(reason, when, docs, approved=rng.random() < 0.75))

        out.append(p)
    return out


def build_all(bulk: int = 200):
    return [p for _, p, _, _, _ in EDGE] + build_bulk(bulk), EDGE
