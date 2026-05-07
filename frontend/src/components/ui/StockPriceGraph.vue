<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'

const props = defineProps({
  symbol: {
    type: String,
    required: true
  },
  period: {
    type: String,
    default: '1m'
  },
  height: {
    type: Number,
    default: 300
  },
  showControls: {
    type: Boolean,
    default: true
  },
  marketData: {
    type: Array,
    default: null
  }
})

const emit = defineEmits(['period-change'])

const marketData = ref([])
const isLoading = ref(false)
const error = ref(null)
const selectedPeriod = ref(props.period)
const hoveredPoint = ref(null)
const containerWidth = ref(0)
const resizeObserver = ref(null)
const graphRef = ref(null)
const chartType = ref('line')

const timePeriods = [
  { value: '1d', label: '1D' },
  { value: '1w', label: '1W' },
  { value: '1m', label: '1M' },
  { value: '3m', label: '3M' },
  { value: '6m', label: '6M' },
  { value: 'ytd', label: 'YTD' },
  { value: '1y', label: '1Y' }
]

// Chart dimensions and calculations
const chartWidth = computed(() => Math.max(containerWidth.value, 400))
const chartHeight = computed(() => props.height)
const padding = computed(() => ({
  top: 20,
  right: 20,
  bottom: 40,
  left: 60
}))

// Chart area calculations
const chartArea = computed(() => ({
  width: chartWidth.value - padding.value.left - padding.value.right,
  height: chartHeight.value - padding.value.top - padding.value.bottom
}))

// Price range calculations
const priceRange = computed(() => {
  if (marketData.value.length === 0) return { min: 0, max: 100 }

  let minPrice, maxPrice
  if (chartType.value === 'candle') {
    minPrice = Math.min(...marketData.value.map(d => d.low_price))
    maxPrice = Math.max(...marketData.value.map(d => d.high_price))
  } else {
    const prices = marketData.value.map(d => d.close_price)
    minPrice = Math.min(...prices)
    maxPrice = Math.max(...prices)
  }

  const range = maxPrice - minPrice
  const pad = range * 0.1

  return { min: minPrice - pad, max: maxPrice + pad }
})

// Candle width based on available space
const candleWidth = computed(() => {
  if (marketData.value.length < 2) return 8
  return Math.max(2, (chartArea.value.width / marketData.value.length) * 0.7)
})

// Volume scale — maps volume to bar height within bottom 20% of chart area
const volumeScale = computed(() => {
  if (marketData.value.length === 0) return () => 0
  const maxVol = Math.max(...marketData.value.map(d => d.volume || 0))
  if (maxVol === 0) return () => 0
  const volAreaHeight = chartArea.value.height * 0.2
  return (volume) => ((volume || 0) / maxVol) * volAreaHeight
})

// Date range calculations
const dateRange = computed(() => {
  if (marketData.value.length === 0) return { min: 0, max: 1 }
  
  const dates = marketData.value.map(d => new Date(d.date).getTime())
  return {
    min: Math.min(...dates),
    max: Math.max(...dates)
  }
})

// Scale functions
const xScale = computed(() => {
  const { min, max } = dateRange.value
  const range = max - min || 1
  return (date) => {
    const dateValue = new Date(date).getTime()
    return ((dateValue - min) / range) * chartArea.value.width
  }
})

const yScale = computed(() => {
  const { min, max } = priceRange.value
  const range = max - min || 1
  return (price) => {
    return chartArea.value.height - ((price - min) / range) * chartArea.value.height
  }
})

// Generate line path for the chart
const linePath = computed(() => {
  if (marketData.value.length === 0) return ''

  const points = marketData.value.map((point, index) => {
    const x = xScale.value(point.date)
    const y = yScale.value(point.close_price)
    return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
  })

  return points.join(' ')
})

// Generate area path for the chart
const areaPath = computed(() => {
  if (marketData.value.length === 0) return ''

  const points = marketData.value.map((point, index) => {
    const x = xScale.value(point.date)
    const y = yScale.value(point.close_price)
    return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
  })

  // Close the area path
  const lastPoint = marketData.value[marketData.value.length - 1]
  const firstPoint = marketData.value[0]

  return points.join(' ') +
    ` L ${xScale.value(lastPoint.date)} ${chartArea.value.height}` +
    ` L ${xScale.value(firstPoint.date)} ${chartArea.value.height}` +
    ' Z'
})

