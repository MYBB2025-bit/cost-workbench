import request from './request'

export function getChangeListApi(projectId?: number) {
  return request.get('/change/list', { params: { project_id: projectId } })
}

export function getChangeDetailApi(id: number) {
  return request.get(`/change/${id}`)
}

export function createChangeApi(data: any) {
  return request.post('/change/create', data)
}

export function updateChangeApi(id: number, data: any) {
  return request.put(`/change/${id}`, data)
}

export function deleteChangeApi(id: number) {
  return request.delete(`/change/${id}`)
}

export function createChangeItemApi(changeId: number, data: any) {
  return request.post(`/change/${changeId}/items`, data)
}

export function updateChangeItemApi(itemId: number, data: any) {
  return request.put(`/change/items/${itemId}`, data)
}

export function deleteChangeItemApi(itemId: number) {
  return request.delete(`/change/items/${itemId}`)
}

export function getVisaListApi(projectId?: number) {
  return request.get('/change/visa/list', { params: { project_id: projectId } })
}

export function createVisaApi(data: any) {
  return request.post('/change/visa/create', data)
}

export function updateVisaApi(id: number, data: any) {
  return request.put(`/change/visa/${id}`, data)
}

export function deleteVisaApi(id: number) {
  return request.delete(`/change/visa/${id}`)
}
