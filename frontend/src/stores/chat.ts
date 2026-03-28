import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { chatApi, streamChatReply, type ChatMessage, type Product, type SessionFacets, type SessionStats, type SessionSummary } from '../api/client'
import { useAuthStore } from './auth'

export const useChatStore = defineStore('chat', () => {
  const authStore = useAuthStore()

  const sessions = ref<SessionSummary[]>([])
  const currentSessionId = ref<string | null>(null)
  const messagesBySession = ref<Record<string, ChatMessage[]>>({})
  const productsBySession = ref<Record<string, Product[]>>({})
  const facetsBySession = ref<Record<string, SessionFacets>>({})
  const statsBySession = ref<Record<string, SessionStats>>({})
  const streamingReply = ref('')
  const streamPhase = ref('idle')
  const streamPlan = ref<any>(null)
  const busy = ref(false)

  const currentMessages = computed(() =>
    currentSessionId.value ? messagesBySession.value[currentSessionId.value] || [] : []
  )
  const currentProducts = computed(() =>
    currentSessionId.value ? productsBySession.value[currentSessionId.value] || [] : []
  )
  const currentFacets = computed(() =>
    currentSessionId.value ? facetsBySession.value[currentSessionId.value] || null : null
  )
  const currentStats = computed(() =>
    currentSessionId.value ? statsBySession.value[currentSessionId.value] || null : null
  )

  function requireToken() {
    if (!authStore.token) {
      throw new Error('Missing auth token')
    }
    return authStore.token
  }

  function isSessionUntouched(sessionId: string) {
    const session = sessions.value.find((item) => item.id === sessionId)
    if (!session) return false
    const messages = messagesBySession.value[sessionId] || []
    const products = productsBySession.value[sessionId] || []
    return session.last_message_preview.trim() === '' && messages.length === 0 && products.length === 0
  }

  async function refreshSessions() {
    const token = requireToken()
    sessions.value = await chatApi.listSessions(token)
    if (!currentSessionId.value && sessions.value.length > 0) {
      currentSessionId.value = sessions.value[0].id
    }
  }

  async function createSession(title?: string) {
    if (!title && currentSessionId.value && isSessionUntouched(currentSessionId.value)) {
      return sessions.value.find((session) => session.id === currentSessionId.value) as SessionSummary
    }

    const token = requireToken()
    const session = await chatApi.createSession(token, title)
    sessions.value = [session, ...sessions.value.filter((item) => item.id !== session.id)]
    currentSessionId.value = session.id
    messagesBySession.value[session.id] = messagesBySession.value[session.id] || []
    productsBySession.value[session.id] = productsBySession.value[session.id] || []
    return session
  }

  async function selectSession(sessionId: string) {
    currentSessionId.value = sessionId
    await Promise.all([loadMessages(sessionId), loadProducts(sessionId), loadFacets(sessionId), loadStats(sessionId)])
  }

  async function loadMessages(sessionId: string) {
    const token = requireToken()
    messagesBySession.value[sessionId] = await chatApi.listMessages(token, sessionId)
  }

  async function loadProducts(sessionId: string) {
    const token = requireToken()
    productsBySession.value[sessionId] = await chatApi.listProducts(token, sessionId)
  }

  async function loadFacets(sessionId: string) {
    const token = requireToken()
    facetsBySession.value[sessionId] = await chatApi.listFacets(token, sessionId)
  }

  async function loadStats(sessionId: string) {
    const token = requireToken()
    statsBySession.value[sessionId] = await chatApi.listStats(token, sessionId)
  }

  async function renameSession(sessionId: string, title: string) {
    const token = requireToken()
    const updated = await chatApi.renameSession(token, sessionId, title)
    sessions.value = sessions.value.map((session) => (session.id === sessionId ? updated : session))
    return updated
  }

  async function deleteSession(sessionId: string) {
    const token = requireToken()
    await chatApi.deleteSession(token, sessionId)
    sessions.value = sessions.value.filter((session) => session.id !== sessionId)
    delete messagesBySession.value[sessionId]
    delete productsBySession.value[sessionId]
    delete facetsBySession.value[sessionId]
    delete statsBySession.value[sessionId]

    if (currentSessionId.value === sessionId) {
      currentSessionId.value = sessions.value[0]?.id || null
      if (currentSessionId.value) {
        await selectSession(currentSessionId.value)
      }
    }
  }

  async function bootstrap() {
    await refreshSessions()
    if (currentSessionId.value) {
      await selectSession(currentSessionId.value)
    }
  }

  async function sendMessage(message: string) {
    const token = requireToken()
    busy.value = true
    streamingReply.value = ''
    streamPlan.value = null
    try {
      if (!currentSessionId.value) {
        await createSession(message.slice(0, 18))
      }
      const sessionId = currentSessionId.value as string
      const optimisticMessage: ChatMessage = {
        id: `local-${Date.now()}`,
        role: 'user',
        content: message,
        created_at: new Date().toISOString()
      }
      messagesBySession.value[sessionId] = [...(messagesBySession.value[sessionId] || []), optimisticMessage]
      await streamChatReply(token, sessionId, message, {
        onStatus(payload) {
          streamPhase.value = payload.label || payload.phase
        },
        onPlan(payload) {
          streamPlan.value = payload
        },
        onToken(payload) {
          streamingReply.value += payload.content || ''
        },
        async onProducts() {
          await Promise.all([loadProducts(sessionId), loadFacets(sessionId), loadStats(sessionId), refreshSessions()])
        },
        async onDone() {
          await loadMessages(sessionId)
          await refreshSessions()
          streamingReply.value = ''
          streamPhase.value = '完成'
        }
      })
    } finally {
      busy.value = false
    }
  }

  return {
    sessions,
    currentSessionId,
    currentMessages,
    currentProducts,
    currentFacets,
    currentStats,
    streamingReply,
    streamPhase,
    streamPlan,
    busy,
    refreshSessions,
    createSession,
    renameSession,
    deleteSession,
    selectSession,
    bootstrap,
    sendMessage
  }
})
