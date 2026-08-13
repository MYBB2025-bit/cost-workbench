import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 与后端 API_PREFIX 对齐；Nginx/本地代理将 /api 转发到 FastAPI
const instance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 请求拦截：附带 JWT
instance.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误与 401 处理；并解包为 resp.data
instance.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail || error.message
    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('perms')
      ElMessage.error('登录已过期，请重新登录')
      router.replace('/login')
    } else if (status === 403) {
      ElMessage.error(`无权限：${detail}`)
    } else {
      ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    }
    return Promise.reject(error)
  },
)

// 响应拦截器已把 resp.data 解包，故把各请求方法重新声明为返回 Promise<T>（默认 any），
// 使调用处直接拿到业务数据（对象/数组），而非 AxiosResponse 包裹。
interface RequestFn {
  <T = any>(config: AxiosRequestConfig): Promise<T>
  get: <T = any>(url: string, config?: AxiosRequestConfig) => Promise<T>
  post: <T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) => Promise<T>
  put: <T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) => Promise<T>
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => Promise<T>
}

const request = ((config: AxiosRequestConfig) => instance(config)) as RequestFn
// 响应拦截器已将 resp.data 解包，故此处把返回值强制声明为业务数据类型 Promise<T>
request.get = <T = any>(url: string, config?: AxiosRequestConfig) => instance.get(url, config) as unknown as Promise<T>
request.post = <T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) => instance.post(url, data, config) as unknown as Promise<T>
request.put = <T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) => instance.put(url, data, config) as unknown as Promise<T>
request.delete = <T = any>(url: string, config?: AxiosRequestConfig) => instance.delete(url, config) as unknown as Promise<T>

export default request
