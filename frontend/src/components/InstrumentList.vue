<script setup>
import { ref, onMounted, watch, computed } from 'vue'

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
const showAddModal = ref(false)
const newSymbol = ref('')

const winners = ref([])
const losers = ref([])
const watchList = ref([])
const watchlistStatus = ref({}) // Track watchlist status for winners/losers

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
      volume: item.volume || 'N/A',
      inWatchlist: false // Will be updated after fetching watchlist status
    }))
    
    // Check watchlist status for each winner
    await updateWatchlistStatusForInstruments(winners.value)
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
      volume: item.volume || 'N/A',
      inWatchlist: false // Will be updated after fetching watchlist status
    }))
    
    // Check watchlist status for each loser
    await updateWatchlistStatusForInstruments(losers.value)
  } catch (err) {
    console.error('Error fetching losers:', err)
    error.value = 'Failed to load losers data. Please try again.'
    
  } finally {
    isLoading.value = false
  }
}

const fetchWatchlist = async () => {
  isLoading.value = true
  error.value = null
  try {
    const response = await fetch('http://localhost:5000/api/watchlist')
    if (!response.ok) {
      throw new Error(`Failed to fetch watchlist: ${response.status}`)
    }
    const data = await response.json()
    // Transform API data to match frontend format
    watchList.value = data.map(item => ({
      id: item.id,
      symbol: item.symbol,
      name: item.name || item.symbol,
      price: item.current_price || 0,
      change: 0, // We don't have change data in watchlist API
      added: new Date(item.created_at).toLocaleDateString(),
      exchange: item.exchange || '—',
      currency: item.currency || 'USD',
      sector: item.sector || '—',
      overall_score: item.overall_score,
      risk_score: item.risk_score
    }))
  } catch (err) {
    console.error('Error fetching watchlist:', err)
    error.value = 'Failed to load watchlist data. Please try again.'
    
  } finally {
    isLoading.value = false
  }
}

const updateWatchlistStatusForInstruments = async (instruments) => {
  for (const instrument of instruments) {
    try {
      const response = await fetch(`http://localhost:5000/api/watchlist/${instrument.symbol}/status`)
      if (response.ok) {
        const data = await response.json()
        instrument.inWatchlist = data.in_watchlist
        watchlistStatus.value[instrument.symbol] = data.in_watchlist
      }
    } catch (err) {
      console.error(`Error checking watchlist status for ${instrument.symbol}:`, err)
      instrument.inWatchlist = false
      watchlistStatus.value[instrument.symbol] = false
    }
  }
}

const addToWatchlist = async (symbol) => {
  try {
    const response = await fetch(`http://localhost:5000/api/watchlist/${symbol}`, {
      method: 'POST'
    })
    
    if (!response.ok) {
      throw new Error(`Failed to add ${symbol} to watchlist: ${response.status}`)
    }
    
    const data = await response.json()
    console.log(`Added ${symbol} to watchlist:`, data)
    
    // Update watchlist status
    watchlistStatus.value[symbol] = true
    
    // Update inWatchlist property for current tab
    if (activeTab.value === 'winners') {
      const winner = winners.value.find(w => w.symbol === symbol)
      if (winner) winner.inWatchlist = true
    } else if (activeTab.value === 'losers') {
      const loser = losers.value.find(l => l.symbol === symbol)
      if (loser) loser.inWatchlist = true
    }
    
    // Refresh watchlist if we're on the watchlist tab
    if (activeTab.value === 'watchlist') {
      await fetchWatchlist()
    }
    
    return true
  } catch (err) {
    console.error(`Error adding ${symbol} to watchlist:`, err)
    error.value = `Failed to add ${symbol} to watchlist. Please try again.`
    return false
  }
}

const removeFromWatchlist = async (symbol) => {
  try {
    const response = await fetch(`http://localhost:5000/api/watchlist/${symbol}`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      throw new Error(`Failed to remove ${symbol} from watchlist: ${response.status}`)
    }
    
    const data = await response.json()
    console.log(`Removed ${symbol} from watchlist:`, data)
    
    // Update watchlist status
    watchlistStatus.value[symbol] = false
    
    // Update inWatchlist property for current tab
    if (activeTab.value === 'winners') {
      const winner = winners.value.find(w => w.symbol === symbol)
      if (winner) winner.inWatchlist = false
    } else if (activeTab.value === 'losers') {
      const loser = losers.value.find(l => l.symbol === symbol)
      if (loser) loser.inWatchlist = false
    }
    
    // Refresh watchlist if we're on the watchlist tab
    if (activeTab.value === 'watchlist') {
      await fetchWatchlist()
    }
    
    return true
  } catch (err) {
    console.error(`Error removing ${symbol} from watchlist:`, err)
    error.value = `Failed to remove ${symbol} from watchlist. Please try again.`
    return false
  }
}

const handleAddToWatchlist = async (symbol) => {
  const success = await addToWatchlist(symbol)
  if (success) {
    // Show success message or update UI
    console.log(`Successfully added ${symbol} to watchlist`)
  }
}

const handleRemoveFromWatchlist = async (symbol) => {
  const success = await removeFromWatchlist(symbol)
  if (success) {
    // Show success message or update UI
    console.log(`Successfully removed ${symbol} from watchlist`)
  }
}

const openAddModal = () => {
  showAddModal.value = true
  newSymbol.value = ''
}

const closeAddModal = () => {
  showAddModal.value = false
  newSymbol.value = ''
}

const handleAddNewSymbol = async () => {
  if (!newSymbol.value.trim()) {
    error.value = 'Please enter a symbol'
    return
  }
  
  const symbol = newSymbol.value.trim().toUpperCase()
  const success = await addToWatchlist(symbol)
  
  if (success) {
    closeAddModal()
    // Refresh watchlist
    await fetchWatchlist()
  }
}

