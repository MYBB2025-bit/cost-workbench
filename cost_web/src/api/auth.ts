import request from './request'

export function loginApi(username: string, password: string) {
  // OAuth2 表单
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  return request.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export function getMeApi() {
  return request.get('/auth/me')
}

export function getMenuListApi() {
  return request.get('/auth/menu')
}
