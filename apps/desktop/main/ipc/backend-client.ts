import fs from 'fs/promises'
import path from 'path'
import type { ReduceProgressData, SubmitReducedAnalysisPayload, SubmitReducedAnalysisResult } from '@log-sparkui/ipc-types'

type ReduceBackendResponse = {
  reduced_report: string
  summary: unknown
  reduce_job_id?: string
}

export async function reduceZipViaPath(
  apiBaseUrl: string,
  zipPath: string,
  compact: boolean,
  reduceJobId: string,
): Promise<ReduceBackendResponse> {
  const form = new FormData()
  form.append('file_path', zipPath)
  form.append('reduce_job_id', reduceJobId)
  if (compact) form.append('compact', 'true')

  const res = await fetch(`${apiBaseUrl}/api/reduce-local-path`, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`reduce-local-path failed (${res.status}): ${errText}`)
  }

  return (await res.json()) as ReduceBackendResponse
}

/**
 * Progress polling with exponential backoff.
 * Starts at 500ms, doubles up to 5s max interval.
 */
export function startProgressPoll(
  apiBaseUrl: string,
  reduceJobId: string,
  sender: Electron.WebContents,
): ReturnType<typeof setInterval> {
  let intervalMs = 500
  const MAX_INTERVAL = 5000
  const timerId = setInterval(async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/reduce-progress/${reduceJobId}`)
      if (!res.ok) return
      const data = (await res.json()) as ReduceProgressData
      sender.send('reduce-progress', data)

      // Exponential backoff: double interval when progress stalls
      const percent = data.percent ?? 0
      if (percent < 100 && percent > 5) {
        intervalMs = Math.min(intervalMs * 2, MAX_INTERVAL)
        clearInterval(timerId)
        // Restart with new interval
        const newTimer = startProgressPollWithInterval(apiBaseUrl, reduceJobId, sender, intervalMs)
        // Store reference for cleanup
        ;(timerId as any)._replacement = newTimer
      } else if (percent >= 100) {
        clearInterval(timerId)
      }
    } catch {
      // Swallow transient polling errors; the next tick retries.
    }
  }, intervalMs)

  return timerId
}

function startProgressPollWithInterval(
  apiBaseUrl: string,
  reduceJobId: string,
  sender: Electron.WebContents,
  intervalMs: number,
): ReturnType<typeof setInterval> {
  return setInterval(async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/reduce-progress/${reduceJobId}`)
      if (!res.ok) return
      const data = (await res.json()) as ReduceProgressData
      sender.send('reduce-progress', data)

      const percent = data.percent ?? 0
      if (percent >= 100) {
        clearInterval(timerId)
      }
    } catch {
      // Swallow transient polling errors
    }
  }, intervalMs)
}

export async function submitReducedAnalysis(
  apiBaseUrl: string,
  payload: SubmitReducedAnalysisPayload,
): Promise<SubmitReducedAnalysisResult> {
  const reducedReport = payload?.reducedReport
  const pyFilePaths = payload?.pyFilePaths || []
  const sparklensContext = payload?.sparklensContext
  const llmProvider = payload?.llmProvider
  const apiKey = payload?.apiKey
  const userId = payload?.userId
  const language = payload?.language || 'en'

  if (!reducedReport || !String(reducedReport).trim()) {
    throw new Error('reducedReport is required')
  }

  const form = new FormData()
  form.append('reduced_report', reducedReport)
  form.append('language', language)
  if (sparklensContext) form.append('sparklens_context', JSON.stringify(sparklensContext))
  if (llmProvider) form.append('llm_provider', llmProvider)
  if (apiKey) form.append('api_key', apiKey)
  if (userId) form.append('user_id', userId)

  for (const filePath of pyFilePaths) {
    // Use streams instead of reading entire file into memory
    const fileName = path.basename(filePath)
    const fileStream = await import('fs').then(fs => fs.createReadStream(filePath))
    form.append('pyspark_files', fileStream, fileName)
  }

  const res = await fetch(`${apiBaseUrl}/api/upload-reduced`, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`upload-reduced failed (${res.status}): ${errText}`)
  }

  return (await res.json()) as SubmitReducedAnalysisResult
}
