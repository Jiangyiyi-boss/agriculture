import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import { useAiChatStore } from './aiChat'

export interface AuthUser {
  id: number
  phone: string
  name: string
  role: number
  avatar: string | null
  region: string | null
  bio: string | null
  specialty: string | null
  title: string | null
  status: number
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<AuthUser | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  function setToken(t: string | null) {
    token.value = t
    if (t) {
      localStorage.setItem('access_token', t)
    } else {
      localStorage.removeItem('access_token')
    }
  }

  async function fetchUser() {
    if (!token.value) return
    loading.value = true
    try {
      const u = await api.getMe()
      user.value = u as AuthUser
    } catch {
      user.value = null
      setToken(null)
    } finally {
      loading.value = false
    }
  }

  async function login(phone: string, password: string, remember = false) {
    const res = await api.login(phone, password, remember)
    if (res.must_change_password) {
      // 专家首次登录强制改密：返回标记，由前端引导走改密流程
      return { mustChangePassword: true } as const
    }
    setToken(res.access_token)
    await fetchUser()
    return { mustChangePassword: false } as const
  }

  async function adminLogin(phone: string, password: string, remember = false) {
    const res = await api.adminLogin(phone, password, remember)
    setToken(res.access_token)
    await fetchUser()
  }

  async function smsLogin(phone: string, code: string, remember = false) {
    const res = await api.smsLogin(phone, code, remember)
    setToken(res.access_token)
    await fetchUser()
  }

  async function register(phone: string, code: string, password: string, name: string) {
    const res = await api.register(phone, code, password, name)
    setToken(res.access_token)
    await fetchUser()
  }

  function logout() {
    setToken(null)
    user.value = null
    // 登出时清空 AI 会话记忆，下次登录进来是新会话
    useAiChatStore().clear()
  }

  return { token, user, loading, isLoggedIn, setToken, fetchUser, login, adminLogin, smsLogin, register, logout }
})
