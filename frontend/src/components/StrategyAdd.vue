<script setup>
import { ref, onMounted } from 'vue'

const strategyName = ref('')
const selectedStrategy = ref('')
const stockListMode = ref('Manual')
const stockList = ref('')
const stockListAiPrompt = ref('')
const parametersJson = ref('{}')
const isLoading = ref(false)
const strategies = ref([])
const loadingStrategies = ref(false)

const emit = defineEmits(['navigate'])

// Load available strategies from the API
const loadStrategies = async () => {
  loadingStrategies.value = true
  try {
    const response = await fetch('http://localhost:5000/api/strategy-list')
    if (response.ok) {
      strategies.value = await response.json()
    } else {
      console.error('Failed to load strategies')
    }
  } catch (error) {
    console.error('Error loading strategies:', error)
  } finally {
    loadingStrategies.value = false
  }
}

// When a strategy is selected, auto-fill the form
const onStrategySelect = () => {
  const strategy = strategies.value.find(s => s.index === selectedStrategy.value)
  if (strategy) {
    // Auto-fill the form with strategy details
    strategyName.value = strategy.strategy
    //category.value = strategy.category
    
    // Set default parameters from YAML configuration
    const defaultParams = strategy.parameters || {}
    parametersJson.value = JSON.stringify(defaultParams, null, 2)
  }
}

const handleBack = () => {
  emit('navigate', 'strategy-list')
}

const handleAddStrategy = async () => {
  if (!strategyName.value.trim()) {
    alert('Please enter a strategy name')
    return
  }

  if (!selectedStrategy.value) {
    alert('Please select a strategy type')
    return
  }

  // Validate JSON parameters
  try {
    if (parametersJson.value.trim()) {
      JSON.parse(parametersJson.value)
    }
  } catch (error) {
    alert('Invalid JSON format in Parameters field. Please check your JSON syntax.')
    return
  }

  isLoading.value = true

  try {
    const response = await fetch('http://localhost:5000/api/strategies', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: strategyName.value,
        strategy_type: selectedStrategy.value,
        stock_list_mode: stockListMode.value,
        stock_list: stockList.value,
        stock_list_ai_prompt: stockListAiPrompt.value,
        parameters: parametersJson.value.trim() ? JSON.parse(parametersJson.value) : {}
      })
    })

    if (response.ok) {
      // Navigate to StrategyList and pass success message
      emit('navigate', 'strategy-list', {
        showSuccessMessage: true,
        message: 'Strategy added successfully!'
      })
    } else {
      throw new Error('Failed to add strategy')
    }
  } catch (error) {
    console.error('Error adding strategy:', error)
    alert('Failed to add strategy. Please try again.')
  } finally {
    isLoading.value = false
  }
}

// Load strategies when component mounts
onMounted(() => {
  loadStrategies()
})
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>Add Strategy</h2>
        <p>Create a new trading strategy</p>
      </div>
      <button class="btn-secondary" @click="handleBack">← Back</button>
    </div>

    <div class="form-section">
      <!-- Strategy Template Selection -->
      <div class="form-group">
        <label for="strategy-template">Strategy</label>
        <select 
          id="strategy-template" 
          v-model="selectedStrategy"
          @change="onStrategySelect"
          :disabled="loadingStrategies"
        >
          <option value="">Select a strategy</option>
          <optgroup v-for="category in ['Long Term', 'Swing Trading', 'Day Trading', 'Greatest Investors', 'Options']" :key="category" :label="category">
            <option 
              v-for="strategy in strategies.filter(s => s.category === category)" 
              :key="strategy.index" 
              :value="strategy.index"
            >
              {{ strategy.strategy }} - {{ strategy.short_description }}
            </option>
          </optgroup>
        </select>
        <small class="form-help" v-if="loadingStrategies">Loading strategies...</small>
      </div>

      <!-- Strategy Details -->
      <div class="strategy-details" v-if="selectedStrategy">
        <div class="strategy-info">
          <h4>Strategy Information</h4>
          <div class="info-grid">
            <div v-for="strategy in strategies.filter(s => s.index === selectedStrategy)" :key="strategy.index">
              <div><strong>Category:</strong> {{ strategy.category }}</div>
              <div><strong>Risk Level:</strong> {{ strategy.risk }}</div>
              <div><strong>Timeframe:</strong> {{ strategy.timeframe }}</div>
              <div><strong>Indicators:</strong> {{ strategy.indicators }}</div>
              <div><strong>Entry Rules:</strong> {{ strategy.entry_rules }}</div>
              <div><strong>Exit Rules:</strong> {{ strategy.exit_rules }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="form-group">
        <label for="strategy-name">Strategy Name</label>
        <input 
          id="strategy-name"
          v-model="strategyName"
          type="text" 
          placeholder="Enter strategy name"
        >
      </div>

      <div class="form-group">
        <label for="stock-list-mode">Stock List Mode</label>
        <select 
          id="stock-list-mode" 
          v-model="stockListMode"
        >
          <option value="Manual">Manual</option>
          <option value="AI">AI</option>
        </select>
      </div>

      <div class="form-group" v-if="stockListMode === 'Manual'">
        <label for="stock-list">Stock List</label>
        <textarea 
          id="stock-list"
          v-model="stockList"
          placeholder="Enter stock symbols separated by commas (e.g., AAPL, TSLA, MSFT)"
          rows="4"
        ></textarea>
      </div>

      <div class="form-group" v-if="stockListMode === 'AI'">
        <label for="stock-list-ai-prompt">AI Prompt for Stock List</label>
        <textarea 
          id="stock-list-ai-prompt"
          v-model="stockListAiPrompt"
          placeholder="Enter a prompt for AI to generate stock list (e.g., 'Find me tech stocks with strong growth potential')"
          rows="4"
        ></textarea>
        <small class="form-help">AI will use this prompt to generate a stock list for your strategy.</small>
      </div>

      <div class="form-group">
        <label for="parameters-json">Parameters (JSON)</label>
        <textarea 
          id="parameters-json"
          v-model="parametersJson"
          placeholder='Strategy parameters will be auto-filled when you select a template'
          rows="8"
        ></textarea>
        <small class="form-help">Strategy parameters in JSON format. These will be auto-filled when you select a template.</small>
      </div>

      <div class="form-actions">
        <button 
          class="btn-primary" 
          @click="handleAddStrategy"
          :disabled="isLoading"
        >
          {{ isLoading ? 'Adding...' : 'Add Strategy' }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.form-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-top: 2rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
  font-family: monospace;
  font-size: 0.9rem;
}

.form-help {
  color: #666;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.form-actions {
  margin-top: 2rem;
}

.strategy-details {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.strategy-info h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: #495057;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 0.5rem;
  font-size: 0.9rem;
}

.info-grid div {
  margin-bottom: 0.25rem;
}

.info-grid strong {
  color: #495057;
}

optgroup {
  font-weight: bold;
}

optgroup option {
  font-weight: normal;
  padding-left: 1rem;
}
</style>
