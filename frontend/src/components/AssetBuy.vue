<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['navigate'])

// Form data
const market = ref('NYSE')
const ticker = ref('')
const shares = ref(1)
const orderType = ref('market')
const price = ref('')
const selectedAccount = ref('')
const accounts = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// Autocomplete and price data
const searchQuery = ref('')
const searchResults = ref([])
const showAutocomplete = ref(false)
const isSearching = ref(false)
const selectedResultIndex = ref(-1)
const currentPrice = ref(null)
const isFetchingPrice = ref(false)

// Market options
const marketOptions = [
  { value: 'NYSE', label: 'NYSE' },
  { value: 'NASDAQ', label: 'Nasdaq' },
  { value: 'DAX', label: 'DAX' },
  { value: 'FTSE', label: 'FTSE' },
  { value: 'NIKKEI', label: 'Nikkei' },
  { value: 'HANG_SENG', label: 'Hang Seng' },
  { value: 'ASX', label: 'ASX' }
]

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

// Stock buy function
const handleBuy = async () => {
  // Clear previous messages
  errorMessage.value = ''
  successMessage.value = ''

  // Validate form
  if (!selectedAccount.value) {
    errorMessage.value = 'Please select an account'
    return
  }

  if (!ticker.value.trim()) {
    errorMessage.value = 'Please enter a ticker symbol'
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
    const buyData = {
      stock_symbol: ticker.value.toUpperCase(),
      shares: shares.value,
      order_type: orderType.value
    }

    // Add price for limit and stop orders
    if (orderType.value === 'limit') {
      buyData.price = parseFloat(price.value)
    } else if (orderType.value === 'stop') {
      buyData.stop_price = parseFloat(price.value)
    }

    const response = await fetch(`http://localhost:5000/api/accounts/${selectedAccount.value}/buy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(buyData)
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
        timestamp: new Date().toISOString()
      }
      
      emit('navigate', 'asset-transaction', transactionData)
    } else {
      const errorData = await response.json()
      errorMessage.value = errorData.message || `Failed to place order. Status: ${response.status}`
    }
  } catch (error) {
    console.error('Error placing order:', error)
    errorMessage.value = 'Failed to connect to server. Please check if the backend is running.'
  } finally {
    isLoading.value = false
  }
}

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


// Autocomplete methods
const searchInstruments = async (query) => {
  if (!query || query.length < 2) {
    searchResults.value = []
    showAutocomplete.value = false
    return
  }

  isSearching.value = true
  showAutocomplete.value = true

  try {
    const response = await fetch(`http://localhost:5000/api/instruments/search?query=${encodeURIComponent(query)}&limit=5`)
    if (response.ok) {
      const data = await response.json()
      searchResults.value = data || []
    } else {
      searchResults.value = []
    }
  } catch (error) {
    console.error('Error searching instruments:', error)
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

const handleTickerInput = (event) => {
  const value = event.target.value
  ticker.value = value
  searchQuery.value = value
  
  // Debounce the search
  clearTimeout(window.searchTimeout)
  window.searchTimeout = setTimeout(() => {
    searchInstruments(value)
  }, 300)
}

const selectResult = (result) => {
  ticker.value = result.symbol
  searchQuery.value = result.symbol
  searchResults.value = []
  showAutocomplete.value = false
  selectedResultIndex.value = -1
  
  // Update market dropdown based on selected instrument's exchange
  updateMarketFromExchange(result.exchange)
  
  // Fetch current price for the selected symbol
  fetchCurrentPrice(result.symbol)
}

const handleKeyDown = (event) => {
  if (!showAutocomplete.value || searchResults.value.length === 0) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedResultIndex.value = Math.min(selectedResultIndex.value + 1, searchResults.value.length - 1)
      break
    case 'ArrowUp':
      event.preventDefault()
      selectedResultIndex.value = Math.max(selectedResultIndex.value - 1, -1)
      break
    case 'Enter':
      event.preventDefault()
      if (selectedResultIndex.value >= 0) {
        selectResult(searchResults.value[selectedResultIndex.value])
      }
      break
    case 'Escape':
      showAutocomplete.value = false
      selectedResultIndex.value = -1
      break
  }
}

const hideAutocomplete = () => {
  // Small delay to allow click events to register
  setTimeout(() => {
    showAutocomplete.value = false
    selectedResultIndex.value = -1
  }, 150)
}

// Map API exchange codes to market dropdown values
const updateMarketFromExchange = (exchange) => {
  const exchangeMap = {
    'NMS': 'NASDAQ',      // NASDAQ
    'NYQ': 'NYSE',        // NYSE
    'NGM': 'NASDAQ',      // NASDAQ Global Market
    'ASE': 'NYSE',        // NYSE American
    'PCX': 'NYSE',        // NYSE Arca
    'BTS': 'NYSE',        // NYSE National
    'IEX': 'NYSE',        // Investors Exchange
    'OPR': 'NYSE',        // Options (default to NYSE)
    'XET': 'DAX',         // Xetra (German)
    'FRA': 'DAX',         // Frankfurt
    'LSE': 'FTSE',        // London Stock Exchange
    'TSE': 'NIKKEI',      // Tokyo Stock Exchange
    'HKG': 'HANG_SENG',   // Hong Kong
    'ASX': 'ASX'          // Australian Securities Exchange
  }
  
  // Default to NYSE if exchange not found in map
  market.value = exchangeMap[exchange] || 'NYSE'
}

// Fetch current price for the selected symbol
const fetchCurrentPrice = async (symbol) => {
  if (!symbol) {
    currentPrice.value = null
    return
  }

  isFetchingPrice.value = true
  currentPrice.value = null

  try {
    // Use the new API endpoint to get instrument data including current price
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

// Computed property for total amount
const totalAmount = () => {
  if (!currentPrice.value || !shares.value) return 0
  return currentPrice.value * shares.value
}
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>Buy Asset</h2>
        <p>Purchase stocks and other assets</p>
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

        <!-- Market Dropdown -->
        <div class="form-group">
          <label for="market">Market</label>
          <select 
            id="market" 
            v-model="market" 
          >
            <option 
              v-for="option in marketOptions" 
              :key="option.value" 
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <!-- Ticker Search Input with Autocomplete -->
        <div class="form-group autocomplete-container">
          <label for="ticker">Ticker Symbol</label>
          <div class="input-wrapper">
            <input 
              id="ticker" 
              v-model="ticker" 
              type="text" 
              placeholder="Enter ticker symbol (e.g., AAPL, MSFT)"
              maxlength="10"
              @input="handleTickerInput"
              @keydown="handleKeyDown"
              @blur="hideAutocomplete"
            />
            <!-- Autocomplete Dropdown -->
            <div v-if="showAutocomplete" class="autocomplete-dropdown">
              <div v-if="isSearching" class="autocomplete-loading">
                Searching...
              </div>
              <div v-else-if="searchResults.length === 0 && searchQuery.length >= 2" class="autocomplete-no-results">
                No results found for "{{ searchQuery }}"
              </div>
              <div v-else class="autocomplete-results">
                <div
                  v-for="(result, index) in searchResults"
                  :key="result.symbol"
                  class="autocomplete-item"
                  :class="{ 'selected': index === selectedResultIndex }"
                  @click="selectResult(result)"
                  @mouseenter="selectedResultIndex = index"
                >
                  <div class="symbol-name">
                    <strong>{{ result.symbol }}</strong>
                    <span class="company-name">{{ result.name }}</span>
                  </div>
                  <div class="instrument-details">
                    <span class="exchange">{{ result.exchange_display }}</span>
                    <span class="type">{{ result.type_display }}</span>
                    <span v-if="result.sector_display" class="sector">{{ result.sector_display }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <p class="form-hint">
            Start typing to search for stocks, ETFs, and options
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

        <!-- Buy Button -->
        <div class="form-actions">
          <button 
            class="btn-primary" 
            @click="handleBuy"
            :disabled="!selectedAccount || !ticker.trim() || shares <= 0 || isLoading || 
                     ((orderType === 'limit' || orderType === 'stop') && (!price || parseFloat(price) <= 0))"
          >
            {{ isLoading ? 'Processing...' : 'Buy Asset' }}
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
              <span class="summary-label">Market:</span>
              <span class="summary-value">{{ market }}</span>
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
            
            <!-- Current Price and Total Amount -->
            <div v-if="ticker && currentPrice !== null" class="summary-item">
              <span class="summary-label">Current Price:</span>
              <span class="summary-value">${{ currentPrice.toFixed(2) }}</span>
            </div>
            <div v-else-if="isFetchingPrice" class="summary-item">
              <span class="summary-label">Current Price:</span>
              <span class="summary-value">Loading...</span>
            </div>
            
            <div v-if="ticker && currentPrice !== null && shares > 0" class="summary-item total-amount">
              <span class="summary-label">Total Amount:</span>
              <span class="summary-value">${{ totalAmount().toFixed(2) }}</span>
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

/* Autocomplete Styles */
.autocomplete-container {
  position: relative;
}

.input-wrapper {
  position: relative;
}

.autocomplete-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-height: 300px;
  overflow-y: auto;
}

.autocomplete-loading,
.autocomplete-no-results {
  padding: 1rem;
  text-align: center;
  color: #666;
  font-size: 0.9rem;
}

.autocomplete-results {
  padding: 0.5rem 0;
}

.autocomplete-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s ease;
}

.autocomplete-item:last-child {
  border-bottom: none;
}

.autocomplete-item:hover,
.autocomplete-item.selected {
  background-color: #f5f5f5;
}

.symbol-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.symbol-name strong {
  font-size: 1rem;
  color: #000000;
}

.company-name {
  font-size: 0.875rem;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.instrument-details {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.exchange,
.type,
.sector {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  background-color: #f0f0f0;
  color: #333;
}

.exchange {
  background-color: #e3f2fd;
  color: #1976d2;
}

.type {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

.sector {
  background-color: #e8f5e8;
  color: #388e3c;
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

  .autocomplete-dropdown {
    position: fixed;
    top: auto;
    left: 1rem;
    right: 1rem;
    bottom: 1rem;
    max-height: 50vh;
    border-radius: 4px;
    border-top: 1px solid #e0e0e0;
  }
}
</style>
