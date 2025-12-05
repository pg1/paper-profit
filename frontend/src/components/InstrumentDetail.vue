<script setup>
import { ref, onMounted, computed } from 'vue'
import StockPriceGraph from './ui/StockPriceGraph.vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const instrumentData = ref(null)
const marketData = ref([])
const isLoading = ref(false)
const error = ref(null)
const symbol = ref('')
const selectedPeriod = ref('1m') // Default to 1 month

const timePeriods = [
  { value: '1d', label: '1D' },
  { value: '1w', label: '1W' },
  { value: '1m', label: '1M' },
  { value: '3m', label: '3M' },
  { value: '6m', label: '6M' },
  { value: 'ytd', label: 'YTD' },
  { value: '1y', label: '1Y' }
]

const emit = defineEmits(['navigate'])

const handleBack = () => {
  emit('navigate', 'portfolio', { accountName: props.navigationParams.accountName })
}

// Fetch instrument data
const fetchInstrumentData = async () => {
  try {
    const response = await fetch(`http://localhost:5000/api/instruments/get/${symbol.value}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch instrument data: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Instrument API Response:', data)
    instrumentData.value = data
  } catch (err) {
    console.error('Error fetching instrument data:', err)
    error.value = 'Failed to load instrument data. Please try again.'
  }
}

// Fetch market data for graph
const fetchMarketData = async () => {
  try {
    const response = await fetch(`http://localhost:5000/api/instruments/${symbol.value}/market-data?period=${selectedPeriod.value}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch market data: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Market Data API Response:', data)
    
    // Transform the data to match frontend expectations
    marketData.value = data.map(item => ({
      timestamp: item.date,
      open: item.open_price,
      high: item.high_price,
      low: item.low_price,
      close: item.close_price,
      volume: item.volume
    }))
  } catch (err) {
    console.error('Error fetching market data:', err)
    // Don't set error for market data as it's optional
  }
}

// Handle period change
const handlePeriodChange = (period) => {
  selectedPeriod.value = period
  fetchMarketData()
}

// Fetch all data
const fetchData = async () => {
  if (!symbol.value) return
  
  isLoading.value = true
  error.value = null
  
  try {
    // First load basic instrument data
    await fetchInstrumentData()
    
    // Then load market data for graph after basic info is loaded
    await fetchMarketData()
  } catch (err) {
    console.error('Error fetching instrument detail data:', err)
    error.value = 'Failed to load instrument data. Please try again.'
  } finally {
    isLoading.value = false
  }
}

// Format currency
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0.00'
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// Format percentage
const formatPercentage = (value) => {
  if (value === null || value === undefined) return '0.00%'
  return `${value.toFixed(2)}%`
}

// Format large numbers (market cap)
const formatLargeNumber = (value) => {
  if (value === null || value === undefined) return 'N/A'
  
  if (value >= 1e12) {
    return `$${(value / 1e12).toFixed(2)}T`
  } else if (value >= 1e9) {
    return `$${(value / 1e9).toFixed(2)}B`
  } else if (value >= 1e6) {
    return `$${(value / 1e6).toFixed(2)}M`
  } else {
    return `$${value.toLocaleString()}`
  }
}

// Calculate price change from 52-week range
const priceChangeFrom52WeekLow = computed(() => {
  if (!instrumentData.value || !instrumentData.value.current_price || !instrumentData.value.fifty_two_week_low) return 0
  const current = instrumentData.value.current_price
  const low = instrumentData.value.fifty_two_week_low
  return ((current - low) / low) * 100
})

// Calculate price change from 52-week high
const priceChangeFrom52WeekHigh = computed(() => {
  if (!instrumentData.value || !instrumentData.value.current_price || !instrumentData.value.fifty_two_week_high) return 0
  const current = instrumentData.value.current_price
  const high = instrumentData.value.fifty_two_week_high
  return ((current - high) / high) * 100
})

// Watch for navigation params to update symbol
onMounted(() => {
  if (props.navigationParams.symbol) {
    symbol.value = props.navigationParams.symbol
    fetchData()
  }
})
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>{{ symbol }}</h2>
        <p v-if="instrumentData">{{ instrumentData.name }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleBack">← Back to Portfolio</button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading instrument data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button class="btn btn-primary" @click="fetchData">Retry</button>
    </div>

    <!-- Instrument Data -->
    <div v-else-if="instrumentData" class="instrument-detail">
      <!-- Price and Basic Info -->
      <div class="price-section">
        <div class="current-price">
          <span class="price">{{ formatCurrency(instrumentData.current_price) }}</span>
          <span class="currency">{{ instrumentData.currency }}</span>
        </div>
        <div class="exchange-info">
          <span class="exchange">{{ instrumentData.exchange }}</span>
          <span class="sector">{{ instrumentData.sector }}</span>
          <span class="industry">{{ instrumentData.industry }}</span>
        </div>
      </div>

      <!-- Market Data Graph -->
      <div class="graph-section">
        <StockPriceGraph 
          :symbol="symbol"
          :period="selectedPeriod"
          :height="400"
          :showControls="true"
          @period-change="handlePeriodChange"
        />
      </div>

      <!-- Financial Metrics -->
      <div class="metrics-section">
        <h3 class="subsection-header">Financial Metrics</h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="metric-label">Market Cap</span>
            <span class="metric-value">{{ formatLargeNumber(instrumentData.market_cap) }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">P/E Ratio</span>
            <span class="metric-value">{{ instrumentData.pe_ratio ? instrumentData.pe_ratio.toFixed(2) : 'N/A' }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Dividend Yield</span>
            <span class="metric-value">{{ instrumentData.dividend_yield ? formatPercentage(instrumentData.dividend_yield) : 'N/A' }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Beta</span>
            <span class="metric-value">{{ instrumentData.beta ? instrumentData.beta.toFixed(3) : 'N/A' }}</span>
          </div>
        </div>
      </div>

      <!-- 52-Week Range -->
      <div class="range-section">
        <h3 class="subsection-header">52-Week Range</h3>
        <div class="range-container">
          <div class="range-labels">
            <span class="range-low">{{ formatCurrency(instrumentData.fifty_two_week_low) }}</span>
            <span class="range-high">{{ formatCurrency(instrumentData.fifty_two_week_high) }}</span>
          </div>
          <div class="range-bar">
            <div 
              class="range-progress"
              :style="{
                left: '0%',
                width: `${((instrumentData.current_price - instrumentData.fifty_two_week_low) / (instrumentData.fifty_two_week_high - instrumentData.fifty_two_week_low)) * 100}%`
              }"
            ></div>
            <div 
              class="current-price-marker"
              :style="{
                left: `${((instrumentData.current_price - instrumentData.fifty_two_week_low) / (instrumentData.fifty_two_week_high - instrumentData.fifty_two_week_low)) * 100}%`
              }"
              :title="`Current: ${formatCurrency(instrumentData.current_price)}`"
            ></div>
          </div>
          <div class="range-stats">
            <span class="range-stat">
              From Low: <span :class="{ positive: priceChangeFrom52WeekLow >= 0, negative: priceChangeFrom52WeekLow < 0 }">
                {{ formatPercentage(priceChangeFrom52WeekLow) }}
              </span>
            </span>
            <span class="range-stat">
              From High: <span :class="{ positive: priceChangeFrom52WeekHigh >= 0, negative: priceChangeFrom52WeekHigh < 0 }">
                {{ formatPercentage(priceChangeFrom52WeekHigh) }}
              </span>
            </span>
          </div>
        </div>
      </div>

      <!-- Additional Info -->
      <div class="additional-info">
        <h3 class="subsection-header">Additional Information</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Symbol</span>
            <span class="info-value">{{ instrumentData.symbol }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Name</span>
            <span class="info-value">{{ instrumentData.name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Exchange</span>
            <span class="info-value">{{ instrumentData.exchange }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Currency</span>
            <span class="info-value">{{ instrumentData.currency }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Sector</span>
            <span class="info-value">{{ instrumentData.sector }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Industry</span>
            <span class="info-value">{{ instrumentData.industry }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- No Data State -->
    <div v-else class="empty-state">
      <p class="empty-message">No instrument data available</p>
    </div>
  </section>
</template>

<style scoped>
.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.instrument-detail {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.price-section {
  background-color: #f9f9f9;
  padding: 2rem;
  border-radius: 8px;
  text-align: center;
  border: 1px solid #f0f0f0;
}

.current-price {
  margin-bottom: 1rem;
}

.price {
  font-size: 3rem;
  font-weight: 700;
  color: #000000;
  margin-right: 0.5rem;
}

.currency {
  font-size: 1.5rem;
  color: #000000;
  opacity: 0.8;
}

.exchange-info {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.exchange, .sector, .industry {
  background-color: #e9ecef;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  color: #000000;
  opacity: 0.8;
}

.subsection-header {
  font-size: 1.5rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #000000;
  padding-bottom: 0.5rem;
}

.graph-section {
  background-color: #ffffff;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
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

.simple-graph {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.graph-container {
  display: flex;
  align-items: flex-end;
  height: 200px;
  gap: 2px;
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #e9ecef;
}

.graph-bar {
  flex: 1;
  min-width: 4px;
  background-color: #28a745;
  border-radius: 2px 2px 0 0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.graph-bar:hover {
  opacity: 0.8;
}

.graph-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: #000000;
  opacity: 0.8;
}

.metrics-section {
  background-color: #ffffff;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.metric-card {
  background-color: #f9f9f9;
  padding: 1.5rem;
  border-radius: 4px;
  text-align: center;
  border: 1px solid #f0f0f0;
}

.metric-label {
  display: block;
  font-size: 0.9rem;
  color: #000000;
  opacity: 0.8;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 600;
  color: #000000;
}

.range-section {
  background-color: #ffffff;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.range-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: #000000;
  opacity: 0.8;
}

.range-bar {
  position: relative;
  height: 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.range-progress {
  position: absolute;
  height: 100%;
  background-color: #007bff;
  border-radius: 4px;
}

.current-price-marker {
  position: absolute;
  top: -4px;
  width: 16px;
  height: 16px;
  background-color: #dc3545;
  border-radius: 50%;
  border: 2px solid #ffffff;
  transform: translateX(-50%);
}

.range-stats {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.range-stat {
  color: #000000;
  opacity: 0.8;
}

.positive {
  color: #28a745;
}

.negative {
  color: #dc3545;
}

.additional-info {
  background-color: #ffffff;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-label {
  font-weight: 600;
  color: #000000;
}

.info-value {
  color: #000000;
  opacity: 0.8;
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

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .exchange-info {
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }
  
  .price {
    font-size: 2rem;
  }
  
  .currency {
    font-size: 1rem;
  }
}
</style>
