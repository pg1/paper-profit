<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['navigate'])

// Transaction data from navigation params
const transactionData = ref({
  account_id: '',
  stock_symbol: '',
  shares: 0,
  order_type: 'market',
  price: null,
  stop_price: null,
  timestamp: new Date().toISOString()
})

// Current price for market orders
const currentPrice = ref(null)
const isFetchingPrice = ref(false)

// Status tracking
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// Initialize with navigation params
onMounted(() => {
  if (props.navigationParams) {
    transactionData.value = {
      ...transactionData.value,
      ...props.navigationParams
    }
    
    // Fetch current price for market orders
    if (transactionData.value.order_type === 'market' && transactionData.value.stock_symbol) {
      fetchCurrentPrice(transactionData.value.stock_symbol)
    }
  }
})

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

// Format price display
const formatPrice = (price) => {
  if (!price) return 'N/A'
  return `$${parseFloat(price).toFixed(2)}`
}

// Format order type for display
const formatOrderType = (orderType) => {
  const types = {
    market: 'Market Order',
    limit: 'Limit Order',
    stop: 'Stop Order'
  }
  return types[orderType] || orderType
}

// Calculate total cost
const calculateTotalCost = () => {
  let price = null
  
  if (transactionData.value.order_type === 'market') {
    // For market orders, use the fetched current price
    price = currentPrice.value
  } else if (transactionData.value.order_type === 'limit') {
    // For limit orders, use the limit price
    price = transactionData.value.price
  } else if (transactionData.value.order_type === 'stop') {
    // For stop orders, use the stop price
    price = transactionData.value.stop_price
  }
  
  if (!price || transactionData.value.shares <= 0) return 'N/A'
  return `$${(parseFloat(price) * transactionData.value.shares).toFixed(2)}`
}


// Handle back to welcome
const handleBackToWelcome = () => {
  emit('navigate', 'welcome')
}

// Handle new transaction
const handleNewTransaction = () => {
  emit('navigate', 'trade')
}
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>Transaction Details</h2>
        <p>Review your order details</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleBackToWelcome">← Back to Home</button>
      </div>
    </div>

    <!-- Transaction Details -->
    <div class="transaction-details">
      <div class="transaction-card">
        <div class="transaction-header">
          <h3 class="transaction-title">Order Confirmation</h3>
          <div class="transaction-status">
            <span class="status-badge status-pending">Pending</span>
          </div>
        </div>

        <div class="transaction-content">
          <!-- Order Summary -->
          <div class="summary-section">
            <h4 class="summary-title">Order Summary</h4>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">Account ID:</span>
                <span class="summary-value">{{ transactionData.account_id || 'N/A' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Stock Symbol:</span>
                <span class="summary-value">{{ transactionData.stock_symbol || 'N/A' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Shares:</span>
                <span class="summary-value">{{ transactionData.shares || 'N/A' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Order Type:</span>
                <span class="summary-value">{{ formatOrderType(transactionData.order_type) }}</span>
              </div>
              
              <!-- Price Information (Conditional) -->
              <div v-if="transactionData.order_type === 'limit'" class="summary-item">
                <span class="summary-label">Limit Price:</span>
                <span class="summary-value">{{ formatPrice(transactionData.price) }}</span>
              </div>
              <div v-else-if="transactionData.order_type === 'stop'" class="summary-item">
                <span class="summary-label">Stop Price:</span>
                <span class="summary-value">{{ formatPrice(transactionData.stop_price) }}</span>
              </div>
              <div v-else-if="transactionData.order_type === 'market'" class="summary-item">
                <span class="summary-label">Current Price:</span>
                <span class="summary-value">
                  <span v-if="isFetchingPrice">Loading...</span>
                  <span v-else-if="currentPrice">{{ formatPrice(currentPrice) }}</span>
                  <span v-else>N/A</span>
                </span>
              </div>
              
              <div class="summary-item">
                <span class="summary-label">Total Cost:</span>
                <span class="summary-value total-cost">{{ calculateTotalCost() }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Order Date:</span>
                <span class="summary-value">{{ new Date(transactionData.timestamp).toLocaleString() }}</span>
              </div>
            </div>
          </div>

          

         
        </div>

        
      </div>
    </div>

    <!-- Messages -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
    <div v-if="successMessage" class="success-message">
      {{ successMessage }}
    </div>
  </section>
</template>

<style scoped>
.transaction-details {
  max-width: 800px;
  margin: 2rem auto 0;
}

.transaction-card {
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  overflow: hidden;
}

.transaction-header {
  background: #000000;
  color: white;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.transaction-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.transaction-status {
  display: flex;
  align-items: center;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
}

.status-pending {
  background: #ffa500;
  color: white;
}

.transaction-content {
  padding: 2rem;
}

.summary-section,
.status-section,
.next-steps {
  margin-bottom: 2rem;
}

.summary-title,
.status-title,
.steps-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1rem;
  border-bottom: 2px solid #000000;
  padding-bottom: 0.5rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
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

.total-cost {
  color: #007bff;
  font-size: 1.1rem;
}

.status-timeline {
  position: relative;
  padding-left: 2rem;
}

.status-timeline::before {
  content: '';
  position: absolute;
  left: 1rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e0e0e0;
}

.timeline-item {
  position: relative;
  margin-bottom: 2rem;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-marker {
  position: absolute;
  left: -2rem;
  top: 0.25rem;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: #e0e0e0;
  border: 2px solid white;
}

.timeline-item.active .timeline-marker {
  background: #007bff;
  border-color: #007bff;
}

.timeline-content {
  display: flex;
  flex-direction: column;
}

.timeline-title {
  font-weight: 600;
  color: #000000;
  margin-bottom: 0.25rem;
}

.timeline-time {
  font-size: 0.875rem;
  color: #666;
}

.steps-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.steps-list li {
  padding: 0.5rem 0;
  position: relative;
  padding-left: 1.5rem;
}

.steps-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #007bff;
  font-weight: bold;
}

.transaction-actions {
  padding: 1.5rem 2rem;
  background: #f5f5f5;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.header-actions {
  display: flex;
  gap: 1rem;
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

@media (max-width: 768px) {
  .transaction-details {
    margin: 1rem 0 0;
  }
  
  .transaction-header {
    padding: 1rem;
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .transaction-content {
    padding: 1rem;
  }
  
  .summary-grid {
    grid-template-columns: 1fr;
  }
  
  .transaction-actions {
    padding: 1rem;
    flex-direction: column;
  }
  
  .header-actions {
    flex-direction: column;
    width: 100%;
  }
}
</style>
