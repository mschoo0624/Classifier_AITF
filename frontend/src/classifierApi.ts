// classifier/API.py 호출 (PDF 업로드 → AI 추출/분류 → 관리자 승인/반려).
// vite.config.ts 의 /classifier-api 프록시가 http://localhost:8001 로 연결합니다.

const CLASSIFIER_API_BASE = import.meta.env.VITE_CLASSIFIER_API_BASE_URL ?? '/classifier-api'

export type ExtractionFields = {
  name?: string
  valid_until?: string
  document_type?: string
  stamp_present?: boolean
  confidence?: number
  anomaly_flags?: string[]
  source_file?: string | null
  error?: string
  _errors?: string[]
  _raw_error?: string
}

export type SubmissionStatus = 'pending' | 'approved' | 'declined'

export type Submission = {
  id: string
  filename: string
  saved_path: string
  military_number: string | null
  extraction: ExtractionFields
  reason_category: string | null
  status: SubmissionStatus
  note: string | null
  created_at: string
  decided_at: string | null
}

// saved_path 는 백엔드 루트 기준 경로(/uploads/...)이므로, 프론트엔드 자체 경로가
// 아니라 /classifier-api 프록시를 거쳐 백엔드로 가도록 앞에 붙여줘야 합니다.
export function submissionFileUrl(savedPath: string): string {
  return `${CLASSIFIER_API_BASE}${savedPath}`
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `요청 실패 (${res.status})`)
  }
  return res.json() as Promise<T>
}

export async function uploadSubmission(file: File, militaryNumber?: string): Promise<Submission> {
  const form = new FormData()
  form.append('file', file)
  if (militaryNumber) form.append('military_number', militaryNumber)
  const res = await fetch(`${CLASSIFIER_API_BASE}/submissions`, { method: 'POST', body: form })
  return handle<Submission>(res)
}

export async function listSubmissions(): Promise<Submission[]> {
  const res = await fetch(`${CLASSIFIER_API_BASE}/submissions`)
  return handle<Submission[]>(res)
}

export async function decideSubmission(
  id: string,
  decision: 'approved' | 'declined',
  note?: string,
): Promise<Submission> {
  const res = await fetch(`${CLASSIFIER_API_BASE}/submissions/${id}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, note }),
  })
  return handle<Submission>(res)
}
