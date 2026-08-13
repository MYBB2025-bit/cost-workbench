import request from './request'

export function checkVersionApi(localVer: string) {
  return request.get('/client/version/check', { params: { local_ver: localVer } })
}

export function publishVersionApi(data: {
  version_code: string
  version_desc?: string
  force_update?: boolean
  min_compat_version?: string
}) {
  return request.post('/client/version/publish', data)
}

export function uploadPatchApi(fromVersion: string, toVersion: string, file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post(`/client/patch/upload?from_version=${fromVersion}&to_version=${toVersion}`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listVersionsApi() {
  return request.get('/client/version/list')
}

export function listPatchesApi() {
  return request.get('/client/patch/list')
}
