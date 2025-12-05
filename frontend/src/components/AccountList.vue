<script setup>
//TODO: This has been moved to welcome page. Remove this??? 

import { ref, onMounted, watch, computed } from 'vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const accounts = ref([])
const isLoading = ref(false)
const error = ref(null)
const showSuccessMessage = ref(false)
const successMessage = ref('')
const sortBy = ref('account_id')
const sortDirection = ref('asc')

const emit = defineEmits(['navigate'])

const handleBack = () => {
  emit('navigate', 'welcome')
}

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

const handleAddAccount = () => {
  emit('navigate', 'account-add')
}

const closeSuccessMessage = () => {
  showSuccessMessage.value = false
  successMessage.value = ''
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

// Sort accounts
const sortedAccounts = computed(() => {
  const sorted = [...accounts.value]
  
  sorted.sort((a, b) => {
    let aValue, bValue
    
    if (sortBy.value === 'account_id') {
      aValue = a.account_id
      bValue = b.account_id
    } else if (sortBy.value === 'cash_balance') {
      aValue = a.cash_balance
      bValue = b.cash_balance
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

// Handle account row click
const handleAccountClick = (account) => {
  emit('navigate', 'portfolio', { accountName: account.account_id })
}

// Handle edit button click
const handleEditAccount = (account, event) => {
  event.stopPropagation() // Prevent row click from triggering
  emit('navigate', 'account-edit', { accountId: account.account_id })
}

// Get sort icon for column
const getSortIcon = (column) => {
  if (sortBy.value !== column) return '↕️'
  return sortDirection.value === 'asc' ? '↑' : '↓'
}

// Watch for navigation params to show success message
watch(() => props.navigationParams, (newParams) => {
  if (newParams.showSuccessMessage && newParams.message) {
    showSuccessMessage.value = true
    successMessage.value = newParams.message
    
    // Auto close after 2 seconds
    setTimeout(() => {
      closeSuccessMessage()
    }, 2000)
  }
}, { immediate: true })

onMounted(() => {
  fetchAccounts()
})
</script>

<template>
  <div class="account-list-page flex-center">
    <div class="card-container">
      <!-- Success Message Banner -->
      <div v-if="showSuccessMessage" class="success-message-banner">
        <div class="success-message-content">
          <span class="success-icon">✓</span>
          <span class="success-text">{{ successMessage }}</span>
        </div>
        <button class="close-button" @click="closeSuccessMessage">×</button>
      </div>
      
      <button class="btn-back" @click="handleBack">← Back</button>
      <div class="actions-section">
        <button class="btn btn-gradient btn-small" @click="handleAddAccount">Add New Account</button>
      </div>
      <br /><br />
      <h1 class="page-header">Your Accounts</h1>
      
      <div class="accounts-section">
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading accounts...</p>
        </div>
        
        <div v-else-if="error" class="error-state">
          <p class="error-message">{{ error }}</p>
          <button class="btn btn-gradient btn-small" @click="fetchAccounts">Retry</button>
        </div>
        
        <div v-else-if="accounts.length === 0" class="empty-state">
          <p class="empty-message">No accounts found</p>
          <button class="btn btn-gradient" @click="handleAddAccount">Add Your First Account</button>
        </div>
        
        <div v-else class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th class="sortable-header" @click="handleSort('account_id')">
                  <span>Account ID</span>
                  <span class="sort-icon">{{ getSortIcon('account_id') }}</span>
                </th>
                <th class="sortable-header" @click="handleSort('cash_balance')">
                  <span>Cash Balance</span>
                  <span class="sort-icon">{{ getSortIcon('cash_balance') }}</span>
                </th>
                <th class="sortable-header" @click="handleSort('created_at')">
                  <span>Created</span>
                  <span class="sort-icon">{{ getSortIcon('created_at') }}</span>
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
                <td class="balance-cell">${{ account.cash_balance?.toLocaleString() || '0' }}</td>
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
      </div>
      
     
    </div>
  </div>
</template>

<style scoped>
.account-list-page {
  min-height: 80vh;
}

.actions-section {
  text-align: center;
  float: right;
}

.account-id-cell {
  font-weight: 600;
  color: #333;
}

.balance-cell {
  font-weight: 600;
  color: #28a745;
}

.created-cell {
  color: #666;
  font-size: 0.9rem;
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
</style>
