<script setup>
import { ref, onMounted, watch, computed } from 'vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['navigate'])

// Form data
const ticker = ref('')
const shares = ref(1)
const orderType = ref('market')
const price = ref('')
const selectedAccount = ref('')
const accounts = ref([])
const portfolioTickers = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// Current price for market orders
const currentPrice = ref(null)
const isFetchingPrice = ref(false)

// Order type options
const orderTypeOptions = [
  { value: 'market', label: 'Market' },
  { value: 'limit', label: 'Limit' },
  { value: 'stop', label: 'Stop' }
]

// Fetch accounts from backend
const fetchAccounts = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/accounts')
    if (response.ok) {
      const data = await response.json()
      accounts.value = data || []
      console.log('Accounts loaded:', accounts.value) // Debug log
      
      // Only set default account if no account is already selected (from navigation params)
      if (accounts.value.length > 0 && !selectedAccount.value) {
        selectedAccount.value = accounts.value[0].account_id
        console.log('Default account selected:', selectedAccount.value) // Debug log
      }
    } else {
      console.error('Failed to fetch accounts')
    }
  } catch (error) {
    console.error('Error fetching accounts:', error)
    errorMessage.value = 'Failed to load accounts. Please check if the backend server is running.'
  }
}

// Fetch portfolio tickers for the selected account
const fetchPortfolioTickers = async (accountName) => {
  if (!accountName) {
    portfolioTickers.value = []
    return
  }

  try {
    const response = await fetch(`http://localhost:5000/api/accounts/${accountName}/portfolio`)
    if (response.ok) {
      const data = await response.json()
      console.log('Portfolio data received:', data) // Debug log
      
      // Extract ticker symbols from holdings object
      if (data && data.holdings && typeof data.holdings === 'object') {
        // Get all ticker symbols from the holdings object keys
        const tickers = Object.keys(data.holdings)
        portfolioTickers.value = tickers.sort()
        console.log('Available tickers:', portfolioTickers.value) // Debug log
      } else {
        console.warn('Portfolio data structure is unexpected:', data)
        portfolioTickers.value = []
      }
    } else {
      console.error('Failed to fetch portfolio')
      portfolioTickers.value = []
    }
  } catch (error) {
    console.error('Error fetching portfolio:', error)
    portfolioTickers.value = []
    // Don't show error message for portfolio fetch - it's expected when backend is not running
  }
}

// Stock sell function
const handleSell = async () => {
  // Clear previous messages
  errorMessage.value = ''
  successMessage.value = ''

  // Validate form
  if (!selectedAccount.value) {
    errorMessage.value = 'Please select an account'
    return
  }

  if (!ticker.value.trim()) {
    errorMessage.value = 'Please select a ticker symbol'
    return
  }

  if (shares.value <= 0) {
    errorMessage.value = 'Please enter a valid number of shares'
    return
  }

  // Validate price for limit and stop orders
  if ((orderType.value === 'limit' || orderType.value === 'stop') && (!price.value || parseFloat(price.value) <= 0)) {
    errorMessage.value = `Please enter a valid ${orderType.value === 'limit' ? 'limit' : 'stop'} price`
    return
  }

  isLoading.value = true

  try {
    const sellData = {
      stock_symbol: ticker.value.toUpperCase(),
      shares: shares.value,
      order_type: orderType.value
    }

    // Add price for limit and stop orders
    if (orderType.value === 'limit') {
      sellData.price = parseFloat(price.value)
    } else if (orderType.value === 'stop') {
      sellData.stop_price = parseFloat(price.value)
    }

    const response = await fetch(`http://localhost:5000/api/accounts/${selectedAccount.value}/sell`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(sellData)
    })

    if (response.ok) {
      const result = await response.json()
      
      // Navigate to transaction details page with order data
      const transactionData = {
        account_id: selectedAccount.value,
        stock_symbol: ticker.value.toUpperCase(),
        shares: shares.value,
        order_type: orderType.value,
        price: orderType.value === 'limit' ? parseFloat(price.value) : null,
        stop_price: orderType.value === 'stop' ? parseFloat(price.value) : null,
        timestamp: new Date().toISOString(),
        side: 'SELL'
      }
      
      emit('navigate', 'asset-transaction', transactionData)
    } else {
      const errorData = await response.json()
      errorMessage.value = errorData.message || `Failed to place sell order. Status: ${response.status}`
    }
  } catch (error) {
    console.error('Error placing sell order:', error)
    errorMessage.value = 'Failed to connect to server. Please check if the backend is running.'
  } finally {
    isLoading.value = false
  }
}

// Fetch current price for market orders
const fetchCurrentPrice = async (symbol) => {
  if (!symbol) {
    currentPrice.value = null
    return
  }

  isFetchingPrice.value = true
  currentPrice.value = null

  try {
    const response = await fetch(`http://localhost:5000/api/instruments/get/${symbol}`)
    if (response.ok) {
      const data = await response.json()
      currentPrice.value = data.current_price || null
    } else {
      console.error('Failed to fetch current price')
      currentPrice.value = null
    }
  } catch (error) {
    console.error('Error fetching current price:', error)
    currentPrice.value = null
  } finally {
    isFetchingPrice.value = false
  }
}

