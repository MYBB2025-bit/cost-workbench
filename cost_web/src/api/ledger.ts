import request from './request'

export function listLedgerApi(projectId?: number) {
  return request.get('/ledger/list', {
    params: projectId ? { project_id: projectId } : {},
  })
}

export function exportLedgerApi(projectId?: number) {
  return request.get('/ledger/export', {
    params: projectId ? { project_id: projectId } : {},
    responseType: 'blob',
  })
}

export function exportLedgerAsyncApi(projectId?: number) {
  return request.get('/ledger/export-async', {
    params: projectId ? { project_id: projectId } : {},
  })
}
