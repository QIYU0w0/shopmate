<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')
const loading = ref(false)

async function handleSubmit() {
  errorMessage.value = ''
  if (mode.value === 'register' && password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。'
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await authStore.login(username.value, password.value)
    } else {
      await authStore.register(username.value, password.value)
    }
    router.replace('/chat')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提交失败，请重试。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="hero-grid">
    <aside class="hero-card">
      <p class="eyebrow">Graduation Project</p>
      <h2>基于多源数据融合的智能购物助手</h2>
      <p class="lead">
        通过 AI 对话提炼购物意图，自动抽取关键词，联动种草内容和电商结果，输出可筛选、可视化、跨品类的商品分析结果。
      </p>
      <div class="hero-metrics">
        <div>
          <strong>流式对话</strong>
          <span>即时反馈关键词与任务状态</span>
        </div>
        <div>
          <strong>多源融合</strong>
          <span>真实 MCP 可插拔，默认稳定 mock 兜底</span>
        </div>
        <div>
          <strong>动态维度</strong>
          <span>品牌 / 平台 / 价格固定，二级维度按品类自动生成</span>
        </div>
      </div>
    </aside>

    <section class="auth-card">
      <div class="auth-tabs">
        <button :class="{ active: mode === 'login' }" type="button" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" type="button" @click="mode = 'register'">注册</button>
      </div>
      <form class="auth-form" @submit.prevent="handleSubmit">
        <label>
          <span>用户名</span>
          <input v-model.trim="username" type="text" placeholder="输入用户名" minlength="3" maxlength="24" required />
        </label>
        <label>
          <span>密码</span>
          <input v-model="password" type="password" placeholder="至少 6 位" minlength="6" maxlength="64" required />
        </label>
        <label v-if="mode === 'register'">
          <span>确认密码</span>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="再次输入密码"
            minlength="6"
            maxlength="64"
            required
          />
        </label>
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        <button class="primary-button" type="submit" :disabled="loading">
          {{ loading ? '提交中...' : mode === 'login' ? '进入 ShopMate' : '创建账号' }}
        </button>
      </form>
    </section>
  </section>
</template>
