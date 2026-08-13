import request from './request'

export function getCostOverviewApi(projectId?: number) {
  return request.get('/stats/cost-overview', {
    params: projectId ? { project_id: projectId } : {},
  })
}
