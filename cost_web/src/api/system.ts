import request from './request'

// 用户
export const listUsersApi = () => request.get('/system/users')
export const createUserApi = (data: any) => request.post('/system/users', data)
export const updateUserApi = (id: number, data: any) => request.put(`/system/users/${id}`, data)
export const deleteUserApi = (id: number) => request.delete(`/system/users/${id}`)

// 角色
export const listRolesApi = () => request.get('/system/roles')
export const createRoleApi = (data: any) => request.post('/system/roles', data)
export const updateRoleApi = (id: number, data: any) => request.put(`/system/roles/${id}`, data)
export const deleteRoleApi = (id: number) => request.delete(`/system/roles/${id}`)

// 权限
export const listPermissionsApi = () => request.get('/system/permissions')
export const createPermissionApi = (data: any) => request.post('/system/permissions', data)
export const updatePermissionApi = (id: number, data: any) => request.put(`/system/permissions/${id}`, data)
export const deletePermissionApi = (id: number) => request.delete(`/system/permissions/${id}`)

// 灰度发布
export const listGrayReleasesApi = () => request.get('/system/gray-releases')
export const createGrayReleaseApi = (data: any) => request.post('/system/gray-releases', data)
export const updateGrayReleaseApi = (id: number, data: any) => request.put(`/system/gray-releases/${id}`, data)
export const deleteGrayReleaseApi = (id: number) => request.delete(`/system/gray-releases/${id}`)

// 项目选择（分配数据权限）
export const listSystemProjectsApi = () => request.get('/system/projects')
