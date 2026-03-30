<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { 
  strategyParameters, 
  getParametersByGroup, 
  getAllGroups,
  createEmptyParameters,
  parametersToJson,
  jsonToParameters 
} from '../utils/strategyParameters.js'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const strategyId = ref('')
const strategyName = ref('')
const strategyCategory = ref('')
const selectedStrategy = ref('')
const stockListMode = ref('Manual')
const stockList = ref('')
const stockListAiPrompt = ref('')
const parameters = ref(createEmptyParameters())
const parametersJson = ref('{}')
const activeTab = ref('strategy')
const isLoading = ref(false)
const isSaving = ref(false)
const strategies = ref([])
const loadingStrategies = ref(false)

const emit = defineEmits(['navigate'])

// Get parameter groups for tabs
const parameterGroups = computed(() => getParametersByGroup())
const groupTabs = computed(() => getAllGroups())

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
    //strategyName.value = strategy.strategy
    
    // Set default parameters from YAML configuration
    const defaultParams = strategy.parameters || {}
    // Convert default params to our structured format
    const structuredParams = createEmptyParameters()
    Object.keys(defaultParams).forEach(key => {
      if (key in structuredParams) {
        structuredParams[key] = defaultParams[key]
      }
    })
    parameters.value = structuredParams
    updateJsonFromParameters()
  }
  // When "No Strategy" is selected, keep existing parameters - don't reset them
}

const handleBack = () => {
  emit('navigate', 'strategy-list')
}

// Fetch strategy details
const fetchStrategy = async () => {
  if (!props.navigationParams.strategyId) {
    alert('No strategy ID provided')
    handleBack()
    return
  }

  strategyId.value = props.navigationParams.strategyId
  isLoading.value = true

  try {
    const response = await fetch(`http://localhost:5000/api/strategies/${strategyId.value}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch strategy: ${response.status}`)
    }
    
    const data = await response.json()
    strategyName.value = data.name
    strategyCategory.value = data.category || ''
    selectedStrategy.value = data.strategy_type || ''
    stockListMode.value = data.stock_list_mode || 'Manual'
    stockList.value = data.stock_list || ''
    stockListAiPrompt.value = data.stock_list_ai_prompt || ''
    
    // Handle parameters - they might be stored as string or object
    let parsedParams = {}
    if (typeof data.parameters === 'string') {
      try {
        parsedParams = JSON.parse(data.parameters)
      } catch {
        parsedParams = {}
      }
    } else {
      parsedParams = data.parameters || {}
    }
    
    // Convert to structured parameters
    const structuredParams = createEmptyParameters()
    Object.keys(parsedParams).forEach(key => {
      if (key in structuredParams) {
        structuredParams[key] = parsedParams[key]
      }
    })
    parameters.value = structuredParams
    updateJsonFromParameters()
  } catch (err) {
    console.error('Error fetching strategy:', err)
    alert('Failed to load strategy. Please try again.')
    handleBack()
  } finally {
    isLoading.value = false
  }
}

// Update JSON from parameters object
const updateJsonFromParameters = () => {
  parametersJson.value = parametersToJson(parameters.value)
}

// Update parameters from JSON
const updateParametersFromJson = () => {
  try {
    parameters.value = jsonToParameters(parametersJson.value)
  } catch (error) {
    console.error('Error parsing JSON:', error)
  }
}

// Watch for JSON changes
watch(parametersJson, () => {
  updateParametersFromJson()
})

