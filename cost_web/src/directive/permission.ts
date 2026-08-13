import type { App, Directive } from 'vue'

// v-permission：无权限则移除元素（按钮级功能权限）
const permissionDirective: Directive = {
  mounted(el: HTMLElement, binding: any) {
    const perms: string[] = binding.value
    const userPerms = (localStorage.getItem('perms') || '').split(',').filter(Boolean)
    const has = perms.some((p) => userPerms.includes(p) || userPerms.includes('*'))
    if (!has) el.remove()
  },
}

export function setupPermissionDirective(app: App) {
  app.directive('permission', permissionDirective)
}
