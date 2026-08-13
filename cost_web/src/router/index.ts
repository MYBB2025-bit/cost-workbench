import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/store/user'
import { usePermissionStore } from '@/store/permission'

export const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'layout',
    component: () => import('@/components/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard.vue'),
        meta: { title: '仪表盘' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes,
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) return next()
  if (!token) return next('/login')

  const user = useUserStore()
  const perm = usePermissionStore()
  // 已登录但未构建动态路由
  if (perm.routes.length === 0 && to.path !== '/login') {
    try {
      await user.fetchProfile()
      await perm.generateRoutes()
      // 重新进入目标路由以匹配新加的路由
      return next({ ...to, replace: true })
    } catch (e) {
      localStorage.removeItem('token')
      return next('/login')
    }
  }
  next()
})

export default router
