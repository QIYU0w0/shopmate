import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '../api/client'

const TOKEN_KEY = 'shopmate-token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<{ id: number; username: string; created_at: string } | null>(null)

  const isAuthed = computed(() => Boolean(token.value && user.value))

  async function register(username: string, password: string) {
    const result = await authApi.register({ username, password })
    token.value = result.token
    user.value = result.user
    localStorage.setItem(TOKEN_KEY, result.token)
  }

  async function login(username: string, password: string) {
    const result = await authApi.login({ username, password })
    token.value = result.token
    user.value = result.user
    localStorage.setItem(TOKEN_KEY, result.token)
  }

  async function loadCurrentUser() {
    if (!token.value) return
    user.value = await authApi.me(token.value)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  return {
    token,
    user,
    isAuthed,
    register,
    login,
    loadCurrentUser,
    logout
  }
})
