<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppSidebar from './components/AppSidebar.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const isAuthed = computed(() => authStore.isAuthed)
const showSidebar = computed(() => isAuthed.value && route.path !== '/login')

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
  <div class="app-shell" :class="{ 'app-shell--with-sidebar': showSidebar }">
    <AppSidebar v-if="showSidebar" />
    <main class="page-wrap" :class="{ 'page-wrap--with-sidebar': showSidebar }">
      <RouterView />
    </main>
  </div>
</template>
