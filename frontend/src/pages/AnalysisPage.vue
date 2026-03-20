<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import ChartCard from '../components/ChartCard.vue'
import ProductCard from '../components/ProductCard.vue'
import { useChatStore } from '../stores/chat'

const router = useRouter()
const chatStore = useChatStore()

const selectedBrand = ref('')
const selectedPlatform = ref('')
const priceMin = ref('')
const priceMax = ref('')
const selectedFacets = ref<Record<string, string[]>>({})
const selectedProductId = ref<string | null>(null)

onMounted(async () => {
  if (!chatStore.sessions.length) {
    await chatStore.bootstrap()
  }
})

const products = computed(() => chatStore.currentProducts)
const facets = computed(() => chatStore.currentFacets)
const stats = computed(() => chatStore.currentStats)
const selectedProduct = computed(() => products.value.find((item) => item.id === selectedProductId.value) || null)

watch(
  () => chatStore.currentSessionId,
  () => {
    selectedBrand.value = ''
    selectedPlatform.value = ''
    priceMin.value = ''
    priceMax.value = ''
    selectedFacets.value = {}
    selectedProductId.value = null
  }
)

const filteredProducts = computed(() =>
  products.value.filter((product) => {
    if (selectedBrand.value && product.brand !== selectedBrand.value) return false
    if (selectedPlatform.value && product.platform !== selectedPlatform.value) return false
    if (priceMin.value && product.price < Number(priceMin.value)) return false
    if (priceMax.value && product.price > Number(priceMax.value)) return false
    for (const [facetKey, values] of Object.entries(selectedFacets.value)) {
      if (!values.length) continue
      const candidateValues = product.dynamic_facets[facetKey] || []
      if (!values.some((value) => candidateValues.includes(value))) {
        return false
      }
    }
    return true
  })
)

const dynamicCharts = computed(() => {
  const data = stats.value?.chart_groups.dynamic || []
  return data.map((item) => {
    const [facetKey, facetValue] = item.label.split(':')
    return { label: `${facetKey} / ${facetValue}`, value: item.value }
  })
})

function toggleFacet(key: string, value: string) {
  const current = selectedFacets.value[key] || []
  selectedFacets.value[key] = current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
}
</script>

<template>
  <section v-if="chatStore.currentSessionId" class="analysis-layout">
    <header class="panel-head">
      <div>
        <p class="eyebrow">Analysis Dashboard</p>
        <h2>商品结构化分析</h2>
      </div>
      <button class="ghost-button" type="button" @click="router.push('/chat')">返回对话页</button>
    </header>

    <div class="analysis-summary">
      <article class="summary-card">
        <span>候选商品</span>
        <strong>{{ stats?.total_products || 0 }}</strong>
      </article>
      <article class="summary-card">
        <span>平均价格</span>
        <strong>¥{{ stats?.average_price || 0 }}</strong>
      </article>
      <article class="summary-card">
        <span>当前品类</span>
        <strong>{{ facets?.category || 'general' }}</strong>
      </article>
    </div>

    <section class="filter-panel">
      <div class="filter-row">
        <label>
          <span>品牌</span>
          <select v-model="selectedBrand">
            <option value="">全部品牌</option>
            <option v-for="option in facets?.fixed[0]?.options || []" :key="option.value" :value="option.value">
              {{ option.value }}
            </option>
          </select>
        </label>
        <label>
          <span>平台</span>
          <select v-model="selectedPlatform">
            <option value="">全部平台</option>
            <option v-for="option in facets?.fixed[1]?.options || []" :key="option.value" :value="option.value">
              {{ option.value }}
            </option>
          </select>
        </label>
        <label>
          <span>最低价</span>
          <input v-model="priceMin" type="number" min="0" placeholder="0" />
        </label>
        <label>
          <span>最高价</span>
          <input v-model="priceMax" type="number" min="0" placeholder="不限" />
        </label>
      </div>

      <div class="facet-cloud">
        <div v-for="facet in facets?.dynamic || []" :key="facet.key" class="facet-group">
          <p>{{ facet.label }}</p>
          <div class="tag-row">
            <button
              v-for="option in facet.options"
              :key="option.value"
              class="pill-button"
              :class="{ active: (selectedFacets[facet.key] || []).includes(option.value) }"
              type="button"
              @click="toggleFacet(facet.key, option.value)"
            >
              {{ option.value }} ({{ option.count }})
            </button>
          </div>
        </div>
      </div>
    </section>

    <section class="chart-grid">
      <ChartCard title="品牌分布" type="bar" :items="stats?.chart_groups.brands || []" />
      <ChartCard title="平台占比" type="pie" :items="stats?.chart_groups.platforms || []" />
      <ChartCard title="价格对比" type="bar" :items="stats?.chart_groups.prices || []" />
      <ChartCard title="动态二级维度" type="bar" :items="dynamicCharts" />
    </section>

    <section class="product-section">
      <header class="section-head">
        <h3>商品卡片</h3>
        <span>{{ filteredProducts.length }} / {{ products.length }} 个结果</span>
      </header>
      <div class="product-grid">
        <button
          v-for="product in filteredProducts"
          :key="product.id"
          class="product-button"
          type="button"
          @click="selectedProductId = product.id"
        >
          <ProductCard :product="product" :active="product.id === selectedProductId" />
        </button>
      </div>
    </section>

    <aside v-if="selectedProduct" class="detail-drawer">
      <header class="section-head">
        <h3>详情面板</h3>
        <button class="ghost-button" type="button" @click="selectedProductId = null">关闭</button>
      </header>
      <img :src="selectedProduct.image_url" :alt="selectedProduct.title" class="detail-cover" />
      <h4>{{ selectedProduct.title }}</h4>
      <p class="muted">{{ selectedProduct.brand }} · {{ selectedProduct.platform }} · ¥{{ selectedProduct.price }}</p>
      <div class="facet-stack">
        <p v-for="[key, values] in Object.entries(selectedProduct.dynamic_facets)" :key="key" class="facet-line">
          <strong>{{ key }}</strong>
          <span>{{ values.join(' / ') }}</span>
        </p>
      </div>
      <ul class="detail-list">
        <li v-for="record in selectedProduct.source_records" :key="record.source_url">
          <strong>{{ record.source_name }}</strong>
          <span>{{ record.notes }}</span>
        </li>
      </ul>
    </aside>
  </section>

  <section v-else class="empty-state">
    <h2>还没有可分析的会话</h2>
    <p>先去对话页发送一条商品需求，系统会生成结构化结果和动态图表。</p>
    <button class="primary-button" type="button" @click="router.push('/chat')">去对话页</button>
  </section>
</template>
