import { defineStore } from 'pinia'
import { ref } from 'vue'
import { loginApi, getMeApi } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref('')
  const realName = ref('')
  const roles = ref<string[]>([])
  const perms = ref<string[]>([])

  async function login(user: string, pwd: string) {
    const res = await loginApi(user, pwd)
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    await fetchProfile()
  }

  async function fetchProfile() {
    const me = await getMeApi()
    username.value = me.username
    realName.value = me.real_name
    roles.value = me.roles || []
    perms.value = me.perms || []
    localStorage.setItem('perms', (perms.value || []).join(','))
  }

  function logout() {
    token.value = ''
    username.value = ''
    perms.value = []
    roles.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('perms')
  }

  return { token, username, realName, roles, perms, login, fetchProfile, logout }
})