// Fetch market data
const fetchMarketData = async () => {
  if (!props.symbol) return
  
  // If marketData prop is provided, use it directly instead of fetching
  if (props.marketData && props.marketData.length > 0) {
    marketData.value = [...props.marketData].sort((a, b) => new Date(a.date) - new Date(b.date))
    return
  }
  
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch(`http://localhost:5000/api/instruments/${props.symbol}/market-data?period=${selectedPeriod.value}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch market data: ${response.status}`)
    }
    
    const data = await response.json()
    // Sort data by date to ensure chronological order (oldest to newest)
    marketData.value = data.sort((a, b) => new Date(a.date) - new Date(b.date))
    
  } catch (err) {
    console.error('Error fetching market data:', err)
    error.value = 'Failed to load market data. Please try again.'
  } finally {
    isLoading.value = false
  }
}

// Handle period change
const handlePeriodChange = (period) => {
  selectedPeriod.value = period
  emit('period-change', period)
  fetchMarketData()
}

// Handle mouse move on chart
const handleMouseMove = (event) => {
  if (marketData.value.length === 0) return

  const svg = event.currentTarget
  const rect = svg.getBoundingClientRect()
  const mouseX = event.clientX - rect.left - padding.value.left

  // Find the closest data point by actual scaled x position
  let closestIndex = 0
  let closestDist = Infinity

  marketData.value.forEach((point, index) => {
    const dist = Math.abs(xScale.value(point.date) - mouseX)
    if (dist < closestDist) {
      closestDist = dist
      closestIndex = index
    }
  })

  hoveredPoint.value = {
    ...marketData.value[closestIndex],
    index: closestIndex
  }
}

// Handle mouse leave
const handleMouseLeave = () => {
  hoveredPoint.value = null
}

// Format currency
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0.00'
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// Format date
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: selectedPeriod.value === '1y' ? 'numeric' : undefined
  })
}

// Watch for symbol changes
watch(() => props.symbol, () => {
  fetchMarketData()
})

// Watch for period prop changes
watch(() => props.period, (newPeriod) => {
  selectedPeriod.value = newPeriod
  fetchMarketData()
})

// Watch for marketData prop changes
watch(() => props.marketData, (newData) => {
  if (newData && newData.length > 0) {
    marketData.value = [...newData].sort((a, b) => new Date(a.date) - new Date(b.date))
  }
}, { deep: true })

// Setup resize observer
const setupResizeObserver = () => {
  if (!graphRef.value) return
  containerWidth.value = graphRef.value.clientWidth
  resizeObserver.value = new ResizeObserver((entries) => {
    for (const entry of entries) {
      containerWidth.value = entry.contentRect.width
    }
  })
  resizeObserver.value.observe(graphRef.value)
}

// Initial data fetch and setup
onMounted(() => {
  fetchMarketData()
  setupResizeObserver()
})

// Cleanup resize observer
onUnmounted(() => {
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
  }
})
</script>

