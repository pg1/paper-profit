<script setup>
import { ref, onMounted, computed, watch, getCurrentInstance } from 'vue'
import SuccessBanner from './ui/SuccessBanner.vue'

const emit = defineEmits(['navigate'])
const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const showSuccessBanner = ref(false)
const successMessage = ref('')

// Generic navigation helper: try router if available, otherwise emit navigate event
const navigateTo = (routeName, params = {}) => {
  try {
    const instance = getCurrentInstance()
    const maybeRouter = instance && instance.appContext && instance.appContext.config && instance.appContext.config.globalProperties && instance.appContext.config.globalProperties.$router
    if (maybeRouter && typeof maybeRouter.push === 'function') {
      // Use query to pass simple params (keeps behavior consistent with previous emits)
      maybeRouter.push({ name: routeName, query: params })
      return
    }
  } catch (err) {
    // ignore and fallback to emit
  }

  emit('navigate', routeName, params)
}

const handleAddAccount = () => {
  navigateTo('account-add')
}

const accounts = ref([])
const isLoading = ref(false)
const error = ref(null)
const sortBy = ref('account_id')
const sortDirection = ref('asc')

const fetchAccounts = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch('http://localhost:5000/api/accounts')
    
    if (!response.ok) {
      throw new Error(`Failed to fetch accounts: ${response.status}`)
    }
    
    const data = await response.json()
    accounts.value = data
  } catch (err) {
    console.error('Error fetching accounts:', err)
    error.value = 'Failed to load accounts. Please try again.'
  } finally {
    isLoading.value = false
  }
}

// Handle account row click
const handleAccountClick = (account) => {
  navigateTo('portfolio', { accountName: account.account_id })
}

// Handle edit button click
const handleEditAccount = (account, event) => {
  event.stopPropagation() // Prevent row click from triggering
  navigateTo('account-edit', { accountId: account.account_id })
}

// Handle sort click
const handleSort = (column) => {
  if (sortBy.value === column) {
    // Toggle direction if same column
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    // New column, default to ascending
    sortBy.value = column
    sortDirection.value = 'asc'
  }
}

// Compute elapsed days from created_at
const getElapsedDays = (createdAt) => {
  if (!createdAt) return 'N/A'
  
  const createdDate = new Date(createdAt)
  const now = new Date()
  const diffTime = Math.abs(now - createdDate)
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return '1 day'
  return `${diffDays} days`
}

// Get sort icon for column
const getSortIcon = (column) => {
  if (sortBy.value !== column) return '⇅'
  return sortDirection.value === 'asc' ? '↑' : '↓'
}

// Format gain/loss percentage with sign and color
const formatGainLoss = (percentage) => {
  if (percentage === undefined || percentage === null) return '0.00%'
  const sign = percentage >= 0 ? '+' : ''
  return `${sign}${percentage.toFixed(2)}%`
}

// Sort accounts
const sortedAccounts = computed(() => {
  const sorted = [...accounts.value]
  
  sorted.sort((a, b) => {
    let aValue, bValue
    
    if (sortBy.value === 'account_id') {
      aValue = a.account_id
      bValue = b.account_id
    } else if (sortBy.value === 'total_equity') {
      aValue = a.total_equity
      bValue = b.total_equity
    } else if (sortBy.value === 'cash_balance') {
      aValue = a.cash_balance
      bValue = b.cash_balance
    } else if (sortBy.value === 'gain_loss_percentage') {
      aValue = a.gain_loss_percentage || 0
      bValue = b.gain_loss_percentage || 0
    } else if (sortBy.value === 'strategy_name') {
      aValue = a.strategy_name || ''
      bValue = b.strategy_name || ''
    } else if (sortBy.value === 'created_at') {
      aValue = new Date(a.created_at).getTime()
      bValue = new Date(b.created_at).getTime()
    }
    
    if (aValue < bValue) return sortDirection.value === 'asc' ? -1 : 1
    if (aValue > bValue) return sortDirection.value === 'asc' ? 1 : -1
    return 0
  })
  
  return sorted
})

// Watch for navigation params to show success banner
watch(() => props.navigationParams, (newParams) => {
  if (newParams.showSuccess) {
    showSuccessBanner.value = true
    successMessage.value = newParams.successMessage || 'Operation completed successfully!'
  }
}, { immediate: true })

onMounted(() => {
  fetchAccounts()
})

const openGuide = (section) => {
  
  try { window.dispatchEvent(new CustomEvent('open-guide', { detail: { section } })) } catch (e) {}
}
</script>