const fetchData = () => {
  if (activeTab.value === 'winners') {
    fetchWinners()
  } else if (activeTab.value === 'losers') {
    fetchLosers()
  } else if (activeTab.value === 'watchlist') {
    fetchWatchlist()
  }
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
      <button 
        :class="['tab', { active: activeTab === 'watchlist' }]" 
        @click="activeTab = 'watchlist'"
      >
        WatchList
      </button>
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
                    <button 
                      v-if="!instrument.inWatchlist"
                      class="watchlist-btn"
                      @click="handleAddToWatchlist(instrument.symbol)"
                      title="Add to Watchlist"
                    >
                      +
                    </button>
                    <button 
                      v-else
                      class="watchlist-btn active"
                      @click="handleRemoveFromWatchlist(instrument.symbol)"
                      title="Remove from Watchlist"
                    >
                      ✓
                    </button>
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
                    <button 
                      v-if="!instrument.inWatchlist"
                      class="watchlist-btn"
                      @click="handleAddToWatchlist(instrument.symbol)"
                      title="Add to Watchlist"
                    >
                      +
                    </button>
                    <button 
                      v-else
                      class="watchlist-btn active"
                      @click="handleRemoveFromWatchlist(instrument.symbol)"
                      title="Remove from Watchlist"
                    >
                      ✓
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- WatchList Tab -->
      <div v-if="activeTab === 'watchlist'" class="tab-pane">
        <div v-if="watchList.length === 0 && !isLoading" class="empty-state">
          <p>Your watchlist is empty. Add stocks to track them here.</p>
        </div>
        
        <div v-if="watchList.length > 0" class="table-container">
          <table class="instrument-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Price</th>
                <th>Sector</th>
                <th>Score</th>
                <th>Risk</th>
                <th>Exchange</th>
                <th>Added</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="instrument in watchList" :key="instrument.symbol">
                <td class="symbol">{{ instrument.symbol }}</td>
                <td class="name">{{ instrument.name }}</td>
                <td class="price">${{ instrument.price.toFixed(2) }}</td>
                <td class="sector">{{ instrument.sector }}</td>
                <td class="score">
                  <span v-if="instrument.overall_score != null" class="score-badge">
                    {{ instrument.overall_score }}/100
                  </span>
                  <span v-else class="score-na">—</span>
                </td>
                <td class="score">
                  <span v-if="instrument.risk_score != null" class="score-badge risk">
                    {{ instrument.risk_score }}/100
                  </span>
                  <span v-else class="score-na">—</span>
                </td>
                <td class="exchange">{{ instrument.exchange }}</td>
                <td class="added">{{ instrument.added }}</td>
                <td class="action">
                  <button class="view-btn" @click="navigateToInstrument(instrument.symbol)">View</button>
                  <button
                    class="remove-btn"
                    @click="handleRemoveFromWatchlist(instrument.symbol)"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="watchlist-actions">
          <button class="add-btn" @click="openAddModal">Add to WatchList</button>
        </div>
        
        <!-- Add Symbol Modal -->
        <div v-if="showAddModal" class="modal-overlay">
          <div class="modal">
            <div class="modal-header">
              <h3>Add Symbol to Watchlist</h3>
              <button class="modal-close" @click="closeAddModal">×</button>
            </div>
            <div class="modal-body">
              <div class="form-group">
                <label for="symbol">Stock Symbol</label>
                <input 
                  type="text" 
                  id="symbol" 
                  v-model="newSymbol" 
                  placeholder="e.g., AAPL, TSLA, MSFT"
                  @keyup.enter="handleAddNewSymbol"
                />
                <p class="form-hint">Enter the stock symbol (ticker) you want to add to your watchlist.</p>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-secondary" @click="closeAddModal">Cancel</button>
              <button class="btn-primary" @click="handleAddNewSymbol">Add to Watchlist</button>
            </div>
          </div>
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

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  font-size: 1.2rem;
  color: #666;
  text-align: center;
  padding: 2rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px dashed #e0e0e0;
}

.watchlist-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid #e0e0e0;
  background-color: white;
  color: #666;
  font-size: 1.2rem;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.watchlist-btn:hover {
  background-color: #f3f4f6;
  border-color: #d1d5db;
}

.watchlist-btn.active {
  background-color: #10b981;
  color: white;
  border-color: #10b981;
}

.watchlist-btn.active:hover {
  background-color: #059669;
  border-color: #059669;
}

.exchange {
  color: #666;
}

.sector {
  color: #555;
  font-size: 0.85rem;
}

.score-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background-color: #dbeafe;
  color: #1d4ed8;
  font-size: 0.8rem;
  font-weight: 600;
}

.score-badge.risk {
  background-color: #d1fae5;
  color: #065f46;
}

.score-na {
  color: #aaa;
  font-size: 0.85rem;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background-color: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.modal-close:hover {
  background-color: #f3f4f6;
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-hint {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #666;
}

.btn-primary, .btn-secondary {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  border: none;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: #10b981;
  color: white;
}

.btn-primary:hover {
  background-color: #059669;
}

.btn-secondary {
  background-color: #f3f4f6;
  color: #333;
}

.btn-secondary:hover {
  background-color: #e5e7eb;
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
  
  .view-btn, .remove-btn, .watchlist-btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
  }
  
  .watchlist-btn {
    width: 28px;
    height: 28px;
    font-size: 1rem;
  }
  
  .modal {
    width: 95%;
    margin: 1rem;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }
}
</style>