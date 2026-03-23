<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'

const authStore = useAuthStore()
const chatStore = useChatStore()
const router = useRouter()
const route = useRoute()

const isCollapsed = ref(false)
const sessions = computed(() => chatStore.sessions)
const currentSessionId = computed(() => chatStore.currentSessionId)
const displayName = computed(() => authStore.user?.username || 'Guest')

onMounted(async () => {
  if (!chatStore.sessions.length && authStore.token) {
    try {
      await chatStore.refreshSessions()
    } catch {
      // The page-level view handles request errors.
    }
  }
})

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
}

async function handleCreateSession() {
  await chatStore.createSession()
  if (route.path !== '/chat') {
    router.push('/chat')
  }
}

async function handleSelectSession(sessionId: string) {
  await chatStore.selectSession(sessionId)
}

function handleLogout() {
  authStore.logout()
  router.replace('/login')
}
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-brandbar">
      <div v-if="!isCollapsed" class="sidebar-brand">
        <span class="sidebar-brand-badge">S</span>
        <span class="sidebar-brand-text">ShopMate</span>
      </div>
      <button class="ghost-icon-button sidebar-toggle" type="button" @click="toggleSidebar">
        {{ isCollapsed ? '›' : '‹' }}
      </button>
    </div>

    <button v-if="!isCollapsed" class="sidebar-newchat" type="button" @click="handleCreateSession">
      <span class="sidebar-plus">+</span>
      <span class="sidebar-newchat-label">新建对话</span>
      <span class="sidebar-newchat-spacer" aria-hidden="true"></span>
    </button>

    <div v-if="!isCollapsed" class="sidebar-sessionlist">
      <button
        v-for="session in sessions"
        :key="session.id"
        class="sidebar-sessionitem"
        :class="{ active: session.id === currentSessionId }"
        type="button"
        :title="session.title"
        @click="handleSelectSession(session.id)"
      >
        <span class="session-title">{{ session.title }}</span>
      </button>

      <div v-if="!sessions.length" class="sidebar-empty">还没有会话</div>
    </div>

    <div v-if="!isCollapsed" class="sidebar-account">
      <div class="account-meta">
        <span class="account-avatar">{{ displayName.slice(0, 1).toUpperCase() }}</span>
        <div class="account-copy">
          <strong>{{ displayName }}</strong>
          <span>{{ route.path === '/analysis' ? '分析页' : '对话页' }}</span>
        </div>
      </div>
      <button class="ghost-button sidebar-logout" type="button" @click="handleLogout">
        退出
      </button>
    </div>
  </aside>
</template>
