import request from './request'

export function listProjectsApi() {
  return request.get('/project/list')
}

export function createProjectApi(data: Record<string, any>) {
  return request.post('/project/create', data)
}

export function updateProjectApi(id: number, data: Record<string, any>) {
  return request.put(`/project/${id}`, data)
}

export function deleteProjectApi(id: number) {
  return request.delete(`/project/${id}`)
}
