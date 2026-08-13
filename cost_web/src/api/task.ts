import request from './request'

export interface TaskJobVO {
  job_id: string
  task_type: string
  status: 'pending' | 'running' | 'success' | 'failed'
  progress: number
  total: number
  processed: number
  result: any
  error: string | null
  created_by: number | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

// 查询异步任务进度与结果
export function getTaskStatusApi(jobId: string) {
  return request.get<TaskJobVO>(`/task/${jobId}`)
}

// 下载异步任务产出的文件（导出类任务）
export async function downloadTaskApi(jobId: string, filename = 'export.csv') {
  const blob = (await request.get(`/task/${jobId}/download`, {
    responseType: 'blob',
  })) as unknown as Blob
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
