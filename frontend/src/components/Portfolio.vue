<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import StockPriceGraph from './ui/StockPriceGraph.vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const performanceData = ref(null)
const holdingsData = ref([])
const ordersData = ref([])
const tradingSignalsData = ref([])
const performanceHistoryData = ref([])
const isLoading = ref(false)
const error = ref(null)
const accountName = ref('test') 
const isAccountActive = ref(null) // Account active status
const strategyName = ref('') // Strategy name
const activeTab = ref('holdings') // Tab state: 'holdings', 'orders', 'signals', 'performance'
const performanceChartType = ref('equity') // 'equity' or 'pnl'

// Signal filter state
const signalFilterType = ref('')
const signalFilterSymbol = ref('')

// Order filter state
const orderFilterSide = ref('')
const orderFilterSymbol = ref('')

const emit = defineEmits(['navigate'])

const handleAddAsset = () => {
  emit('navigate', 'trade', { account_id: accountName.value })
}

const handleSymbolClick = (symbol) => {
  emit('navigate', 'instrument-detail', { symbol: symbol, accountName: accountName.value })
}

// Toggle account active status
const toggleAccountStatus = async () => {
  try {
    const newStatus = isAccountActive.value
    // Send 1 for active (true), 0 for inactive (false) to match database expectations
    const isActiveValue = newStatus ? 1 : 0
    const response = await fetch(`http://localhost:5000/api/accounts/${accountName.value}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActiveValue })
    })
    
    if (!response.ok) {
      throw new Error(`Failed to update account status: ${response.status}`)
    }
    
    isAccountActive.value = newStatus
  } catch (err) {
    console.error('Error updating account status:', err)
  }
}

// Fetch performance data
const fetchPerformance = async () => {
  try {
    const response = await fetch(`http://localhost:5000/api/accounts/${accountName.value}/performance`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch performance: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Performance API Response:', data) // Debug log
    performanceData.value = data
  } catch (err) {
    console.error('Error fetching performance:', err)
    error.value = 'Failed to load performance data. Please try again.'
  }
}

// Fetch holdings data
const fetchHoldings = async () => {
  try {
    const response = await fetch(`http://localhost:5000/api/accounts/${accountName.value}/portfolio`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch holdings: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Portfolio API Response:', data) // Debug log
    
    // Transform the holdings data from object to array format
    if (data.holdings) {
      holdingsData.value = Object.entries(data.holdings).map(([symbol, holding]) => {
        // Calculate percentage gain/loss
        const gainLossPercentage = holding.average_entry_price > 0 
          ? ((holding.price - holding.average_entry_price) / holding.average_entry_price) * 100 
          : 0
        
        return {
          symbol,
          name: holding.company_name,
          quantity: holding.shares,
          current_price: holding.price,
          current_value: holding.value,
          average_entry_price: holding.average_entry_price,
          gain_loss: holding.unrealized_pnl || 0, // Use unrealized_pnl from API
          gain_loss_percentage: gainLossPercentage
        }
      })
    } else {
      holdingsData.value = []
    }
  } catch (err) {
    console.error('Error fetching holdings:', err)
    error.value = 'Failed to load portfolio holdings. Please try again.'
  }
}

// Fetch orders for the account with optional filters
const fetchOrders = async () => {
  try {
    let url = `http://localhost:5000/api/accounts/${accountName.value}/orders?limit=100`
    if (orderFilterSide.value) {
      url += `&side=${orderFilterSide.value}`
    }
    if (orderFilterSymbol.value) {
      url += `&symbol=${orderFilterSymbol.value.toUpperCase()}`
    }
    
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch orders: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Orders API Response:', data) // Debug log
    ordersData.value = data
  } catch (err) {
    console.error('Error fetching orders:', err)
  }
}

// Fetch trading signals for account's strategy
const fetchTradingSignals = async () => {
  try {
    // First, get the account to get its strategy_id
    const accountResponse = await fetch(`http://localhost:5000/api/accounts/${accountName.value}`)
    
    if (!accountResponse.ok) {
      throw new Error(`Failed to fetch account: ${accountResponse.status}`)
    }
    
    const accountData = await accountResponse.json()
    console.log('Account API Response:', accountData) // Debug log
    
    // Set account active status based on is_active field (1 = true, 0 = false)
    if (accountData.is_active !== undefined) {
      // Handle both boolean true/false and numeric 1/0 values
      isAccountActive.value = Boolean(accountData.is_active)
    }
    // Set strategy name from account data
    if (accountData.strategy_name) {
      strategyName.value = accountData.strategy_name
    }
    console.log(isAccountActive.value)
    const strategyId = accountData.strategy_id
    
    // Build URL with strategy_id and filter params if available
    // Use a higher limit (100) so filtering has more data to work with
    let url = `http://localhost:5000/api/trading-signals?limit=100`
    if (strategyId) {
      url += `&strategy_id=${strategyId}`
    }
    if (signalFilterType.value) {
      url += `&signal_type=${signalFilterType.value}`
    }
    if (signalFilterSymbol.value) {
      url += `&symbol=${signalFilterSymbol.value.toUpperCase()}`
    }
    
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch trading signals: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Trading Signals API Response:', data) // Debug log
    tradingSignalsData.value = data
  } catch (err) {
    console.error('Error fetching trading signals:', err)
    // Don't set error for trading signals - it's optional
  }
}

// Fetch performance history (equity curve and daily P&L)
const fetchPerformanceHistory = async () => {
  try {
    const response = await fetch(`http://localhost:5000/api/accounts/${accountName.value}/performance/history?limit=100`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch performance history: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Performance History API Response:', data) // Debug log
    performanceHistoryData.value = data
  } catch (err) {
    console.error('Error fetching performance history:', err)
  }
}

// Computed property for equity curve data mapped to StockPriceGraph format
const equityCurveData = computed(() => {
  return performanceHistoryData.value.map(item => ({
    date: item.date,
    close_price: item.total_equity,
    open_price: item.total_equity,
    high_price: item.total_equity,
    low_price: item.total_equity,
    volume: 0
  }))
})

// Computed property for daily P&L data mapped to StockPriceGraph format
const dailyPnlData = computed(() => {
  return performanceHistoryData.value.map(item => ({
    date: item.date,
    close_price: item.daily_pnl,
    open_price: item.daily_pnl,
    high_price: item.daily_pnl,
    low_price: item.daily_pnl,
    volume: 0
  }))
})

// Fetch all data
const fetchData = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    await Promise.all([fetchPerformance(), fetchHoldings(), fetchTradingSignals(), fetchOrders()])
  } catch (err) {
    console.error('Error fetching portfolio data:', err)
    error.value = 'Failed to load portfolio data. Please try again.'
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

// Format date
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Calculate total portfolio value
const totalPortfolioValue = computed(() => {
  if (!holdingsData.value.length) return 0
  return holdingsData.value.reduce((total, holding) => {
    return total + (holding.current_value || 0)
  }, 0)
})

// Calculate cash balance (from performance data)
const cashBalance = computed(() => {
  if (!performanceData.value) return 0
  return performanceData.value.cash_balance || 0
})

// Calculate total equity (cash + portfolio value)
const totalEquity = computed(() => {
  return cashBalance.value + totalPortfolioValue.value
})

// Calculate total gain/loss
const totalGainLoss = computed(() => {
  if (!performanceData.value) return 0
  return performanceData.value.total_pnl || 0
})

// Calculate total gain/loss percentage
const totalGainLossPercentage = computed(() => {
  if (!performanceData.value) return 0
  return performanceData.value.total_return_percentage || 0
})

// Get daily gain/loss value
const dailyGainLoss = computed(() => {
  if (!performanceData.value) return 0
  // For now, use total gain/loss since daily data isn't available
  return performanceData.value.total_pnl || 0
})

// Get daily gain/loss percentage
const dailyGainLossPercentage = computed(() => {
  if (!performanceData.value) return 0
  // For now, use total gain/loss percentage since daily data isn't available
  return performanceData.value.daily_return_percentage || 0
})

// Get Sharpe ratio
const sharpeRatio = computed(() => {
  if (!performanceData.value) return 0
  return performanceData.value.sharpe_ratio || 0
})

// Get max drawdown
const maxDrawdown = computed(() => {
  if (!performanceData.value) return 0
  return performanceData.value.max_drawdown || 0
})

// Format Sharpe ratio (2 decimal places)
const formatSharpeRatio = (value) => {
  if (value === null || value === undefined) return '0.00'
  return value.toFixed(2)
}

// Format max drawdown as percentage
const formatMaxDrawdown = (value) => {
  if (value === null || value === undefined) return '0.00%'
  // Max drawdown is stored as a decimal (e.g., 0.15 = 15%), display as percentage
  return `${(value * 100).toFixed(2)}%`
}

// Filtered trading signals based on signal type and symbol

const filteredSignals = computed(() => {
  let signals = tradingSignalsData.value
  
  // Filter by signal type
  if (signalFilterType.value) {
    signals = signals.filter(s => s.signal_type === signalFilterType.value)
  }
  
  // Filter by symbol (case-insensitive partial match)
  if (signalFilterSymbol.value) {
    const searchSymbol = signalFilterSymbol.value.toUpperCase()
    signals = signals.filter(s => s.symbol && s.symbol.toUpperCase().includes(searchSymbol))
  }
  
  return signals
})

// Watch for navigation params to update account name
watch(() => props.navigationParams, (newParams) => {
  console.log('Portfolio navigation params:', newParams) // Debug log
  if (newParams.accountName) {
    accountName.value = newParams.accountName
    console.log('Portfolio account name updated to:', accountName.value) // Debug log
    // Refetch data when account name changes
    fetchData()
  }
}, { immediate: true })

// Refetch trading signals when filters change
watch([signalFilterType, signalFilterSymbol], () => {
  if (activeTab.value === 'signals') {
    fetchTradingSignals()
  }
})

// Refetch orders when filters change
watch([orderFilterSide, orderFilterSymbol], () => {
  if (activeTab.value === 'orders') {
    fetchOrders()
  }
})

onMounted(() => {
  fetchData()
})
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>Portfolio - {{ accountName }}</h2>
        <p>View your investment performance and holdings</p>
      </div>
      <div class="header-actions">
        <div class="strategy-name-display" v-if="strategyName">
          <span class="strategy-label">Strategy:</span>
          <span class="strategy-value">{{ strategyName }}</span>
        </div>
        <div class="account-status-toggle">
          <label for="account-active-toggle">Bot active:</label>
          <input
            id="account-active-toggle"
            type="checkbox"
            v-model="isAccountActive"
            @change="toggleAccountStatus"
            class="status-checkbox"
          >
        </div>
        <button class="btn-primary" @click="handleAddAsset">Add Asset</button>
      </div>
    </div>

    <!-- Portfolio Summary -->
    <div class="portfolio-summary">
      <div class="summary-cards">
        <div class="summary-card">
          <span class="summary-label">Total Equity</span>
          <span class="summary-value">{{ formatCurrency(totalEquity) }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Cash Balance</span>
          <span class="summary-value">{{ formatCurrency(cashBalance) }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Total Portfolio Value</span>
          <span class="summary-value">{{ formatCurrency(totalPortfolioValue) }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Total Gain/Loss</span>
          <span class="summary-value" :class="{ positive: totalGainLoss >= 0, negative: totalGainLoss < 0 }">
            {{ formatCurrency(totalGainLoss) }}
            <span class="percentage-badge" :class="{ positive: totalGainLossPercentage >= 0, negative: totalGainLossPercentage < 0 }">
              {{ formatPercentage(totalGainLossPercentage) }}
            </span>
          </span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Sharpe Ratio</span>
          <span class="summary-value" :class="{ positive: sharpeRatio >= 1, negative: sharpeRatio < 1 }">
            {{ formatSharpeRatio(sharpeRatio) }}
          </span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Max Drawdown</span>
          <span class="summary-value negative">
            {{ formatMaxDrawdown(maxDrawdown) }}
          </span>
        </div>
      </div>

    </div>


    <!-- Tabs Navigation -->
    <div class="tabs">
      <button 
        :class="['tab', { active: activeTab === 'holdings' }]" 
        @click="activeTab = 'holdings'"
      >
        Holdings
      </button>
      <button 
        :class="['tab', { active: activeTab === 'orders' }]" 
        @click="activeTab = 'orders'"
      >
        Orders
      </button>
      <button 
        :class="['tab', { active: activeTab === 'signals' }]" 
        @click="activeTab = 'signals'"
      >
        Signals
      </button>
      <button 
        :class="['tab', { active: activeTab === 'performance' }]" 
        @click="activeTab = 'performance'; fetchPerformanceHistory()"
      >
        Performance
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <!-- Holdings Tab -->
      <div v-if="activeTab === 'holdings'" class="tab-pane">
        <h3 class="subsection-header">Stock Holdings</h3>
        
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading holdings...</p>
        </div>
        
        <div v-else-if="error" class="error-state">
          <p class="error-message">{{ error }}</p>
          <button class="btn btn-primary" @click="fetchData">Retry</button>
        </div>
        
        <div v-else-if="holdingsData.length === 0" class="empty-state">
          <p class="empty-message">No holdings found in your portfolio</p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Quantity</th>
                <th>Avg Entry Price</th>
                <th>Current Price</th>
                <th>Current Value</th>
                <th>Gain/Loss</th>
                <th>% Gain/Loss</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="holding in holdingsData" 
                :key="holding.symbol" 
                class="clickable-row"
              >
                <td 
                  class="symbol-cell clickable" 
                  @click="handleSymbolClick(holding.symbol || holding.ticker)"
                >
                  {{ holding.symbol || holding.ticker || 'N/A' }}
                </td>
                <td class="name-cell">{{ holding.name || holding.company_name || holding.description || 'N/A' }}</td>
                <td class="quantity-cell">{{ holding.quantity || holding.shares || holding.qty || 0 }}</td>
                <td class="price-cell">{{ formatCurrency(holding.average_entry_price) }}</td>
                <td class="price-cell">{{ formatCurrency(holding.current_price || holding.price || holding.last_price) }}</td>
                <td class="value-cell">{{ formatCurrency(holding.current_value || holding.value || holding.market_value) }}</td>
                <td class="gain-loss-cell">
                  <span 
                    :class="{ positive: holding.gain_loss >= 0, negative: holding.gain_loss < 0 }"
                  >
                    {{ formatCurrency(holding.gain_loss) }}
                  </span>
                </td>
                <td class="gain-loss-percentage-cell">
                  <span 
                    :class="{ positive: holding.gain_loss_percentage >= 0, negative: holding.gain_loss_percentage < 0 }"
                  >
                    {{ formatPercentage(holding.gain_loss_percentage) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Orders Tab -->
      <div v-if="activeTab === 'orders'" class="tab-pane">
        <h3 class="subsection-header">Recent Orders</h3>
        
        <!-- Order Filters -->
        <div class="signal-filters">
          <div class="filter-group">
            <label for="order-side-filter">Side:</label>
            <select id="order-side-filter" v-model="orderFilterSide" class="filter-select">
              <option value="">All</option>
              <option value="BUY">Buy</option>
              <option value="SELL">Sell</option>
            </select>
          </div>
          <div class="filter-group">
            <label for="order-symbol-filter">Ticker:</label>
            <input
              id="order-symbol-filter"
              type="text"
              v-model="orderFilterSymbol"
              placeholder="e.g. AAPL"
              class="filter-input"
            />
          </div>
          <div class="filter-info" v-if="ordersData.length > 0">
            Showing {{ ordersData.length }} orders
          </div>
        </div>
        
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading orders...</p>
        </div>
        
        <div v-else-if="error" class="error-state">
          <p class="error-message">{{ error }}</p>
          <button class="btn btn-primary" @click="fetchData">Retry</button>
        </div>
        
        <div v-else-if="ordersData.length === 0" class="empty-state">
          <p class="empty-message">No recent orders found</p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Type</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Status</th>
                <th>Submitted</th>
                <th>Filled</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="order in ordersData" 
                :key="order.id" 
                class="clickable-row"
              >
                <td 
                  class="symbol-cell clickable" 
                  @click="handleSymbolClick(order.symbol)"
                >
                  {{ order.symbol || 'N/A' }}
                </td>
                <td class="side-cell">
                  <span 
                    :class="{ buy: order.side === 'BUY', sell: order.side === 'SELL' }"
                  >
                    {{ order.side || 'N/A' }}
                  </span>
                </td>
                <td class="type-cell">{{ order.order_type || 'N/A' }}</td>
                <td class="quantity-cell">{{ order.quantity || 0 }}</td>
                <td class="price-cell">{{ formatCurrency(order.price) }}</td>
                <td class="status-cell">
                  <span 
                    :class="{ 
                      'status-pending': order.status === 'PENDING',
                      'status-filled': order.status === 'FILLED',
                      'status-cancelled': order.status === 'CANCELLED'
                    }"
                  >
                    {{ order.status || 'N/A' }}
                  </span>
                </td>
                <td class="date-cell">{{ formatDate(order.submitted_at) }}</td>
                <td class="date-cell">{{ formatDate(order.filled_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Signals Tab -->
      <div v-if="activeTab === 'signals'" class="tab-pane">
        <h3 class="subsection-header">Trading Bot Signals</h3>
        
        <!-- Signal Filters -->
        <div class="signal-filters">
          <div class="filter-group">
            <label for="signal-type-filter">Signal Type:</label>
            <select id="signal-type-filter" v-model="signalFilterType" class="filter-select">
              <option value="">All</option>
              <option value="BUY">Buy</option>
              <option value="SELL">Sell</option>
              <option value="HOLD">Hold</option>
            </select>
          </div>
          <div class="filter-group">
            <label for="signal-symbol-filter">Ticker:</label>
            <input
              id="signal-symbol-filter"
              type="text"
              v-model="signalFilterSymbol"
              placeholder="e.g. AAPL"
              class="filter-input"
            />
          </div>
          <div class="filter-info" v-if="tradingSignalsData.length > 0">
            Showing {{ filteredSignals.length }} of {{ tradingSignalsData.length }} signals
          </div>
        </div>
        
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading trading signals...</p>
        </div>
        
        <div v-else-if="tradingSignalsData.length === 0" class="empty-state">
          <p class="empty-message">No trading signals found</p>
        </div>
        
        <div v-else-if="filteredSignals.length === 0" class="empty-state">
          <p class="empty-message">No signals match the current filters</p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Signal</th>
                <th>Strategy</th>
                <th>Price</th>
                <th>Strength</th>
                <th>Confidence</th>
                <th>Time</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="signal in filteredSignals" 
                :key="signal.id" 
                class="clickable-row"
              >
                <td 
                  class="symbol-cell clickable" 
                  @click="handleSymbolClick(signal.symbol)"
                >
                  {{ signal.symbol || 'N/A' }}
                </td>
                <td class="signal-cell">
                  <span 
                    :class="{ 
                      'signal-buy': signal.signal_type === 'BUY',
                      'signal-sell': signal.signal_type === 'SELL',
                      'signal-hold': signal.signal_type === 'HOLD'
                    }"
                  >
                    {{ signal.signal_type || 'N/A' }}
                  </span>
                </td>
                <td class="strategy-cell">{{ signal.strategy || 'N/A' }}</td>
                <td class="price-cell">{{ formatCurrency(signal.price) }}</td>
                <td class="strength-cell">
                  <span 
                    :class="{ 
                      'positive': signal.strength > 0,
                      'negative': signal.strength < 0,
                      'neutral': signal.strength === 0 || signal.strength === null
                    }"
                  >
                    {{ signal.strength !== null ? signal.strength.toFixed(2) : 'N/A' }}
                  </span>
                </td>
                <td class="confidence-cell">
                  <span 
                    :class="{ 
                      'high-confidence': signal.confidence >= 0.7,
                      'medium-confidence': signal.confidence >= 0.4 && signal.confidence < 0.7,
                      'low-confidence': signal.confidence < 0.4
                    }"
                  >
                    {{ signal.confidence !== null ? (signal.confidence * 100).toFixed(0) + '%' : 'N/A' }}
                  </span>
                </td>
                <td class="date-cell">{{ formatDate(signal.timestamp) }}</td>
                <td class="reason-cell" :title="signal.reason">{{ signal.reason ? signal.reason.substring(0, 50) + (signal.reason.length > 50 ? '...' : '') : 'N/A' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Performance Tab -->
      <div v-if="activeTab === 'performance'" class="tab-pane">
        <h3 class="subsection-header">Performance Charts</h3>
        
        <div v-if="performanceHistoryData.length === 0" class="empty-state">
          <p class="empty-message">No performance history data available</p>
        </div>
        
        <div v-else class="performance-charts">
          <div class="chart-section">
            <h4 class="chart-title">Daily Equity Value</h4>
            <StockPriceGraph 
              :marketData="equityCurveData" 
              :symbol="accountName + ' Equity'"
              :height="400"
              :showControls="false"
            />
          </div>
          
          <div class="chart-section">
            <h4 class="chart-title">Daily Gain / Loss ($)</h4>
            <StockPriceGraph 
              :marketData="dailyPnlData" 
              :symbol="accountName + ' P&L'"
              :height="400"
              :showControls="false"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.portfolio-summary {
  margin: 2rem 0;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.summary-card {
  background-color: #f9f9f9;
  padding: 1.5rem;
  border-radius: 4px;
  text-align: center;
  border: 1px solid #f0f0f0;
}

.summary-label {
  display: block;
  font-size: 0.9rem;
  color: #000000;
  opacity: 0.8;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  color: #000000;
}

.subsection-header {
  font-size: 1.5rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #000000;
  padding-bottom: 0.5rem;
}

.positive {
  color: #28a745;
}

.negative {
  color: #dc3545;
}

.percentage-badge {
  display: inline-block;
  font-size: 1rem;
  font-weight: 600;
  margin-left: 0.5rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  vertical-align: middle;
}

.percentage-badge.positive {
  background-color: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.percentage-badge.negative {
  background-color: rgba(220, 53, 69, 0.1);
  color: #dc3545;
}


/* Tab styles copied from AssetTrade.vue */
.tabs {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 2rem;
}

.tab {
  padding: 1rem 2rem;
  background: none;
  border: none;
  font-size: 1rem;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
}

.tab:hover {
  color: #000000;
}

.tab.active {
  color: #000000;
  font-weight: 600;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #000000;
}

.tab-content {
  
}

.tab-pane {
  
}

@media (max-width: 768px) {
  .tab {
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
  }
}

.signal-buy {
  color: #28a745;
  font-weight: 600;
}

.signal-sell {
  color: #dc3545;
  font-weight: 600;
}

.signal-hold {
  color: #ffc107;
  font-weight: 600;
}

.buy {
  color: #28a745;
  font-weight: 600;
}

.sell {
  color: #dc3545;
  font-weight: 600;
}

.high-confidence {
  color: #28a745;
  font-weight: 600;
}

.medium-confidence {
  color: #ffc107;
  font-weight: 600;
}

.low-confidence {
  color: #dc3545;
  font-weight: 600;
}

.neutral {
  color: #6c757d;
}

.signal-cell,
.strength-cell,
.confidence-cell,
th:nth-child(2),  /* Signal */
th:nth-child(5),  /* Strength */
th:nth-child(6) { /* Confidence */
  text-align: center;
}

.reason-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pending {
  color: #ffc107;
  font-weight: 600;
}

.status-filled {
  color: #28a745;
  font-weight: 600;
}

.status-cancelled {
  color: #dc3545;
  font-weight: 600;
}

.side-cell,
.type-cell,
.status-cell,
th:nth-child(2),  /* Side */
th:nth-child(3),  /* Type */
th:nth-child(6) { /* Status */
  text-align: center;
}

.date-cell,
th:nth-child(7),  /* Submitted */
th:nth-child(8) { /* Filled */
  text-align: center;
  font-size: 0.9rem;
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

.symbol-cell {
  font-weight: 600;
  color: #000000;
}

.clickable {
  cursor: pointer;
  transition: color 0.2s ease;
}

.clickable:hover {
  color: #007bff;
  text-decoration: underline;
}

.name-cell {
  color: #000000;
  opacity: 0.8;
}

.quantity-cell,
.price-cell,
.value-cell,
.gain-loss-cell,
.gain-loss-percentage-cell,
th:nth-child(3),  /* Quantity */
th:nth-child(4),  /* Avg Entry Price */
th:nth-child(5),  /* Current Price */
th:nth-child(6),  /* Current Value */
th:nth-child(7),  /* Gain/Loss */
th:nth-child(8) { /* % Gain/Loss */
  text-align: right;
}

.gain-loss-cell,
.gain-loss-percentage-cell {
  font-weight: 600;
}

/* Signal filter styles */
.signal-filters {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.filter-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #333;
}

.filter-select,
.filter-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
  background: #fff;
  color: #333;
  min-width: 140px;
}

.filter-select:focus,
.filter-input:focus {
  outline: none;
  border-color: #000000;
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1);
}

.filter-input {
  min-width: 160px;
}

.filter-info {
  font-size: 0.85rem;
  color: #666;
  padding: 0.5rem 0;
  align-self: center;
}

/* Strategy name display styles */
.strategy-name-display {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.strategy-label {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.strategy-value {
  color: #000;
  font-weight: 500;
  font-size: 0.9rem;
}

/* Account status toggle styles */
.account-status-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.account-status-toggle label {
  font-weight: 600;
  color: #333;
  margin: 0;
  font-size: 0.9rem;
}

.status-checkbox {
  width: 1.2rem;
  height: 1.2rem;
  cursor: pointer;
}

.status-label {
  font-size: 0.9rem;
  color: #666;
  min-width: 60px;
}

/* Performance chart styles */
.performance-charts {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.chart-section {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
}

.chart-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #000;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #f0f0f0;
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
  
  .summary-cards {
    grid-template-columns: 1fr;
  }
  
  .data-table {
    font-size: 0.9rem;
  }
}
</style>
