import { useEffect, useState } from 'react'
import {
  decideSubmission, listSubmissions, submissionFileUrl, uploadSubmission,
  type Submission,
} from './classifierApi'

const STATUS_STYLE: Record<Submission['status'], string> = {
  pending: 'bg-slate-100 text-slate-600',
  approved: 'bg-emerald-50 text-emerald-800',
  declined: 'bg-rose-50 text-rose-700',
}
const STATUS_LABEL: Record<Submission['status'], string> = {
  pending: '검토대기', approved: '승인', declined: '반려',
}

export function ExtractionSummary({ extraction, category }: { extraction: Submission['extraction']; category: string | null }) {
  if (extraction.error) {
    return <p className="text-[13px] text-rose-700">추출 실패: {extraction.error}</p>
  }
  return (
    <div className="grid grid-cols-2 gap-2 text-[13px] md:grid-cols-4">
      <div><div className="text-[11px] text-slate-400">서류종류</div><div className="font-medium">{extraction.document_type || '—'}</div></div>
      <div><div className="text-[11px] text-slate-400">성명</div><div className="font-medium">{extraction.name || '—'}</div></div>
      <div><div className="text-[11px] text-slate-400">유효기간</div><div className="num font-medium">{extraction.valid_until || '—'}</div></div>
      <div><div className="text-[11px] text-slate-400">사유 분류(AI)</div><div className="font-medium">{category ?? '모델 미학습'}</div></div>
      {!!extraction.anomaly_flags?.length && (
        <div className="col-span-2 md:col-span-4">
          <div className="text-[11px] text-amber-700">이상 신호</div>
          <ul className="text-amber-700">{extraction.anomaly_flags.map((f, i) => <li key={i}>! {f}</li>)}</ul>
        </div>
      )}
    </div>
  )
}

export default function UploadReviewView() {
  const [file, setFile] = useState<File | null>(null)
  const [militaryNumber, setMilitaryNumber] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const refresh = () => listSubmissions().then((list) => {
    setSubmissions(list)
    setSelectedId((prev) => prev ?? list[0]?.id ?? null)
  }).catch((e: unknown) => setError(e instanceof Error ? e.message : '목록을 불러오지 못했습니다'))

  useEffect(() => { refresh() }, [])

  const selected = submissions.find((s) => s.id === selectedId) ?? null

  const handleUpload = async () => {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const created = await uploadSubmission(file, militaryNumber.trim() || undefined)
      setFile(null)
      setMilitaryNumber('')
      await refresh()
      setSelectedId(created.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : '업로드에 실패했습니다')
    } finally {
      setBusy(false)
    }
  }

  const handleDecision = async (id: string, decision: 'approved' | 'declined') => {
    setBusy(true)
    try {
      await decideSubmission(id, decision)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '처리에 실패했습니다')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <section className="rounded border border-slate-300 bg-white p-4">
        <h2 className="mb-3 text-[14px] font-semibold">서류 업로드</h2>
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={militaryNumber} onChange={(e) => setMilitaryNumber(e.target.value)}
            placeholder="군번 (예: 22-76010001)"
            className="w-52 rounded border border-slate-300 px-2.5 py-1.5 text-[13px] outline-emerald-800"
          />
          <input
            type="file" accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-[13px]"
          />
          <button
            disabled={!file || busy} onClick={handleUpload}
            className="rounded bg-emerald-800 px-3 py-1.5 text-[13px] font-semibold text-white disabled:opacity-50"
          >
            제출 및 AI 분석
          </button>
        </div>
        <p className="mt-2 text-[12px] text-slate-400">제출하면 검토함에 대기 항목으로 추가됩니다. (지금은 매번 새 PDF를 업로드하지만, 나중에는 이미 접수된 서류를 승인/반려만 하는 흐름으로 바뀔 예정입니다.)</p>
        {error && <p className="mt-2 text-[13px] text-rose-700">{error}</p>}
      </section>

      <section className="flex h-[calc(100vh-320px)] min-h-[420px] overflow-hidden rounded border border-slate-300 bg-white">
        <div className="w-[280px] shrink-0 overflow-y-auto border-r border-slate-300">
          <div className="border-b border-slate-200 px-3.5 py-2.5 text-[12.5px] text-slate-500">
            제출 목록 <b className="num text-slate-900">{submissions.length}</b>건
          </div>
          {submissions.length === 0 && <p className="p-4 text-[13px] text-slate-400">제출된 서류가 없습니다.</p>}
          {submissions.map((s) => (
            <button key={s.id} onClick={() => setSelectedId(s.id)}
                    className={`block w-full border-b border-slate-100 px-3.5 py-2.5 text-left ${
                      selectedId === s.id ? 'bg-slate-50 border-l-2 border-l-emerald-800' : 'border-l-2 border-l-transparent hover:bg-slate-50'}`}>
              <div className="flex items-baseline gap-1.5">
                <span className="text-[13.5px] font-semibold">{s.military_number ?? s.filename}</span>
                <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[s.status]}`}>{STATUS_LABEL[s.status]}</span>
              </div>
              <div className="text-[12.5px] text-slate-500">{s.extraction.document_type || s.filename}</div>
              <div className="num text-[11.5px] text-slate-400">제출 {new Date(s.created_at).toLocaleString()}</div>
            </button>
          ))}
        </div>

        <div className="flex flex-1 items-center justify-center bg-slate-100">
          {selected ? (
            <iframe title="서류 원본" src={submissionFileUrl(selected.saved_path)} className="h-full w-full bg-white" />
          ) : (
            <p className="p-10 text-center text-[13.5px] text-slate-400">왼쪽에서 제출 건을 선택하면 원본 PDF가 여기에 표시됩니다.</p>
          )}
        </div>

        {selected && (
          <aside className="w-[300px] shrink-0 overflow-y-auto border-l border-slate-300 p-4">
            <dl className="mb-3 grid grid-cols-[60px_1fr] gap-y-1.5 text-[13px]">
              <dt className="text-slate-500">군번</dt><dd className="num">{selected.military_number ?? '미기재'}</dd>
              <dt className="text-slate-500">파일명</dt><dd>{selected.filename}</dd>
            </dl>
            <ExtractionSummary extraction={selected.extraction} category={selected.reason_category} />
            {selected.status === 'pending' ? (
              <div className="mt-4 flex gap-2">
                <button disabled={busy} onClick={() => handleDecision(selected.id, 'approved')}
                        className="rounded bg-emerald-800 px-3 py-1.5 text-[12.5px] font-semibold text-white disabled:opacity-50">
                  승인
                </button>
                <button disabled={busy} onClick={() => handleDecision(selected.id, 'declined')}
                        className="rounded border border-rose-700 px-3 py-1.5 text-[12.5px] font-semibold text-rose-700 disabled:opacity-50">
                  반려
                </button>
              </div>
            ) : (
              <p className="mt-4 text-[12.5px] text-slate-400">이미 {STATUS_LABEL[selected.status]} 처리됨</p>
            )}
          </aside>
        )}
      </section>
    </div>
  )
}