<template>

    <section id="accounts" class="section">
        

        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading accounts...</p>
        </div>
        
        <div v-else-if="error" class="error-state">
          <p class="error-message">{{ error }}</p>
          <button class="btn btn-gradient btn-small" @click="fetchAccounts">Retry</button>
        </div>
        
        <div v-else-if="accounts.length === 0" class="empty-state">
          <div class="welcome-header">
            <div>
              <h2>Welcome to PaperProfit</h2>
              <p class="lead">Let's get you set up — create an account to start investing and trading.</p>
            </div>
            <button class="btn btn-primary" @click="handleAddAccount">Add Your First Account</button>
          </div>

          <div class="empty-help">
            <h3>Quick start guide</h3>
            <p>If you're new to trading, try to read the guide understand the basics of how investment and trading works. Open any of the sections below to learn more.</p>

            <ul class="guide-links">
              <li><button class="link-button" @click="openGuide('markets')">Markets & exchanges</button></li>
              <li><button class="link-button" @click="openGuide('stocks')">Instruments (stocks, ETFs)</button></li>
              <li><button class="link-button" @click="openGuide('exchanges')">Placing orders — buy & sell</button></li>
              <li><button class="link-button" @click="openGuide('losses')">Risk management & best practices</button></li>
            </ul>

            <h4>Quick steps</h4>
            <ol class="quick-steps">
              <li>Create an account using the button above.</li>
              <li>Edit the account to add an initial cash balance.</li>
              <li>Use the Buy page to place your first order and view your portfolio.</li>
              <li>Create your first strategy and link it to your account.</li>
            </ol>

            <div class="empty-actions">
              <button class="btn btn-primary" @click="handleAddAccount">Add Your First Account</button>
              <button class="btn btn-outline" @click="openGuide('getting-started')">Open Guide</button>
            </div>

            <img src="/images/to-the-moon.png" class="welcome-image" @click="handleAddAccount" alt="Start your journey" />
          </div>
        </div>

        <div v-else class="table-container">
          <div class="section-header">
            <div>
                <h2>Accounts</h2>
                <p>Manage your trading accounts or learn about <a @click="openGuide('investing')">investing.</a></p>
            </div>
            <button class="btn-primary" @click="handleAddAccount">Add Account</button>
         </div>

          <table class="data-table">
            <thead>
              <tr>
                <th class="sortable-header" @click="handleSort('account_id')">
                  <span>Account ID</span>
                  <span class="sort-arrow">{{ getSortIcon('account_id') }}</span>
                </th>
                <th class="sortable-header" @click="handleSort('total_equity')">
                  <span>Total Equity</span>
                  <span class="sort-arrow">{{ getSortIcon('total_equity') }}</span>
                </th>
                <th class="sortable-header" @click="handleSort('cash_balance')">
                  <span>Cash Balance</span>
                  <span class="sort-arrow">{{ getSortIcon('cash_balance') }}</span>
                </th>
                <th class="sortable-header" @click="handleSort('gain_loss_percentage')">
                  <span>% Gain/Loss</span>
                  <span class="sort-arrow">{{ getSortIcon('gain_loss_percentage') }}</span>
                </th>
                <th class="sortable-header" @click="handleSort('strategy_name')">
                  <span>Strategy</span>
                  <span class="sort-arrow">{{ getSortIcon('strategy_name') }}</span>
                </th>
                <th class="sortable-header" @click="handleSort('created_at')">
                  <span>Created</span>
                  <span class="sort-arrow">{{ getSortIcon('created_at') }}</span>
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="account in sortedAccounts" 
                :key="account.account_id" 
                class="clickable-row"
                @click="handleAccountClick(account)"
              >
                <td class="account-id-cell">{{ account.account_id }}</td>
                <td class="equity-cell">${{ account.total_equity?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00' }}</td>
                <td class="balance-cell">${{ account.cash_balance?.toLocaleString() || '0' }}</td>
                <td :class="['gain-loss-cell', { 'positive': (account.gain_loss_percentage || 0) > 0, 'negative': (account.gain_loss_percentage || 0) < 0 }]">
                  {{ formatGainLoss(account.gain_loss_percentage) }}
                </td>
                <td class="strategy-cell">{{ account.strategy_name || 'None' }}</td>
                <td class="created-cell">{{ getElapsedDays(account.created_at) }}</td>
                <td class="actions-cell">
                  <button 
                    class="btn-edit"
                    @click="handleEditAccount(account, $event)"
                  >
                    Edit
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
    </section>

    <!-- Success Banner -->
    <SuccessBanner
      :show="showSuccessBanner"
      :message="successMessage"
      @close="showSuccessBanner = false"
    />

</template>

<style scoped>
  .welcome-header{
    display: flex;
    margin-bottom: 20px;
  }
  .welcome-header button{
    margin-left: auto;
  }

  .actions-cell {
    text-align: center;
  }

  .btn-edit {
    background: #ffc107;
    color: #212529;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    transition: background-color 0.2s;
  }

  .btn-edit:hover {
    background: #e0a800;
  }

  .equity-cell {
    font-weight: 600;
    color: #2e7d32;
  }

  .gain-loss-cell {
    font-weight: 600;
  }

  .gain-loss-cell.positive {
    color: #2e7d32; /* Green for positive */
  }

  .gain-loss-cell.negative {
    color: #c62828; /* Red for negative */
  }

  .welcome-image{
    width:300px;
  }

  /* Empty state help styling */
  .empty-help {
    background: #fff;
    border: 1px solid #eee;
    padding: 1.5rem;
    border-radius: 8px;
    margin-top: 1rem;
    max-width: 920px;
  }

  .empty-help .lead {
    margin: 0.25rem 0 1rem 0;
    color: #222;
    opacity: 0.9;
  }

  .guide-links {
    list-style: none;
    padding: 0;
    margin: 0.5rem 0 1rem 0;
  }

  .guide-links li {
    margin: 0.35rem 0;
  }

  .guide-links a {
    color: #0366d6;
    text-decoration: none;
    font-weight: 600;
  }

  .guide-links a:hover {
    text-decoration: underline;
  }

  .quick-steps {
    margin-left: 1.25rem;
    margin-bottom: 1rem;
  }

  .empty-actions {
    display: flex;
    gap: 0.75rem;
    margin: 0.75rem 0 1rem 0;
  }

  .btn-outline {
    background: transparent;
    border: 1px solid #0366d6;
    color: #0366d6;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .btn-outline:hover { background: #f5faff; }

  .tip {
    margin-top: 0.5rem;
    color: #444;
    font-size: 0.95rem;
  }

  /* Link-like button used for internal guide navigation */
  .link-button {
    background: none;
    border: none;
    color: #0366d6;
    padding: 0;
    font-weight: 600;
    cursor: pointer;
    text-decoration: underline;
  }

  .link-button:hover { opacity: 0.9; }

  .btn-primary{
      height: 4rem;
  }

  .section-header a{
    text-decoration: underline;
    cursor: pointer;
  }
</style>
