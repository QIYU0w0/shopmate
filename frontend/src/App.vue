<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const isAuthed = computed(() => authStore.isAuthed)

function handleLogout() {
  authStore.logout()
  router.replace('/login')
}

onMounted(async () => {
  if (authStore.token && !authStore.user) {
    try {
      await authStore.loadCurrentUser()
    } catch {
      authStore.logout()
      if (route.path !== '/login') {
        router.replace('/login')
      }
    }
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Multi-source Shopping Copilot</p>
        <h1>ShopMate</h1>
      </div>
      <nav class="topnav">
        <RouterLink v-if="isAuthed" to="/chat">对话页</RouterLink>
        <RouterLink v-if="isAuthed" to="/analysis">分析页</RouterLink>
        <button v-if="isAuthed" class="ghost-button" type="button" @click="handleLogout">退出</button>
      </nav>
    </header>
    <main class="page-wrap">
      <RouterView />
    </main>
  </div>
</template>