<template>
  <div ref="graphRef" class="stock-price-graph">
    <!-- Graph Header -->
    <div v-if="showControls" class="graph-header">
      <h3 class="graph-title">Price Chart - {{ symbol }}</h3>
      <div class="header-controls">
        <div class="chart-type-toggle">
          <button
            class="chart-type-btn"
            :class="{ active: chartType === 'line' }"
            @click="chartType = 'line'"
            title="Line chart"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <polyline points="1,11 4,6 7,8 10,3 13,5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <button
            class="chart-type-btn"
            :class="{ active: chartType === 'candle' }"
            @click="chartType = 'candle'"
            title="Candlestick chart"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <line x1="3" y1="1" x2="3" y2="13" stroke="currentColor" stroke-width="1"/>
              <rect x="1.5" y="4" width="3" height="5" fill="currentColor"/>
              <line x1="11" y1="1" x2="11" y2="13" stroke="currentColor" stroke-width="1"/>
              <rect x="9.5" y="3" width="3" height="6" fill="none" stroke="currentColor" stroke-width="1"/>
            </svg>
          </button>
        </div>
        <div class="period-selector">
          <button
            v-for="period in timePeriods"
            :key="period.value"
            class="period-btn"
            :class="{ active: selectedPeriod === period.value }"
            @click="handlePeriodChange(period.value)"
          >
            {{ period.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading market data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button class="btn btn-primary" @click="fetchMarketData">Retry</button>
    </div>

    <!-- Chart Container -->
    <div v-else-if="marketData.length > 0" class="chart-container">
      <svg
        width="100%"
        :height="chartHeight"
        class="chart-svg"
        @mousemove="handleMouseMove"
        @mouseleave="handleMouseLeave"
      >
        <!-- Grid Lines -->
        <defs>
          <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e9ecef" stroke-width="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        <!-- Chart Area -->
        <g :transform="`translate(${padding.left}, ${padding.top})`">

          <!-- Line chart -->
          <template v-if="chartType === 'line'">
            <path :d="areaPath" class="area-fill" fill="url(#areaGradient)" />
            <path :d="linePath" class="price-line" fill="none" stroke-width="2" />
            <circle
              v-if="hoveredPoint"
              :cx="xScale(hoveredPoint.date)"
              :cy="yScale(hoveredPoint.close_price)"
              r="4"
              class="hover-point"
            />
          </template>

          <!-- Candlestick chart -->
          <template v-if="chartType === 'candle'">
            <!-- Volume bars (bottom 20% of chart, drawn first so candles sit on top) -->
            <rect
              v-for="point in marketData"
              :key="`vol-${point.date}`"
              :x="xScale(point.date) - candleWidth / 2"
              :y="chartArea.height - volumeScale(point.volume)"
              :width="candleWidth"
              :height="volumeScale(point.volume)"
              :fill="point.close_price >= point.open_price ? '#26a69a' : '#ef5350'"
              opacity="0.25"
            />
            <!-- Candles -->
            <g v-for="point in marketData" :key="point.date">
              <line
                :x1="xScale(point.date)"
                :x2="xScale(point.date)"
                :y1="yScale(point.high_price)"
                :y2="yScale(point.low_price)"
                :stroke="point.close_price >= point.open_price ? '#26a69a' : '#ef5350'"
                stroke-width="1"
              />
              <rect
                :x="xScale(point.date) - candleWidth / 2"
                :y="yScale(Math.max(point.open_price, point.close_price))"
                :width="candleWidth"
                :height="Math.max(1, Math.abs(yScale(point.open_price) - yScale(point.close_price)))"
                :fill="point.close_price >= point.open_price ? '#26a69a' : '#ef5350'"
              />
            </g>
          </template>

          <!-- Hover vertical line -->
          <line
            v-if="hoveredPoint"
            :x1="xScale(hoveredPoint.date)"
            :x2="xScale(hoveredPoint.date)"
            y1="0"
            :y2="chartArea.height"
            class="hover-line"
          />

          <!-- Hover horizontal line to price axis -->
          <line
            v-if="hoveredPoint"
            x1="0"
            :x2="xScale(hoveredPoint.date)"
            :y1="yScale(hoveredPoint.close_price)"
            :y2="yScale(hoveredPoint.close_price)"
            class="hover-line"
          />
        </g>

        <!-- Y-axis labels -->
        <g class="y-axis">
          <text
            v-for="(_, index) in 5"
            :key="index"
            x="10"
            :y="padding.top + (index * chartArea.height / 4)"
            class="axis-label"
            text-anchor="start"
            dominant-baseline="middle"
          >
            {{ formatCurrency(priceRange.max - (index * (priceRange.max - priceRange.min) / 4)) }}
          </text>
        </g>

        <!-- X-axis labels -->
        <g class="x-axis">
          <text
            v-for="(point, index) in marketData.filter((_, i) => i % Math.ceil(marketData.length / 6) === 0)"
            :key="index"
            :x="xScale(point.date) + padding.left"
            :y="chartHeight - 10"
            class="axis-label"
            text-anchor="middle"
          >
            {{ formatDate(point.date) }}
          </text>
        </g>
      </svg>

      <!-- Tooltip -->
      <div v-if="hoveredPoint" class="tooltip" :style="{
        left: `${xScale(hoveredPoint.date) + padding.left}px`,
        top: `${yScale(hoveredPoint.close_price) + padding.top - 60}px`
      }">
        <div class="tooltip-date">{{ formatDate(hoveredPoint.date) }}</div>
        <template v-if="chartType === 'candle'">
          <div class="tooltip-ohlc">O: {{ formatCurrency(hoveredPoint.open_price) }}</div>
          <div class="tooltip-ohlc">H: {{ formatCurrency(hoveredPoint.high_price) }}</div>
          <div class="tooltip-ohlc">L: {{ formatCurrency(hoveredPoint.low_price) }}</div>
          <div class="tooltip-ohlc">C: {{ formatCurrency(hoveredPoint.close_price) }}</div>
        </template>
        <div v-else class="tooltip-price">{{ formatCurrency(hoveredPoint.close_price) }}</div>
        <div class="tooltip-volume">Vol: {{ hoveredPoint.volume?.toLocaleString() }}</div>
      </div>

      <!-- Current Price Display -->
      <div class="current-price-display" v-if="marketData.length > 0">
        <div class="price-change">
          <span class="current-price">{{ formatCurrency(marketData[marketData.length - 1].close_price) }}</span>
          <span class="price-difference" :class="{
            positive: marketData[marketData.length - 1].close_price >= marketData[0].close_price,
            negative: marketData[marketData.length - 1].close_price < marketData[0].close_price
          }">
            {{ formatCurrency(Math.abs(marketData[marketData.length - 1].close_price - marketData[0].close_price)) }}
            ({{ ((marketData[marketData.length - 1].close_price - marketData[0].close_price) / marketData[0].close_price * 100).toFixed(2) }}%)
          </span>
        </div>
      </div>
    </div>

    <!-- No Data State -->
    <div v-else class="empty-state">
      <p class="empty-message">No market data available</p>
    </div>

    <!-- Gradient definitions -->
    <svg width="0" height="0">
      <defs>
        <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#007bff" stop-opacity="0.3" />
          <stop offset="100%" stop-color="#007bff" stop-opacity="0.1" />
        </linearGradient>
      </defs>
    </svg>
  </div>
