import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RouteRecordRaw } from 'vue-router'
import { getMenuListApi } from '@/api/auth'
import router from '@/router'

// 菜单路径 → 视图组件（避免动态拼路径的脆弱性）
const viewMap: Record<string, () => Promise<unknown>> = {
  '/dashboard': () => import('@/views/dashboard.vue'),
  '/project': () => import('@/views/project/index.vue'),
  '/progress': () => import('@/views/progress/index.vue'),
  '/pricing': () => import('@/views/pricing/index.vue'),
  '/budget': () => import('@/views/budget/index.vue'),
  '/change': () => import('@/views/change/index.vue'),
  '/settlement': () => import('@/views/settlement/index.vue'),
  '/risk': () => import('@/views/risk/index.vue'),
  '/ledger': () => import('@/views/ledger/index.vue'),
  '/cost-dashboard': () => import('@/views/cost-dashboard/index.vue'),
  '/client/version-manage': () => import('@/views/client/version-manage.vue'),
  '/system/users': () => import('@/views/system/users.vue'),
  '/system/roles': () => import('@/views/system/roles.vue'),
  '/system/perms': () => import('@/views/system/perms.vue'),
  '/system/gray': () => import('@/views/system/gray.vue'),
}

export const usePermissionStore = defineStore('permission', () => {
  const menus = ref<any[]>([])
  const routes = ref<RouteRecordRaw[]>([])

  function transformMenuToRoute(menuList: any[]): RouteRecordRaw[] {
    return (menuList || []).map((m) => ({
      path: m.path,
      name: m.path.replace(/\//g, '-'),
      component: viewMap[m.path] || viewMap['/dashboard'],
      meta: { title: m.name, perm: m.perm },
    }))
  }

  const generateRoutes = async () => {
    const res = await getMenuListApi()
    // /dashboard 已是常量路由，避免重复挂载
    const dynamic = (res.menus || []).filter((m: any) => m.path !== '/dashboard')
    menus.value = dynamic
    const accessRoutes = transformMenuToRoute(dynamic)
    accessRoutes.forEach((r) => router.addRoute('layout', r))
    routes.value = accessRoutes
    return accessRoutes
  }

  return { menus, routes, generateRoutes }
})
