# 보류·연기 판정 시스템 — 프론트엔드

React + Vite + TypeScript + Tailwind v4. 팀 저장소의 다른 프런트엔드
(예비군/분대/전투편성 시스템)와는 **완전히 별개**입니다 — 이건 우리가
만든 판정 엔진(`assess.py`) 전용 화면입니다.

## 실행

```bash
npm install
python ../export_frontend.py   # public/data.json 갱신 (백엔드 코드는 안 건드림)
npm run dev
```

`http://localhost:5173` 접속.

## 데이터가 오는 곳

지금은 `public/data.json` 정적 파일입니다. `export_frontend.py` 가
`models.py` / `rules.py` / `assess.py` 의 결과를 그대로 떠서 저장할
뿐, **백엔드 코드는 한 줄도 안 건드립니다.**

실제 서버가 준비되면 `src/api.ts` 상단의 `DATA_SOURCE` 를 `'api'` 로
바꾸고 엔드포인트 경로만 맞추면 됩니다. 화면 컴포넌트(`App.tsx`)는
`Bootstrap` 타입만 알고 출처를 모르므로 손댈 필요 없습니다.

승인/반려/확인요청 버튼은 지금 `acceptDocument` / `rejectDocument` /
`verifyDocument` 스텁을 호출합니다 (콘솔 로그만 남기고 로컬 상태만
바뀜). 실제 백엔드가 생기면 이 세 함수 안의 `fetch` 만 채우면 됩니다.

## 화면

**검토함** — 대기 서류 목록(제출 오래된 순, 우선순위 없음) + 원본
서류 + 판정 패널. 승인 시 등록된 종류·발급일을 그대로 쓰고, 반려는
사유 8종 + 안내 문구 자동 발송, 확인요청은 위변조 등 4종.

**명부** — 236명 전체. 검색·분류 필터·"검토 대기만" 체크. 행을
클릭하면 판정 근거·알람·제출 서류 전체를 모달로 봅니다.

## 다음에 필요한 것

- 실제 PDF 서빙 (`file_path` 는 지금 `pdfs/*.pdf` 상대경로 — 실제
  파일은 없습니다)
- 백엔드 연결 (`src/api.ts` 참고)
- 승인 시 프론트가 아니라 서버가 `assess()` 를 다시 돌려 최신
  분류를 반환하도록 (지금은 export 시점에 미리 계산한
  `if_accepted_classification` 을 그대로 신뢰)
