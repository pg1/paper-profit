<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import SuccessBanner from './ui/SuccessBanner.vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const strategies = ref([])
const isLoading = ref(false)
const error = ref(null)
const showSuccessMessage = ref(false)
const successMessage = ref('')
const sortBy = ref('id')
const sortDirection = ref('asc')

const emit = defineEmits(['navigate'])

const openGuide = (section) => {  
  try { window.dispatchEvent(new CustomEvent('open-guide', { detail: { section } })) } catch (e) {}
}

const fetchStrategies = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch('http://localhost:5000/api/strategies')
    
    if (!response.ok) {
      throw new Error(`Failed to fetch strategies: ${response.status}`)
    }
    
    const data = await response.json()
    strategies.value = data
  } catch (err) {
    console.error('Error fetching strategies:', err)
    error.value = 'Failed to load strategies. Please try again.'
  } finally {
    isLoading.value = false
  }
}

const handleAddStrategy = () => {
  emit('navigate', 'strategy-add')
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
  if (diffDays === 1) return '1 day ago'
  return `${diffDays} days ago`
}

// Sort strategies
const sortedStrategies = computed(() => {
  const sorted = [...strategies.value]
  
  sorted.sort((a, b) => {
    let aValue, bValue
    
    if (sortBy.value === 'id') {
      aValue = a.id
      bValue = b.id
    } else if (sortBy.value === 'name') {
      aValue = a.name
      bValue = b.name
    } else if (sortBy.value === 'strategy_type') {
      aValue = a.strategy_type
      bValue = b.strategy_type
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

// Handle strategy row click
const handleStrategyClick = (strategy) => {
  emit('navigate', 'strategy-edit', { strategyId: strategy.id })
}

// Get sort icon for column
const getSortIcon = (column) => {
  if (sortBy.value !== column) return '⇅'
  return sortDirection.value === 'asc' ? '↑' : '↓'
}

// Watch for navigation params to show success message and refresh data
watch(() => props.navigationParams, (newParams) => {
  if (newParams.showSuccessMessage && newParams.message) {
    showSuccessMessage.value = true
    successMessage.value = newParams.message
    
    // Refresh strategies list after successful operations
    fetchStrategies()
  }
}, { immediate: true })

onMounted(() => {
  fetchStrategies()
})
</script>

<template>
  <section class="section">
    <!-- Success Banner -->
    <SuccessBanner
      :show="showSuccessMessage"
      :message="successMessage"
      :duration="2000"
      @close="closeSuccessMessage"
    />
    
    <div class="section-header">
      <div>
        <h2>Your Strategies</h2>
        <p>Manage your trading strategies</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="openGuide('strategy')">Learn</button>
        <button class="btn-primary" @click="handleAddStrategy">Add New Strategy</button>
      </div>
    </div>

    <div class="strategies-section">
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Loading strategies...</p>
      </div>
      
      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button class="btn btn-primary" @click="fetchStrategies">Retry</button>
      </div>
      
      <div v-else-if="strategies.length === 0" class="empty-state">
        <p class="empty-message">No strategies found</p>
        <button class="btn btn-primary" @click="handleAddStrategy">Add Your First Strategy</button>
      </div>
      
      <div v-else class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th class="sortable-header" @click="handleSort('id')">
                <span>Strategy ID</span>
                <span class="sort-arrow">{{ getSortIcon('id') }}</span>
              </th>
              <th class="sortable-header" @click="handleSort('name')">
                <span>Name</span>
                <span class="sort-arrow">{{ getSortIcon('name') }}</span>
              </th>
              <th class="sortable-header" @click="handleSort('created_at')">
                <span>Created</span>
                <span class="sort-arrow">{{ getSortIcon('created_at') }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="strategy in sortedStrategies" 
              :key="strategy.id" 
              class="clickable-row"
              @click="handleStrategyClick(strategy)"
            >
              <td class="strategy-id-cell">{{ strategy.id }}</td>
              <td class="name-cell">{{ strategy.name }}</td>
              <td class="created-cell">{{ getElapsedDays(strategy.created_at) }}</td>
            </tr>
          </tbody>
        </table>
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

.strategies-section {
  margin: 2rem 0;
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

.strategy-id-cell {
  font-weight: 600;
  color: #000000;
}

.name-cell {
  font-weight: 600;
  color: #000000;
}

.type-cell {
  color: #000000;
  opacity: 0.8;
  font-weight: 500;
}

.created-cell {
  color: #000000;
  opacity: 0.8;
  font-size: 0.9rem;
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
  
  .data-table {
    font-size: 0.9rem;
  }
}
</style>