</template>

<style scoped>
.stock-price-graph {
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  padding: 1.5rem;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.graph-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #000000;
  margin: 0;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.chart-type-toggle {
  display: flex;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.chart-type-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background-color: #ffffff;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.15s ease;
  padding: 0;
}

.chart-type-btn:not(:last-child) {
  border-right: 1px solid #e9ecef;
}

.chart-type-btn:hover {
  background-color: #f8f9fa;
  color: #007bff;
}

.chart-type-btn.active {
  background-color: #007bff;
  color: #ffffff;
}

.period-selector {
  display: flex;
  gap: 0.5rem;
}

.period-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #e9ecef;
  background-color: #ffffff;
  color: #000000;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.period-btn:hover {
  background-color: #f8f9fa;
  border-color: #007bff;
}

.period-btn.active {
  background-color: #007bff;
  color: #ffffff;
  border-color: #007bff;
}

.chart-container {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chart-svg {
  display: block;
  width: 100%;
  border-radius: 4px;
  background-color: #ffffff;
}

.area-fill {
  opacity: 0.6;
}

.price-line {
  stroke: #007bff;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.hover-line {
  stroke: #6c757d;
  stroke-width: 1;
  stroke-dasharray: 4, 4;
  pointer-events: none;
}

.hover-point {
  fill: #007bff;
  stroke: #ffffff;
  stroke-width: 2;
  pointer-events: none;
}

.axis-label {
  font-size: 0.75rem;
  fill: #6c757d;
  font-family: Arial, sans-serif;
}

.tooltip {
  position: absolute;
  background-color: rgba(0, 0, 0, 0.8);
  color: #ffffff;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.875rem;
  pointer-events: none;
  transform: translateX(-50%);
  z-index: 10;
  min-width: 120px;
}

.tooltip-date {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.tooltip-price {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.tooltip-ohlc {
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
  margin-bottom: 0.1rem;
}

.tooltip-volume {
  opacity: 0.8;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.current-price-display {
  text-align: center;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.current-price {
  font-size: 1.5rem;
  font-weight: 600;
  color: #000000;
  margin-right: 0.5rem;
}

.price-difference {
  font-size: 1rem;
  font-weight: 500;
}

.price-difference.positive {
  color: #28a745;
}

.price-difference.negative {
  color: #dc3545;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  color: #000000;
  opacity: 0.8;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #000000;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  padding: 2rem;
}

.error-message {
  color: #e74c3c;
  margin-bottom: 1rem;
  font-size: 1rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
}

.empty-message {
  color: #000000;
  opacity: 0.8;
  font-size: 1.1rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: #007bff;
  color: #ffffff;
}

.btn-primary:hover {
  background-color: #0056b3;
}
</style>
