<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, type ComponentPublicInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'

const authStore = useAuthStore()
const chatStore = useChatStore()
const router = useRouter()
const route = useRoute()

const isCollapsed = ref(false)
const activeMenuSessionId = ref<string | null>(null)
const renamingSessionId = ref<string | null>(null)
const renameDraft = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)
const menuPosition = ref<{ top: number; left: number } | null>(null)
const sessions = computed(() => chatStore.sessions)
const currentSessionId = computed(() => chatStore.currentSessionId)
const displayName = computed(() => authStore.user?.username || 'Guest')
const activeMenuSession = computed(
  () => sessions.value.find((session) => session.id === activeMenuSessionId.value) || null
)

function closeSessionMenu() {
  activeMenuSessionId.value = null
  menuPosition.value = null
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (!target) return
  if (target.closest('.sidebar-sessionmenu') || target.closest('.sidebar-menu-trigger')) {
    return
  }
  closeSessionMenu()
}

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick)
  window.addEventListener('resize', closeSessionMenu)
  window.addEventListener('scroll', closeSessionMenu, true)
  if (!chatStore.sessions.length && authStore.token) {
    try {
      await chatStore.refreshSessions()
    } catch {
      // The page-level view handles request errors.
    }
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  window.removeEventListener('resize', closeSessionMenu)
  window.removeEventListener('scroll', closeSessionMenu, true)
})

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
  if (isCollapsed.value) {
    closeSessionMenu()
  }
}

function setRenameInputRef(element: Element | ComponentPublicInstance | null) {
  renameInputRef.value = element instanceof HTMLInputElement ? element : null
}

async function handleCreateSession() {
  await chatStore.createSession()
  closeSessionMenu()
  renamingSessionId.value = null
  if (route.path !== '/chat') {
    router.push('/chat')
  }
}

async function handleSelectSession(sessionId: string) {
  if (renamingSessionId.value === sessionId) return
  closeSessionMenu()
  await chatStore.selectSession(sessionId)
}

function toggleMenu(sessionId: string, event: MouseEvent) {
  const trigger = event.currentTarget as HTMLElement | null
  if (!trigger) return
  if (activeMenuSessionId.value === sessionId) {
    closeSessionMenu()
    return
  }
  const rect = trigger.getBoundingClientRect()
  activeMenuSessionId.value = sessionId
  menuPosition.value = {
    top: rect.top + rect.height / 2,
    left: rect.right + 8
  }
}

async function startRename(sessionId: string, currentTitle: string) {
  closeSessionMenu()
  renamingSessionId.value = sessionId
  renameDraft.value = currentTitle
  await nextTick()
  renameInputRef.value?.focus()
  renameInputRef.value?.select()
}

function cancelRename() {
  renamingSessionId.value = null
  renameDraft.value = ''
}

async function submitRename(sessionId: string) {
  const nextTitle = renameDraft.value.trim()
  if (!nextTitle) {
    cancelRename()
    return
  }
  await chatStore.renameSession(sessionId, nextTitle)
  cancelRename()
}

async function handleDeleteSession(sessionId: string) {
  closeSessionMenu()
  if (!window.confirm('确认删除这个会话吗？')) return
  await chatStore.deleteSession(sessionId)
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
      <div
        v-for="session in sessions"
        :key="session.id"
        class="sidebar-sessionrow"
        :class="{ active: session.id === currentSessionId, 'menu-open': session.id === activeMenuSessionId }"
      >
        <button
          v-if="renamingSessionId !== session.id"
          class="sidebar-sessionitem"
          type="button"
          :title="session.title"
          @click="handleSelectSession(session.id)"
        >
          <span class="session-title">{{ session.title }}</span>
        </button>

        <form v-else class="sidebar-renameform" @submit.prevent="submitRename(session.id)" @click.stop>
          <input
            :ref="setRenameInputRef"
            v-model.trim="renameDraft"
            class="sidebar-renameinput"
            type="text"
            maxlength="80"
            @keydown.esc.prevent="cancelRename"
            @blur="submitRename(session.id)"
          />
        </form>

        <button
          v-if="renamingSessionId !== session.id"
          class="sidebar-menu-trigger"
          type="button"
          @click.stop="toggleMenu(session.id, $event)"
        >
          ⋯
        </button>
      </div>

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

  <Teleport to="body">
    <div
      v-if="activeMenuSession && menuPosition"
      class="sidebar-sessionmenu"
      :style="{ top: `${menuPosition.top}px`, left: `${menuPosition.left}px` }"
      @click.stop
    >
      <button type="button" @click="startRename(activeMenuSession.id, activeMenuSession.title)">重命名</button>
      <button type="button" class="danger" @click="handleDeleteSession(activeMenuSession.id)">删除</button>
    </div>
  </Teleport>
</template>