// Update strategy
const handleUpdateStrategy = async () => {
  if (!strategyName.value.trim()) {
    alert('Please enter a strategy name')
    return
  }

  /*if (!selectedStrategy.value) {
    alert('Please select a strategy type')
    return
  }*/

  isSaving.value = true

  try {
    const response = await fetch(`http://localhost:5000/api/strategies/${strategyId.value}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: strategyName.value,
        category: strategyCategory.value,
        strategy_type: selectedStrategy.value,
        stock_list_mode: stockListMode.value,
        stock_list: stockList.value,
        stock_list_ai_prompt: stockListAiPrompt.value,
        parameters: parameters.value
      })
    })

    if (response.ok) {
      // Navigate to StrategyList and pass success message
      emit('navigate', 'strategy-list', {
        showSuccessMessage: true,
        message: 'Strategy updated successfully!'
      })
    } else {
      throw new Error('Failed to update strategy')
    }
  } catch (error) {
    console.error('Error updating strategy:', error)
    alert('Failed to update strategy. Please try again.')
  } finally {
    isSaving.value = false
  }
}

// Load strategies when component mounts
onMounted(() => {
  loadStrategies()
  fetchStrategy()
})
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>Edit Strategy</h2>
        <p>Modify your trading strategy</p>
      </div>
      <button class="btn-secondary" @click="handleBack">← Back</button>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading strategy...</p>
    </div>
    
    <div v-else class="form-section">

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
        <label for="strategy-category">Strategy Type</label>
        <select 
          id="strategy-category" 
          v-model="strategyCategory"
        >
          <option value="Investing">Investing</option>
          <option value="Trading">Trading</option>
        </select>
      </div>

      <!--<div class="form-group">
        <label for="stock-list-mode">Stock List Mode</label>
        <select 
          id="stock-list-mode" 
          v-model="stockListMode"
        >
          <option value="Manual">Manual</option>
          <option value="AI">AI</option>
        </select>
      </div>-->

      <div class="form-group" v-if="stockListMode === 'Manual'">
        <label for="stock-list">Stock List</label>
        <textarea 
          id="stock-list"
          v-model="stockList"
          placeholder="Enter stock symbols separated by commas (e.g., AAPL, TSLA, MSFT)\n or use Screening/stock universe settings"
          rows="4"
        ></textarea>
      </div>

      <div class="form-group" v-if="stockListMode === 'AI'">
        <label for="stock-list-ai-prompt">AI Prompt for Stock List</label>
        <textarea 
          id="stock-list-ai-prompt"
          v-model="stockListAiPrompt"
           placeholder="Enter stock symbols separated by commas (e.g., AAPL, TSLA, MSFT) 
or use Strategy Parameters: Screening > stock universe settings"          
          rows="4"
        ></textarea>
        <small class="form-help">AI will use this prompt to generate a stock list for your strategy.</small>
      </div>

      <!-- Strategy Template Selection -->
      <div class="form-group">
        <label for="strategy-template">Strategy</label>
        <select 
          id="strategy-template" 
          v-model="selectedStrategy"
          @change="onStrategySelect"
          :disabled="loadingStrategies"
        >
          <option value="">Custom strategy</option>
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

      <!-- Strategy Parameters Tabs -->
      <div class="parameters-section">
        <h3>Strategy Parameters</h3>
        
        <!-- Tab Navigation -->
        <div class="tabs">
          <button
            v-for="group in groupTabs"
            :key="group"
            :class="['tab-button', { active: activeTab === group }]"
            @click="activeTab = group"
          >
            {{ group.charAt(0).toUpperCase() + group.slice(1) }}
          </button>
          <button
            :class="['tab-button', { active: activeTab === 'json' }]"
            @click="activeTab = 'json'"
          >
            JSON View
          </button>
        </div>

        <!-- Tab Content -->
        <div class="tab-content">
          <!-- Parameter Groups -->
          <div v-if="activeTab !== 'json'" class="parameter-group">
            <div v-for="param in parameterGroups[activeTab]" :key="param.name" class="form-group">
              <label :for="param.name">
                {{ param.name.replace(/_/g, ' ') }}
                <span class="param-type">({{ param.type }})</span>
              </label>
              
              <!-- String Input -->
              <input
                v-if="param.type === 'string'"
                :id="param.name"
                v-model="parameters[param.name]"
                type="text"
                :placeholder="`Enter ${param.name.replace(/_/g, ' ')}`"
              >
              
              <!-- Boolean Input -->
              <div v-else-if="param.type === 'boolean'" class="boolean-input">
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    :id="param.name"
                    v-model="parameters[param.name]"
                  >
                  <span>{{ parameters[param.name] ? 'Enabled' : 'Disabled' }}</span>
                </label>
              </div>
              
              <!-- Number/Integer/Percentage Input -->
              <input
                v-else-if="['number', 'integer', 'percentage'].includes(param.type)"
                :id="param.name"
                v-model="parameters[param.name]"
                type="number"
                :step="param.type === 'integer' ? '1' : '0.01'"
                :placeholder="`Enter ${param.name.replace(/_/g, ' ')}`"
              >
              
              <!-- List Input -->
              <textarea
                v-else-if="param.type === 'list'"
                :id="param.name"
                v-model="parameters[param.name]"
                :placeholder="`Enter ${param.name.replace(/_/g, ' ')} separated by commas`"
                rows="3"
              ></textarea>
              
              <small class="form-help">
                {{ param.description }}
                <span v-if="param.typical_values" class="typical-values">
                  Typical values: {{ param.typical_values }}
                </span>
              </small>
            </div>
          </div>

          <!-- JSON View -->
          <div v-if="activeTab === 'json'" class="json-view">
            <div class="form-group">
              <label for="parameters-json">Parameters (JSON)</label>
              <textarea 
                id="parameters-json"
                v-model="parametersJson"
                placeholder='Strategy parameters in JSON format'
                rows="12"
              ></textarea>
              <small class="form-help">
                Edit parameters directly in JSON format. Changes will be reflected in the form tabs.
              </small>
            </div>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button 
          class="btn-primary" 
          @click="handleUpdateStrategy"
          :disabled="isSaving"
        >
          {{ isSaving ? 'Updating...' : 'Update Strategy' }}
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

.parameters-section {
  margin-top: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 1.5rem;
  background: #f8f9fa;
}

.parameters-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #495057;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #dee2e6;
  padding-bottom: 0.5rem;
}

.tab-button {
  padding: 0.5rem 1rem;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 4px 4px 0 0;
  cursor: pointer;
  font-size: 0.9rem;
  color: #495057;
  transition: all 0.2s;
}

.tab-button:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.tab-button.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.tab-content {
  min-height: 300px;
}

.parameter-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.param-type {
  font-size: 0.8rem;
  color: #6c757d;
  font-weight: normal;
  margin-left: 0.5rem;
}

.boolean-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.typical-values {
  display: block;
  color: #28a745;
  font-style: italic;
  margin-top: 0.25rem;
}

.json-view textarea {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .form-actions {
    flex-direction: column;
  }
  
  .parameter-group {
    grid-template-columns: 1fr;
  }
  
  .tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
  }
  
  .tab-button {
    white-space: nowrap;
  }
}
</style>
