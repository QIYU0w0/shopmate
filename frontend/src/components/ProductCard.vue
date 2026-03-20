<script setup lang="ts">
import { computed } from 'vue'

import type { Product } from '../api/client'

const props = defineProps<{
  product: Product
  active?: boolean
}>()

const facetEntries = computed(() => Object.entries(props.product.dynamic_facets).slice(0, 3))
</script>

<template>
  <article class="product-card" :class="{ active }">
    <img :src="product.image_url" :alt="product.title" class="product-cover" />
    <div class="product-meta">
      <div class="product-row">
        <span class="pill subtle">{{ product.platform }}</span>
        <span class="score-pill">Score {{ Math.round(product.score) }}</span>
      </div>
      <h3>{{ product.title }}</h3>
      <p class="muted">{{ product.brand }} · ¥{{ product.price }}</p>
      <div class="tag-row">
        <span v-for="keyword in product.matched_keywords.slice(0, 4)" :key="keyword" class="pill">
          {{ keyword }}
        </span>
      </div>
      <div class="facet-stack">
        <p v-for="[facetKey, values] in facetEntries" :key="facetKey" class="facet-line">
          <strong>{{ facetKey }}</strong>
          <span>{{ values.join(' / ') }}</span>
        </p>
      </div>
      <ul class="highlight-list">
        <li v-for="item in product.highlights.slice(0, 3)" :key="item">{{ item }}</li>
      </ul>
    </div>
  </article>
</template>
