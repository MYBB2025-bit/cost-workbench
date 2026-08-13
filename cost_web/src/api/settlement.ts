import request from './request'

export function getSettlementListApi(projectId?: number) {
  return request.get('/settlement/list', { params: { project_id: projectId } })
}

export function getSettlementDetailApi(id: number) {
  return request.get(`/settlement/${id}`)
}

export function createSettlementApi(data: any) {
  return request.post('/settlement/create', data)
}

export function updateSettlementApi(id: number, data: any) {
  return request.put(`/settlement/${id}`, data)
}

export function deleteSettlementApi(id: number) {
  return request.delete(`/settlement/${id}`)
}

export function createSettlementItemApi(settlementId: number, data: any) {
  return request.post(`/settlement/${settlementId}/items`, data)
}

export function updateSettlementItemApi(itemId: number, data: any) {
  return request.put(`/settlement/items/${itemId}`, data)
}

export function deleteSettlementItemApi(itemId: number) {
  return request.delete(`/settlement/items/${itemId}`)
}
