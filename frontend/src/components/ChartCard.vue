<script setup lang="ts">
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  title: string
  type: 'bar' | 'pie'
  items: Array<{ label: string; value: number }>
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!containerRef.value) return
  chart ??= echarts.init(containerRef.value)
  const labels = props.items.map((item) => item.label)
  const values = props.items.map((item) => item.value)
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: props.type === 'pie' ? 'item' : 'axis' },
    grid: { top: 18, right: 18, bottom: 30, left: 38 },
    xAxis:
      props.type === 'bar'
        ? {
            type: 'category',
            data: labels,
            axisLabel: { color: '#516072', rotate: labels.length > 4 ? 20 : 0 }
          }
        : undefined,
    yAxis:
      props.type === 'bar'
        ? {
            type: 'value',
            axisLabel: { color: '#516072' },
            splitLine: { lineStyle: { color: 'rgba(89, 112, 141, 0.16)' } }
          }
        : undefined,
    series:
      props.type === 'pie'
        ? [
            {
              type: 'pie',
              radius: ['40%', '72%'],
              data: props.items.map((item) => ({ name: item.label, value: item.value })),
              label: { color: '#314255' }
            }
          ]
        : [
            {
              type: 'bar',
              data: values,
              itemStyle: { color: '#ff7a59', borderRadius: [10, 10, 0, 0] }
            }
          ]
  })
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

watch(() => props.items, renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chart?.dispose()
})
</script>

<template>
  <section class="chart-card">
    <header class="section-head">
      <h3>{{ title }}</h3>
    </header>
    <div ref="containerRef" class="chart-container"></div>
  </section>
</template>
