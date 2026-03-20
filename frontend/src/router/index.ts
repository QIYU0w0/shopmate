import { createRouter, createWebHistory } from 'vue-router'

import AnalysisPage from '../pages/AnalysisPage.vue'
import ChatPage from '../pages/ChatPage.vue'
import LoginPage from '../pages/LoginPage.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    { path: '/login', component: LoginPage },
    { path: '/chat', component: ChatPage, meta: { requiresAuth: true } },
    { path: '/analysis', component: AnalysisPage, meta: { requiresAuth: true } }
  ]
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (authStore.token && !authStore.user) {
    try {
      await authStore.loadCurrentUser()
    } catch {
      authStore.logout()
    }
  }
  if (to.meta.requiresAuth && !authStore.isAuthed) {
    return '/login'
  }
  if (to.path === '/login' && authStore.isAuthed) {
    return '/chat'
  }
  return true
})

export default router