// Watch for account selection changes to fetch portfolio tickers
watch(selectedAccount, (newAccount) => {
  if (newAccount) {
    fetchPortfolioTickers(newAccount)
    // Reset ticker selection when account changes
    ticker.value = ''
    currentPrice.value = null
  }
})

// Watch for ticker changes to fetch current price
watch(ticker, (newTicker) => {
  if (newTicker && orderType.value === 'market') {
    fetchCurrentPrice(newTicker)
  } else {
    currentPrice.value = null
  }
})

// Watch for order type changes
watch(orderType, (newOrderType) => {
  if (newOrderType === 'market' && ticker.value) {
    fetchCurrentPrice(ticker.value)
  } else {
    currentPrice.value = null
  }
})

// Watch for navigation params to auto-select account
watch(() => props.navigationParams, (newParams) => {
  console.log('Navigation params received:', newParams) // Debug log
  if (newParams.account_id) {
    // If accounts are already loaded, select immediately
    if (accounts.value.length > 0) {
      const accountExists = accounts.value.some(account => account.account_id === newParams.account_id)
      if (accountExists) {
        selectedAccount.value = newParams.account_id
        console.log('Auto-selected account:', newParams.account_id) // Debug log
      }
    } else {
      // If accounts aren't loaded yet, wait for them to load
      const waitForAccounts = () => {
        if (accounts.value.length > 0) {
          const accountExists = accounts.value.some(account => account.account_id === newParams.account_id)
          if (accountExists) {
            selectedAccount.value = newParams.account_id
            console.log('Auto-selected account after loading:', newParams.account_id) // Debug log
          }
        } else {
          setTimeout(waitForAccounts, 100)
        }
      }
      waitForAccounts()
    }
  }
}, { immediate: true })

onMounted(() => {
  fetchAccounts()
})

