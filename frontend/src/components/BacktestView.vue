<script setup>
import { ref, onMounted, computed } from 'vue'
import SuccessBanner from './ui/SuccessBanner.vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['navigate'])

// State
const strategy = ref(null)
const backtestResults = ref([])
const isRunning = ref(false)
const isLoading = ref(false)
const error = ref(null)
const showSuccessMessage = ref(false)
const successMessage = ref('')

// Form fields
const startDate = ref('')
const endDate = ref('')
const initialCapital = ref(100000)

// Current backtest result detail
const selectedResult = ref(null)
const showDetail = ref(false)

// Chart data
const showChart = ref(false)

// Fetch strategy and backtest results
const fetchData = async () => {
  const strategyId = props.navigationParams?.strategyId
  if (!strategyId) {
    error.value = 'No strategy ID provided'
    return
  }

  isLoading.value = true
  error.value = null

  try {
    // Fetch strategy
    const strategyResponse = await fetch(`http://localhost:5000/api/strategies/${strategyId}`)
    if (!strategyResponse.ok) throw new Error('Failed to fetch strategy')
    strategy.value = await strategyResponse.json()

    // Fetch backtest results
    const resultsResponse = await fetch(`http://localhost:5000/api/strategies/${strategyId}/backtest-results?limit=10`)
    if (resultsResponse.ok) {
      backtestResults.value = await resultsResponse.json()
    }

    // Set default dates (last 6 months)
    const now = new Date()
    const sixMonthsAgo = new Date(now)
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6)
    endDate.value = now.toISOString().split('T')[0]
    startDate.value = sixMonthsAgo.toISOString().split('T')[0]

  } catch (err) {
    console.error('Error fetching data:', err)
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

// Run backtest
const runBacktest = async () => {
  const strategyId = props.navigationParams?.strategyId
  if (!strategyId) return

  if (!startDate.value || !endDate.value) {
    error.value = 'Please select start and end dates'
    return
  }

  isRunning.value = true
  error.value = null
  showDetail.value = false

  try {
    const response = await fetch(`http://localhost:5000/api/strategies/${strategyId}/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_date: startDate.value,
        end_date: endDate.value,
        initial_capital: initialCapital.value,
      })
    })

    if (!response.ok) {
      const errData = await response.json()
      throw new Error(errData.detail || 'Backtest failed')
    }

    const result = await response.json()
    selectedResult.value = result
    showDetail.value = true
    showChart.value = true
    showSuccessMessage.value = true
    successMessage.value = 'Backtest completed successfully!'

    // Refresh results list
    const resultsResponse = await fetch(`http://localhost:5000/api/strategies/${strategyId}/backtest-results?limit=10`)
    if (resultsResponse.ok) {
      backtestResults.value = await resultsResponse.json()
    }

  } catch (err) {
    console.error('Backtest error:', err)
    error.value = err.message
  } finally {
    isRunning.value = false
  }
}

// View a previous result
const viewResult = async (resultId) => {
  try {
    const response = await fetch(`http://localhost:5000/api/backtest-results/${resultId}`)
    if (!response.ok) throw new Error('Failed to fetch result')
    selectedResult.value = await response.json()
    showDetail.value = true
    showChart.value = true
  } catch (err) {
    console.error('Error fetching result:', err)
    error.value = err.message
  }
}

// Delete a result
const deleteResult = async (resultId) => {
  try {
    const response = await fetch(`http://localhost:5000/api/backtest-results/${resultId}`, {
      method: 'DELETE'
    })
    if (!response.ok) throw new Error('Failed to delete result')
    backtestResults.value = backtestResults.value.filter(r => r.id !== resultId)
    if (selectedResult.value?.id === resultId) {
      selectedResult.value = null
      showDetail.value = false
    }
    showSuccessMessage.value = true
    successMessage.value = 'Backtest result deleted'
  } catch (err) {
    console.error('Error deleting result:', err)
    error.value = err.message
  }
}

// Format currency
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0.00'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

// Format percentage
const formatPercent = (value) => {
  if (value === null || value === undefined) return '0.00%'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

// Format number
const formatNumber = (value) => {
  if (value === null || value === undefined) return '0'
  return new Intl.NumberFormat('en-US').format(value)
}

// Color class for positive/negative values
const pnlColor = (value) => {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return ''
}

// Equity curve data for chart
const equityChartData = computed(() => {
  if (!selectedResult.value?.equity_curve) return []
  return selectedResult.value.equity_curve
})

// Get bar height as percentage of max equity
const getBarHeight = (equity) => {
  const data = equityChartData.value
  if (!data || data.length === 0) return 0
  const maxEquity = Math.max(...data.map(p => p.equity))
  if (maxEquity <= 0) return 0
  return Math.max(2, (equity / maxEquity) * 100)
}

// Get bar color based on whether equity is above initial capital
const getBarColor = (equity) => {
  const initial = selectedResult.value?.initial_capital || 100000
  return equity >= initial ? '#2e7d32' : '#c62828'
}

// Trade log
const tradeLog = computed(() => {
  if (!selectedResult.value?.trade_log) return []
  return selectedResult.value.trade_log
})

// Monthly returns
const monthlyReturns = computed(() => {
  if (!selectedResult.value?.monthly_returns) return {}
  return selectedResult.value.monthly_returns
})

// Go back to strategy list
const goBack = () => {
  emit('navigate', 'strategy-list')
}

// Close success message
const closeSuccessMessage = () => {
  showSuccessMessage.value = false
  successMessage.value = ''
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <section class="section">
    <!-- Success Banner -->
    <SuccessBanner
      :show="showSuccessMessage"
      :message="successMessage"
      :duration="3000"
      @close="closeSuccessMessage"
    />

    <div class="section-header">
      <div>
        <h2>Backtest: {{ strategy?.name || 'Loading...' }}</h2>
        <p>Test your strategy against historical market data</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="goBack">← Back to Strategies</button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading strategy data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error && !strategy" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button class="btn btn-primary" @click="fetchData">Retry</button>
    </div>

    <div v-else>
      <!-- Backtest Configuration -->
      <div class="card">
        <h3>Backtest Configuration</h3>
        <div class="form-row">
          <div class="form-group">
            <label for="startDate">Start Date</label>
            <input
              id="startDate"
              v-model="startDate"
              type="date"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label for="endDate">End Date</label>
            <input
              id="endDate"
              v-model="endDate"
              type="date"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label for="initialCapital">Initial Capital ($)</label>
            <input
              id="initialCapital"
              v-model.number="initialCapital"
              type="number"
              min="1000"
              step="1000"
              class="form-input"
            />
          </div>
          <div class="form-group form-actions">
            <label>&nbsp;</label>
            <button
              class="btn-primary"
              @click="runBacktest"
              :disabled="isRunning"
            >
              {{ isRunning ? 'Running...' : 'Run Backtest' }}
            </button>
          </div>
        </div>
        <div v-if="error" class="error-message" style="margin-top: 1rem;">
          {{ error }}
        </div>
      </div>

      <!-- Running State -->
      <div v-if="isRunning" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Running backtest simulation...</p>
      </div>

      <!-- Backtest Results Detail -->
      <div v-if="showDetail && selectedResult" class="card">
        <h3>Backtest Results</h3>

        <!-- Summary Metrics -->
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="metric-label">Total Return</span>
            <span class="metric-value" :class="pnlColor(selectedResult.total_return_pct)">
              {{ formatCurrency(selectedResult.total_return) }}
            </span>
            <span class="metric-sub" :class="pnlColor(selectedResult.total_return_pct)">
              {{ formatPercent(selectedResult.total_return_pct) }}
            </span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Final Equity</span>
            <span class="metric-value">{{ formatCurrency(selectedResult.final_equity) }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Annualized Return</span>
            <span class="metric-value" :class="pnlColor(selectedResult.annualized_return)">
              {{ formatPercent(selectedResult.annualized_return) }}
            </span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Sharpe Ratio</span>
            <span class="metric-value" :class="pnlColor(selectedResult.sharpe_ratio)">
              {{ selectedResult.sharpe_ratio?.toFixed(2) || '0.00' }}
            </span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Max Drawdown</span>
            <span class="metric-value negative">{{ formatPercent(selectedResult.max_drawdown_pct) }}</span>
            <span class="metric-sub negative">{{ formatCurrency(selectedResult.max_drawdown) }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Volatility</span>
            <span class="metric-value">{{ formatPercent(selectedResult.volatility) }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Win Rate</span>
            <span class="metric-value" :class="pnlColor(selectedResult.win_rate - 50)">
              {{ selectedResult.win_rate?.toFixed(1) || '0.0' }}%
            </span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Profit Factor</span>
            <span class="metric-value" :class="pnlColor(selectedResult.profit_factor - 1)">
              {{ selectedResult.profit_factor?.toFixed(2) || '0.00' }}
            </span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Total Trades</span>
            <span class="metric-value">{{ selectedResult.total_trades || 0 }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Winning / Losing</span>
            <span class="metric-value">
              <span class="positive">{{ selectedResult.winning_trades || 0 }}</span>
              /
              <span class="negative">{{ selectedResult.losing_trades || 0 }}</span>
            </span>
          </div>
        </div>

        <!-- Equity Curve (Simple Text Chart) -->
        <div v-if="equityChartData.length > 0" class="chart-section">
          <h4>Equity Curve</h4>
          <div class="equity-chart">
            <div
              v-for="(point, idx) in equityChartData"
              :key="idx"
              class="chart-bar-wrapper"
            >
              <div
                class="chart-bar"
                :style="{
                  height: getBarHeight(point.equity) + '%',
                  backgroundColor: getBarColor(point.equity)
                }"
                :title="`${point.date}: ${formatCurrency(point.equity)}`"
              ></div>
            </div>
          </div>
          <div class="chart-labels">
            <span>{{ equityChartData[0]?.date || '' }}</span>
            <span>{{ equityChartData[equityChartData.length - 1]?.date || '' }}</span>
          </div>
        </div>

        <!-- Monthly Returns -->
        <div v-if="Object.keys(monthlyReturns).length > 0" class="monthly-section">
          <h4>Monthly Returns</h4>
          <div class="monthly-grid">
            <div
              v-for="(ret, month) in monthlyReturns"
              :key="month"
              class="monthly-card"
              :class="ret >= 0 ? 'positive-bg' : 'negative-bg'"
            >
              <span class="month-label">{{ month }}</span>
              <span class="month-value">{{ formatPercent(ret) }}</span>
            </div>
          </div>
        </div>

        <!-- Trade Log -->
        <div v-if="tradeLog.length > 0" class="trade-log-section">
          <h4>Trade Log ({{ tradeLog.length }} trades)</h4>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Price</th>
                  <th>Qty</th>
                  <th>Value</th>
                  <th v-if="tradeLog[0].pnl !== undefined">P&L</th>
                  <th v-if="tradeLog[0].pnl_pct !== undefined">P&L %</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(trade, idx) in tradeLog"
                  :key="idx"
                  :class="{
                    'row-buy': trade.action === 'BUY',
                    'row-sell': trade.action === 'SELL'
                  }"
                >
                  <td>{{ trade.date }}</td>
                  <td><strong>{{ trade.symbol }}</strong></td>
                  <td>
                    <span :class="trade.action === 'BUY' ? 'badge-buy' : 'badge-sell'">
                      {{ trade.action }}
                    </span>
                  </td>
                  <td>{{ formatCurrency(trade.price) }}</td>
                  <td>{{ formatNumber(trade.quantity) }}</td>
                  <td>{{ formatCurrency(trade.value) }}</td>
                  <td v-if="trade.pnl !== undefined" :class="pnlColor(trade.pnl)">
                    {{ formatCurrency(trade.pnl) }}
                  </td>
                  <td v-if="trade.pnl_pct !== undefined" :class="pnlColor(trade.pnl_pct)">
                    {{ formatPercent(trade.pnl_pct) }}
                  </td>
                  <td class="reason-cell">{{ trade.reason || trade.reasons?.join('; ') || '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Previous Results -->
      <div v-if="backtestResults.length > 0" class="card">
        <h3>Previous Backtest Results</h3>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Period</th>
                <th>Initial Capital</th>
                <th>Total Return</th>
                <th>Sharpe</th>
                <th>Win Rate</th>
                <th>Trades</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="result in backtestResults" :key="result.id">
                <td>{{ result.created_at?.split('T')[0] || 'N/A' }}</td>
                <td>{{ result.start_date?.split('T')[0] }} → {{ result.end_date?.split('T')[0] }}</td>
                <td>{{ formatCurrency(result.initial_capital) }}</td>
                <td :class="pnlColor(result.total_return_pct)">
                  {{ formatPercent(result.total_return_pct) }}
                </td>
                <td>{{ result.sharpe_ratio?.toFixed(2) || 'N/A' }}</td>
                <td>{{ result.win_rate?.toFixed(1) || 'N/A' }}%</td>
                <td>{{ result.total_trades || 0 }}</td>
                <td>
                  <span :class="result.status === 'completed' ? 'badge-success' : result.status === 'failed' ? 'badge-error' : 'badge-warning'">
                    {{ result.status }}
                  </span>
                </td>
                <td class="actions-cell">
                  <button
                    class="btn-small btn-secondary"
                    @click="viewResult(result.id)"
                    :disabled="result.status !== 'completed'"
                  >
                    View
                  </button>
                  <button
                    class="btn-small btn-danger"
                    @click="deleteResult(result.id)"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
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

.card {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.card h3 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  color: #000000;
}

.card h4 {
  margin: 1.5rem 0 0.75rem 0;
  font-size: 1rem;
  color: #000000;
}

.form-row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 150px;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #000000;
}

.form-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #000000;
  background: #ffffff;
}

.form-input:focus {
  outline: none;
  border-color: #000000;
}

.form-actions {
  flex: 0 0 auto;
  min-width: auto;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.metric-card {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 0.75rem;
  text-align: center;
}

.metric-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6c757d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.25rem;
}

.metric-value {
  display: block;
  font-size: 1.1rem;
  font-weight: 700;
  color: #000000;
}

.metric-sub {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  margin-top: 0.15rem;
}

.positive { color: #2e7d32; }
.negative { color: #c62828; }

/* Equity Chart */
.chart-section {
  margin-top: 1rem;
}

.equity-chart {
  display: flex;
  align-items: flex-end;
  height: 120px;
  gap: 2px;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e0e0e0;
}

.chart-bar-wrapper {
  flex: 1;
  display: flex;
  align-items: flex-end;
  height: 100%;
}

.chart-bar {
  width: 100%;
  min-height: 2px;
  border-radius: 2px 2px 0 0;
  transition: height 0.3s ease;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #6c757d;
  margin-top: 0.25rem;
}

/* Monthly Returns */
.monthly-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.5rem;
}

.monthly-card {
  padding: 0.5rem;
  border-radius: 4px;
  text-align: center;
  font-size: 0.8rem;
}

.positive-bg {
  background: #e8f5e9;
  border: 1px solid #c8e6c9;
}

.negative-bg {
  background: #ffebee;
  border: 1px solid #ffcdd2;
}

.month-label {
  display: block;
  font-weight: 600;
  color: #000000;
}

.month-value {
  display: block;
  font-weight: 700;
  margin-top: 0.15rem;
}

.positive-bg .month-value { color: #2e7d32; }
.negative-bg .month-value { color: #c62828; }

/* Trade Log */
.trade-log-section {
  margin-top: 1rem;
}

.row-buy {
  background: #f1f8e9;
}

.row-sell {
  background: #fce4ec;
}

.badge-buy {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: #2e7d32;
  color: white;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 700;
}

.badge-sell {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: #c62828;
  color: white;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 700;
}

.badge-success {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-error {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: #ffebee;
  color: #c62828;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-warning {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  background: #fff8e1;
  color: #f57f17;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
}

.reason-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8rem;
  color: #666;
}

.actions-cell {
  display: flex;
  gap: 0.5rem;
}

.btn-small {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 3px;
  cursor: pointer;
  border: 1px solid #ccc;
  background: #ffffff;
  color: #000000;
}

.btn-small:hover {
  background: #f0f0f0;
}

.btn-danger {
  border-color: #c62828;
  color: #c62828;
}

.btn-danger:hover {
  background: #ffebee;
}

/* Loading State */
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
  color: #c62828;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }

  .form-group {
    min-width: 100%;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .monthly-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
