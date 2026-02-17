<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['navigate'])

const activeTab = ref('winners')
const isLoading = ref(false)
const error = ref(null)

const winners = ref([])
const losers = ref([])
const watchList = ref([
  { symbol: 'AAPL', name: 'Apple Inc.', price: 185.25, change: '+3.45%', added: '2024-01-15' },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 415.86, change: '+2.87%', added: '2024-01-10' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 152.34, change: '+2.15%', added: '2024-01-05' }
])

const handleNavigation = (page, params = {}) => {
  emit('navigate', page, params)
}

const navigateToInstrument = (symbol) => {
  handleNavigation('instrument-detail', { symbol })
}

const fetchWinners = async () => {
  isLoading.value = true
  error.value = null
  try {
    const response = await fetch('http://localhost:5000/api/instruments/list/winners?limit=20')
    if (!response.ok) {
      throw new Error(`Failed to fetch winners: ${response.status}`)
    }
    const data = await response.json()
    // Transform API data to match frontend format
    winners.value = data.map(item => ({
      symbol: item.symbol,
      name: item.name || item.symbol,
      price: item.price || 0,
      change: item.change_percent || 0,
      volume: item.volume || 'N/A'
    }))
  } catch (err) {
    console.error('Error fetching winners:', err)
    error.value = 'Failed to load winners data. Please try again.'
    
  } finally {
    isLoading.value = false
  }
}

const fetchLosers = async () => {
  isLoading.value = true
  error.value = null
  try {
    const response = await fetch('http://localhost:5000/api/instruments/list/losers?limit=20')
    if (!response.ok) {
      throw new Error(`Failed to fetch losers: ${response.status}`)
    }
    const data = await response.json()
    // Transform API data to match frontend format
    losers.value = data.map(item => ({
      symbol: item.symbol,
      name: item.name || item.symbol,
      price: item.price || 0,
      change: item.change_percent || 0,
      volume: item.volume || 'N/A'
    }))
  } catch (err) {
    console.error('Error fetching losers:', err)
    error.value = 'Failed to load losers data. Please try again.'
    
  } finally {
    isLoading.value = false
  }
}

const fetchData = () => {
  if (activeTab.value === 'winners') {
    fetchWinners()
  } else if (activeTab.value === 'losers') {
    fetchLosers()
  }
  // Watchlist remains as placeholder for now
}

// Watch for tab changes to fetch appropriate data
watch(activeTab, () => {
  fetchData()
})

// Initial data fetch
onMounted(() => {
  fetchData()
})
</script>

