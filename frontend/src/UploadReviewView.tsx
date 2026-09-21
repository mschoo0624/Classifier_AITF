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

  const refresh = () => listSubmissions().then(setSubmissions).catch((e: unknown) => setError(e instanceof Error ? e.message : '목록을 불러오지 못했습니다'))

  useEffect(() => { refresh() }, [])

  const handleUpload = async () => {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      await uploadSubmission(file, militaryNumber.trim() || undefined)
      setFile(null)
      setMilitaryNumber('')
      await refresh()
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
        <p className="mt-2 text-[12px] text-slate-400">제출하면 검토함에 대기 항목으로 추가됩니다.</p>
        {error && <p className="mt-2 text-[13px] text-rose-700">{error}</p>}
      </section>

      <section className="rounded border border-slate-300 bg-white">
        <div className="border-b border-slate-200 px-4 py-3 text-[13px] text-slate-500">
          제출 이력 <b className="num text-slate-900">{submissions.length}</b>건
        </div>
        {submissions.length === 0 && <p className="p-4 text-[13px] text-slate-400">제출된 서류가 없습니다.</p>}
        <div className="divide-y divide-slate-100">
          {submissions.map((s) => (
            <div key={s.id} className="px-4 py-3">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="font-medium">{s.filename}</span>
                {s.military_number && <span className="num text-[12px] text-slate-500">{s.military_number}</span>}
                <span className={`rounded px-1.5 py-0.5 text-[11.5px] font-semibold ${STATUS_STYLE[s.status]}`}>{STATUS_LABEL[s.status]}</span>
                <a href={submissionFileUrl(s.saved_path)} target="_blank" rel="noopener noreferrer" className="text-[12.5px] text-emerald-800 hover:underline">
                  원본 열기 ↗
                </a>
                <span className="num ml-auto text-[11.5px] text-slate-400">{new Date(s.created_at).toLocaleString()}</span>
              </div>
              <ExtractionSummary extraction={s.extraction} category={s.reason_category} />
              {s.status === 'pending' && (
                <div className="mt-3 flex gap-2">
                  <button disabled={busy} onClick={() => handleDecision(s.id, 'approved')}
                          className="rounded bg-emerald-800 px-3 py-1.5 text-[12.5px] font-semibold text-white disabled:opacity-50">
                    승인
                  </button>
                  <button disabled={busy} onClick={() => handleDecision(s.id, 'declined')}
                          className="rounded border border-rose-700 px-3 py-1.5 text-[12.5px] font-semibold text-rose-700 disabled:opacity-50">
                    반려
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
