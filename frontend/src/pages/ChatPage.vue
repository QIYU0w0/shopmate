<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useChatStore } from '../stores/chat'

const router = useRouter()
const chatStore = useChatStore()

const draft = ref('')
const localError = ref('')
const quickPrompts = [
  '油皮春夏防晒推荐，预算 100-200',
  '通勤跑鞋推荐，缓震好，预算 300 左右',
  '适合学生党的平板，主要看网课和追剧'
]

const messages = computed(() => chatStore.currentMessages)
const sessions = computed(() => chatStore.sessions)
const products = computed(() => chatStore.currentProducts)

async function bootstrapPage() {
  try {
    await chatStore.bootstrap()
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '加载失败。'
  }
}

onMounted(bootstrapPage)

async function handleSend(message?: string) {
  const content = (message ?? draft.value).trim()
  if (!content || chatStore.busy) return
  draft.value = ''
  localError.value = ''
  try {
    await chatStore.sendMessage(content)
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '发送失败。'
  }
}

async function handleCreateSession() {
  localError.value = ''
  try {
    await chatStore.createSession()
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '创建会话失败。'
  }
}
</script>

<template>
  <section class="workspace-grid">
    <aside class="sidebar-panel">
      <div class="sidebar-head">
        <div>
          <p class="eyebrow">Sessions</p>
          <h2>会话记录</h2>
        </div>
        <button class="ghost-button" type="button" @click="handleCreateSession">新建</button>
      </div>
      <div class="session-list">
        <button
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === chatStore.currentSessionId }"
          type="button"
          @click="chatStore.selectSession(session.id)"
        >
          <strong>{{ session.title }}</strong>
          <span>{{ session.last_message_preview || '还没有消息' }}</span>
          <small>{{ session.category }}</small>
        </button>
      </div>
    </aside>

    <div class="chat-panel">
      <header class="panel-head">
        <div>
          <p class="eyebrow">Streaming Chat</p>
          <h2>多源购物对话</h2>
        </div>
        <button class="primary-button" type="button" @click="router.push('/analysis')">查看分析页</button>
      </header>

      <section class="plan-strip">
        <div>
          <strong>状态</strong>
          <span>{{ chatStore.streamPhase }}</span>
        </div>
        <div>
          <strong>分类</strong>
          <span>{{ chatStore.streamPlan?.category || '待识别' }}</span>
        </div>
        <div>
          <strong>关键词</strong>
          <span>{{ chatStore.streamPlan?.keywords?.join(' / ') || '待抽取' }}</span>
        </div>
      </section>

      <div class="message-board">
        <article v-for="message in messages" :key="message.id" class="bubble" :class="message.role">
          <span class="bubble-role">{{ message.role === 'user' ? '你' : 'ShopMate' }}</span>
          <p>{{ message.content }}</p>
        </article>

        <article v-if="chatStore.streamingReply" class="bubble assistant">
          <span class="bubble-role">ShopMate</span>
          <p>{{ chatStore.streamingReply }}</p>
        </article>

        <div v-if="products.length > 0" class="result-preview">
          <header class="section-head">
            <h3>当前商品结果</h3>
            <span>{{ products.length }} 个候选</span>
          </header>
          <div class="preview-grid">
            <div v-for="product in products.slice(0, 3)" :key="product.id" class="mini-card">
              <img :src="product.image_url" :alt="product.title" />
              <div>
                <strong>{{ product.title }}</strong>
                <span>{{ product.brand }} · {{ product.platform }}</span>
                <small>¥{{ product.price }}</small>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="composer-panel">
        <div class="prompt-row">
          <button v-for="prompt in quickPrompts" :key="prompt" class="pill-button" type="button" @click="handleSend(prompt)">
            {{ prompt }}
          </button>
        </div>
        <textarea
          v-model="draft"
          class="chat-input"
          placeholder="描述你的购物需求，例如：预算、场景、偏好、品类。"
          rows="4"
        />
        <div class="composer-foot">
          <p v-if="localError" class="error-text">{{ localError }}</p>
          <button class="primary-button" type="button" :disabled="chatStore.busy" @click="handleSend()">
            {{ chatStore.busy ? '生成中...' : '发送并搜索' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