<template>
    
    <!-- Tabs Navigation -->
    <div class="tabs">
      <button 
        :class="['tab', { active: activeTab === 'winners' }]" 
        @click="activeTab = 'winners'"
      >
        Winners
      </button>
      <button 
        :class="['tab', { active: activeTab === 'losers' }]" 
        @click="activeTab = 'losers'"
      >
        Losers
      </button>
      <!--<button 
        :class="['tab', { active: activeTab === 'watchlist' }]" 
        @click="activeTab = 'watchlist'"
      >
        WatchList
      </button>-->
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <!-- Loading and Error States -->
      <div v-if="isLoading" class="loading-state">
        <p>Loading data...</p>
      </div>
      
      <div v-if="error && !isLoading" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button class="retry-btn" @click="fetchData">Retry</button>
      </div>

      <!-- Winners Tab -->
      <div v-if="activeTab === 'winners' && !isLoading" class="tab-pane">
        <section class="section">
          <div class="section-header">
            <div>
              <h2>Market Movers</h2>
              <p>A list of the stocks with the highest percentage gain today.</p>
            </div>
          </div>

          <div class="table-container">
            <table class="instrument-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Name</th>
                  <th>Price</th>
                  <th>Change</th>
                  <th>Volume</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="instrument in winners" :key="instrument.symbol">
                  <td class="symbol">{{ instrument.symbol }}</td>
                  <td class="name">{{ instrument.name }}</td>
                  <td class="price">${{ instrument.price.toFixed(2) }}</td>
                  <td class="change positive">{{ instrument.change.toFixed(2)  }}%</td>
                  <td class="volume">{{ instrument.volume }}</td>
                  <td class="action">
                    <button class="view-btn" @click="navigateToInstrument(instrument.symbol)">View</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- Losers Tab -->
      <div v-if="activeTab === 'losers' && !isLoading" class="tab-pane">
        <section class="section">
          <div class="section-header">
            <div>
              <h2>Market Movers</h2>
              <p>A list of the stocks with the highest percentage decrease today.</p>
            </div>
          </div>
          <div class="table-container">
            <table class="instrument-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Name</th>
                  <th>Price</th>
                  <th>Change</th>
                  <th>Volume</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="instrument in losers" :key="instrument.symbol">
                  <td class="symbol">{{ instrument.symbol }}</td>
                  <td class="name">{{ instrument.name }}</td>
                  <td class="price">${{ instrument.price.toFixed(2) }}</td>
                  <td class="change negative">{{ instrument.change.toFixed(2) }}%</td>
                  <td class="volume">{{ instrument.volume }}</td>
                  <td class="action">
                    <button class="view-btn" @click="navigateToInstrument(instrument.symbol)">View</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- WatchList Tab -->
      <div v-if="activeTab === 'watchlist'" class="tab-pane">
        <div class="table-container">
          <table class="instrument-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Price</th>
                <th>Change</th>
                <th>Added</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="instrument in watchList" :key="instrument.symbol">
                <td class="symbol">{{ instrument.symbol }}</td>
                <td class="name">{{ instrument.name }}</td>
                <td class="price">${{ instrument.price.toFixed(2) }}</td>
                <td class="change positive">{{ instrument.change }}</td>
                <td class="added">{{ instrument.added }}</td>
                <td class="action">
                  <button class="view-btn" @click="navigateToInstrument(instrument.symbol)">View</button>
                  <button class="remove-btn">Remove</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="watchlist-actions">
          <button class="add-btn">Add to WatchList</button>
        </div>
      </div>
    </div>
</template>

<style scoped>

h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  color: #333;
}

.subtitle {
  color: #666;
  margin-bottom: 2rem;
  font-size: 1.1rem;
}

.section-header{
    margin-bottom: 2rem;
}

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
  min-height: 400px;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  font-size: 1.2rem;
  color: #666;
}

.error-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  padding: 2rem;
  text-align: center;
}

.error-message {
  color: #ef4444;
  margin-bottom: 1rem;
  font-size: 1.1rem;
}

.retry-btn {
  padding: 0.5rem 1.5rem;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.retry-btn:hover {
  background-color: #2563eb;
}

.table-container {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.instrument-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.instrument-table th {
  background-color: #f8f9fa;
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
}

.instrument-table td {
  padding: 1rem;
  border-bottom: 1px solid #f0f0f0;
}

.instrument-table tr:hover {
  background-color: #f8f9fa;
}

.instrument-table tr:last-child td {
  border-bottom: none;
}

.symbol {
  font-weight: 600;
  color: #333;
}

.name {
  color: #666;
}

.price {
  font-weight: 600;
  color: #333;
}

.change.positive {
  color: #10b981;
  font-weight: 600;
}

.change.negative {
  color: #ef4444;
  font-weight: 600;
}

.volume, .added {
  color: #666;
}

.action {
  display: flex;
  gap: 0.5rem;
}

.view-btn, .remove-btn, .add-btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.view-btn {
  background-color: #3b82f6;
  color: white;
}

.view-btn:hover {
  background-color: #2563eb;
}

.remove-btn {
  background-color: #f3f4f6;
  color: #666;
}

.remove-btn:hover {
  background-color: #e5e7eb;
  color: #333;
}

.watchlist-actions {
  margin-top: 2rem;
  display: flex;
  justify-content: flex-end;
}

.add-btn {
  background-color: #10b981;
  color: white;
  padding: 0.75rem 1.5rem;
}

.add-btn:hover {
  background-color: #059669;
}

@media (max-width: 768px) {
  .instrument-list-container {
    padding: 1rem;
  }
  
  .tab {
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
  }
  
  .tab-pane {
    padding: 1rem 0;
  }
  
  .instrument-table th,
  .instrument-table td {
    padding: 0.75rem 0.5rem;
    font-size: 0.9rem;
  }
  
  .action {
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .view-btn, .remove-btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
  }
}
</style>