// Calculate total amount
const calculateTotalAmount = () => {
  let price = null
  
  if (orderType.value === 'market') {
    // For market orders, use the fetched current price
    price = currentPrice.value
  } else if (orderType.value === 'limit') {
    // For limit orders, use the limit price
    price = parseFloat(price.value)
  } else if (orderType.value === 'stop') {
    // For stop orders, use the stop price
    price = parseFloat(price.value)
  }
  
  if (!price || shares.value <= 0) return 'N/A'
  return `$${(price * shares.value).toFixed(2)}`
}
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>Sell Asset</h2>
        <p>Sell stocks from your portfolio</p>
      </div>
    </div>

    <!-- Order Form -->
    <div class="order-form">
      <div class="form-section">
        <h3 class="subsection-header">Order Details</h3>
        
        <!-- Account Selection -->
        <div class="form-group">
          <label for="account">Account</label>
          <select 
            id="account" 
            v-model="selectedAccount" 
            :disabled="accounts.length === 0"
          >
            <option value="" disabled>Select an account</option>
            <option 
              v-for="account in accounts" 
              :key="account.account_id" 
              :value="account.account_id"
            >
              {{ account.account_id }} (Balance: ${{ account.cash_balance.toFixed(2) }})
            </option>
          </select>
          <p v-if="accounts.length === 0" class="form-hint">
            No accounts found. Please add an account first.
          </p>
        </div>

        <!-- Ticker Dropdown -->
        <div class="form-group">
          <label for="ticker">Ticker Symbol</label>
          <select 
            id="ticker" 
            v-model="ticker" 
            :disabled="!selectedAccount || portfolioTickers.length === 0"
          >
            <option value="" disabled>Select a ticker</option>
            <option 
              v-for="tickerSymbol in portfolioTickers" 
              :key="tickerSymbol" 
              :value="tickerSymbol"
            >
              {{ tickerSymbol }}
            </option>
          </select>
          <p v-if="selectedAccount && portfolioTickers.length === 0" class="form-hint">
            No assets found in this account's portfolio.
          </p>
          <p v-if="!selectedAccount" class="form-hint">
            Please select an account first to see available tickers.
          </p>
        </div>

        <!-- Number of Shares -->
        <div class="form-group">
          <label for="shares">Number of Shares</label>
          <input 
            id="shares" 
            v-model.number="shares" 
            type="number" 
            min="1" 
            step="1"
            placeholder="Enter number of shares"
          />
        </div>

        <!-- Order Type Dropdown -->
        <div class="form-group">
          <label for="orderType">Order Type</label>
          <select 
            id="orderType" 
            v-model="orderType" 
          >
            <option 
              v-for="option in orderTypeOptions" 
              :key="option.value" 
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <!-- Price Input (Conditional for Limit/Stop Orders) -->
        <div v-if="orderType === 'limit' || orderType === 'stop'" class="form-group">
          <label for="price">
            {{ orderType === 'limit' ? 'Limit Price' : 'Stop Price' }}
          </label>
          <input 
            id="price" 
            v-model="price" 
            type="number" 
            min="0.01" 
            step="0.01"
            :placeholder="orderType === 'limit' ? 'Enter limit price' : 'Enter stop price'"
          />
          <p class="form-hint">
            {{ orderType === 'limit' 
              ? 'Order will execute only at this price or better' 
              : 'Order will trigger when price reaches this level' 
            }}
          </p>
        </div>

        <!-- Order Type Description -->
        <div class="order-type-info">
          <p v-if="orderType === 'market'" class="info-text">
            <strong>Market Order:</strong> Execute immediately at the current market price
          </p>
          <p v-else-if="orderType === 'limit'" class="info-text">
            <strong>Limit Order:</strong> Execute only at a specified price or better
          </p>
          <p v-else-if="orderType === 'stop'" class="info-text">
            <strong>Stop Order:</strong> Execute when price reaches a specified level
          </p>
        </div>

        <!-- Messages -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>

        <!-- Sell Button -->
        <div class="form-actions">
          <button 
            class="btn-primary" 
            @click="handleSell"
            :disabled="!selectedAccount || !ticker.trim() || shares <= 0 || isLoading || 
                     ((orderType === 'limit' || orderType === 'stop') && (!price || parseFloat(price) <= 0))"
          >
            {{ isLoading ? 'Processing...' : 'Sell Asset' }}
          </button>
        </div>
      </div>

        <!-- Order Summary -->
        <div class="order-summary">
          <h3 class="subsection-header">Order Summary</h3>
          <div class="summary-content">
            <div class="summary-item">
              <span class="summary-label">Account:</span>
              <span class="summary-value">{{ selectedAccount || 'N/A' }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Ticker:</span>
              <span class="summary-value">{{ ticker.toUpperCase() || 'N/A' }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Shares:</span>
              <span class="summary-value">{{ shares }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Order Type:</span>
              <span class="summary-value">{{ orderType }}</span>
            </div>
            <div v-if="(orderType === 'limit' || orderType === 'stop') && price" class="summary-item">
              <span class="summary-label">{{ orderType === 'limit' ? 'Limit Price' : 'Stop Price' }}:</span>
              <span class="summary-value">${{ parseFloat(price).toFixed(2) }}</span>
            </div>
            <div v-else-if="orderType === 'market' && ticker" class="summary-item">
              <span class="summary-label">Current Price:</span>
              <span class="summary-value">
                <span v-if="isFetchingPrice">Loading...</span>
                <span v-else-if="currentPrice">${{ currentPrice.toFixed(2) }}</span>
                <span v-else>N/A</span>
              </span>
            </div>
            <div class="summary-item total-amount">
              <span class="summary-label">Total Amount:</span>
              <span class="summary-value">{{ calculateTotalAmount() }}</span>
            </div>
          </div>
        </div>
    </div>
  </section>
</template>

<style scoped>
.order-form {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
  margin-top: 2rem;
}

.form-section {
  background: #f9f9f9;
  border-radius: 4px;
  padding: 2rem;
  border: 1px solid #f0f0f0;
}

.subsection-header {
  font-size: 1.5rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #000000;
  padding-bottom: 0.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-hint {
  margin: 0.5rem 0 0 0;
  font-size: 0.875rem;
  color: #000000;
  opacity: 0.8;
  font-style: italic;
}

.order-type-info {
  background: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 1rem;
  margin: 1.5rem 0;
}

.info-text {
  margin: 0;
  color: #000000;
  opacity: 0.8;
  font-size: 0.9rem;
  line-height: 1.4;
}

.error-message {
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
  padding: 1rem;
  margin: 1rem 0;
  color: #c33;
  font-size: 0.9rem;
  line-height: 1.4;
}

.success-message {
  background: #efe;
  border: 1px solid #cfc;
  border-radius: 4px;
  padding: 1rem;
  margin: 1rem 0;
  color: #363;
  font-size: 0.9rem;
  line-height: 1.4;
}

.form-actions {
  margin-top: 2rem;
}

.order-summary {
  background: #f9f9f9;
  border-radius: 4px;
  padding: 2rem;
  border: 1px solid #f0f0f0;
  align-self: start;
}

.summary-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.summary-item:last-child {
  border-bottom: none;
}

.summary-label {
  font-weight: 600;
  color: #000000;
  opacity: 0.8;
}

.summary-value {
  font-weight: 600;
  color: #000000;
}

.total-amount {
  background-color: #f8f9fa;
  border-radius: 4px;
  padding: 1rem;
  margin-top: 0.5rem;
  border: 2px solid #e9ecef;
}

.total-amount .summary-label {
  font-size: 1.1rem;
  color: #000000;
  opacity: 1;
}

.total-amount .summary-value {
  font-size: 1.1rem;
  color: #28a745;
  font-weight: 700;
}

@media (max-width: 768px) {
  .order-form {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .form-section,
  .order-summary {
    padding: 1.5rem;
  }
}
</style>
