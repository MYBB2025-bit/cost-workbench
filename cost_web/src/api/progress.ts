import request from './request'

export function listProgressApi() {
  return request.get('/progress/list')
}

export function createProgressApi(data: Record<string, any>) {
  return request.post('/progress/create', data)
}

export function paymentStatsApi(projectId: number) {
  return request.get(`/progress/payment-stats/${projectId}`)
}

export function upsertPaymentNodeApi(data: Record<string, any>) {
  return request.post('/progress/payment-node', data)
}

export function listRiskItemsApi() {
  return request.get('/risk/items')
}

export function listWarningsApi() {
  return request.get('/risk/warnings')
}

export function createRiskItemApi(data: Record<string, any>) {
  return request.post('/risk/items', data)
}

export function updateRiskItemApi(id: number, data: Record<string, any>) {
  return request.put(`/risk/items/${id}`, data)
}

export function deleteRiskItemApi(id: number) {
  return request.delete(`/risk/items/${id}`)
}

export function listLedgerApi() {
  return request.get('/ledger/list')
}

export function listPricingApi(projectId?: number) {
  return request.get('/pricing/list', { params: projectId ? { project_id: projectId } : {} })
}
