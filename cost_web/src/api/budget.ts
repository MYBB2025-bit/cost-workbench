import request from './request'

export function getBudgetListApi(projectId?: number) {
  return request.get('/budget/list', { params: { project_id: projectId } })
}

export function getBudgetTreeApi(projectId: number) {
  return request.get('/budget/tree', { params: { project_id: projectId } })
}

export function createBudgetApi(data: any) {
  return request.post('/budget/create', data)
}

export function updateBudgetApi(id: number, data: any) {
  return request.put(`/budget/${id}`, data)
}

export function deleteBudgetApi(id: number) {
  return request.delete(`/budget/${id}`)
}

export function importBudgetApi(projectId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('project_id', String(projectId))
  return request.post('/budget/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 异步导入（适配大文件，返回 job_id 供轮询进度）
export function importBudgetAsyncApi(projectId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('project_id', String(projectId))
  return request.post('/budget/import-async', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
