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

const strategyName = ref('')
const strategyCategory = ref('Trading')
const selectedStrategy = ref('')
const stockListMode = ref('Manual')
const stockList = ref('')
const stockListAiPrompt = ref('')
const parameters = ref(createEmptyParameters())
const parametersJson = ref('{}')
const activeTab = ref('strategy')
const strategyTab = ref('general')
const isLoading = ref(false)
const strategies = ref([])
const loadingStrategies = ref(false)

const emit = defineEmits(['navigate'])

// Get parameter groups for tabs
const parameterGroups = computed(() => getParametersByGroup())
const groupTabs = computed(() => getAllGroups())

// Condition builder logic
const nextConditionId = ref(2) // Start from 2 since we have one default condition

// Indicator definitions (similar to HTML file but simplified)
const INDICATORS = [
  { id: 'RSI', label: 'RSI', hasPeriod: true, defaultPeriod: 14, valueType: 'number', valuePlaceholder: '30' },
  { id: 'EMA', label: 'EMA', hasPeriod: true, defaultPeriod: 10, valueType: 'number', valuePlaceholder: '200' },
  { id: 'SMA', label: 'SMA', hasPeriod: true, defaultPeriod: 20, valueType: 'number', valuePlaceholder: '50' },
  { id: 'MACD', label: 'MACD', hasPeriod: false, valueType: 'select', options: ['crossover_up', 'crossover_down', 'above_signal', 'below_signal'] },
  { id: 'BB_UPPER', label: 'BB upper', hasPeriod: true, defaultPeriod: 20, valueType: 'price', valuePlaceholder: 'price' },
  { id: 'BB_LOWER', label: 'BB lower', hasPeriod: true, defaultPeriod: 20, valueType: 'price', valuePlaceholder: 'price' },
  { id: 'STOCH', label: 'Stochastic', hasPeriod: true, defaultPeriod: 14, valueType: 'number', valuePlaceholder: '20' },
  { id: 'ATR', label: 'ATR', hasPeriod: true, defaultPeriod: 14, valueType: 'number', valuePlaceholder: '2' },
  { id: 'VOLUME', label: 'Volume', hasPeriod: false, valueType: 'multiplier', valuePlaceholder: '1.5x avg' },
  { id: 'CLOSE', label: 'Close price', hasPeriod: false, valueType: 'price', valuePlaceholder: '100' },
]

const OPS_NUMBER = ['>', '<', '>=', '<=', '=', 'crosses_above', 'crosses_below']
const OPS_SELECT = ['=']

// Add a new condition
const addCondition = () => {
  parameters.value.entryConditions.push({
    id: nextConditionId.value++,
    indicator: 'RSI',
    period: 14,
    op: '>',
    value: '30',
    logic: 'AND'
  })
}

// Remove a condition
const removeCondition = (id) => {
  parameters.value.entryConditions = parameters.value.entryConditions.filter(c => c.id !== id)
}

// Update a field in a condition
const updateConditionField = (id, field, value) => {
  const condition = parameters.value.entryConditions.find(c => c.id === id)
  if (!condition) return
  
  condition[field] = value
  
  // If indicator changed, update period and value defaults
  if (field === 'indicator') {
    const meta = INDICATORS.find(i => i.id === value)
    if (meta) {
      condition.period = meta.defaultPeriod || ''
      condition.value = meta.options ? meta.options[0] : ''
      condition.op = meta.valueType === 'select' ? '=' : '>'
    }
  }
}

// Toggle logic between AND/OR
const toggleLogic = (id) => {
  const condition = parameters.value.entryConditions.find(c => c.id === id)
  if (condition) {
    condition.logic = condition.logic === 'AND' ? 'OR' : 'AND'
  }
}

// Get available operators for a condition
const getAvailableOperators = (indicatorId) => {
  const meta = INDICATORS.find(i => i.id === indicatorId)
  return meta?.valueType === 'select' ? OPS_SELECT : OPS_NUMBER
}

// Get indicator meta
const getIndicatorMeta = (indicatorId) => {
  return INDICATORS.find(i => i.id === indicatorId) || INDICATORS[0]
}

// Generate preview text for conditions
const conditionsPreview = computed(() => {
  if (!parameters.value.entryConditions || parameters.value.entryConditions.length === 0) {
    return 'No conditions yet.'
  }
  
  return parameters.value.entryConditions.map((cond, idx) => {
    const meta = getIndicatorMeta(cond.indicator)
    const label = meta.hasPeriod && cond.period ? `${cond.indicator}(${cond.period})` : cond.indicator
    const valDisplay = cond.value !== undefined && cond.value !== '' ? cond.value : '?'
    let parts = `<span class="tag tag-indicator">${label}</span> <span class="tag tag-op">${cond.op}</span> <span class="tag tag-val">${valDisplay}</span>`
    if (idx < parameters.value.entryConditions.length - 1) {
      parts += ` <span class="tag tag-logic">${parameters.value.entryConditions[idx + 1].logic}</span>`
    }
    return parts
  }).join(' ')
})

// Helper to update a strategy parameter value
const updateStrategyParam = (type, field, value) => {
  const strategy = parameters.value?.strategy
  if (!Array.isArray(strategy)) return
  const item = strategy.find(s => s?.type === type)
  if (item?.parameters) {
    item.parameters[field] = value
  }
}

// Helper to create a writable computed for a strategy parameter field
const makeStrategyField = (type, field, defaultValue = '') => {
  return computed({
    get: () => {
      const strategy = parameters.value?.strategy
      if (!Array.isArray(strategy)) return defaultValue
      const item = strategy.find(s => s?.type === type)
      return item?.parameters?.[field] ?? defaultValue
    },
    set: (value) => {
      updateStrategyParam(type, field, value)
    }
  })
}

// Writable computed properties for exit/stopLoss/takeProfit fields
const exitIndicator = makeStrategyField('exit', 'indicator', 'RSI')
const exitOperator = makeStrategyField('exit', 'operator', '<')
const exitValue = makeStrategyField('exit', 'value', '')
const stopLossType = makeStrategyField('stopLoss', 'lossType', 'percent')
const stopLossValue = makeStrategyField('stopLoss', 'value', '')
const takeProfitType = makeStrategyField('takeProfit', 'profitType', 'percent')
const takeProfitValue = makeStrategyField('takeProfit', 'value', '')

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
}

const handleBack = () => {
  emit('navigate', 'strategy-list')
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

const handleAddStrategy = async () => {
  if (!strategyName.value.trim()) {
    alert('Please enter a strategy name')
    return
  }

  /*if (!selectedStrategy.value) {
    alert('Please select a strategy type')
    return
  }*/

  isLoading.value = true

  try {
    const response = await fetch('http://localhost:5000/api/strategies', {
      method: 'POST',
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
      
      <!-- New Tab Interface -->
      <div class="tabs">
        <button 
          :class="['tab', { active: strategyTab === 'general' }]" 
          @click="strategyTab = 'general'"
        >
          General
        </button>
        <button 
          :class="['tab', { active: strategyTab === 'entry' }]" 
          @click="strategyTab = 'entry'"
        >
          Entry
        </button>
        <button 
          :class="['tab', { active: strategyTab === 'exit' }]" 
          @click="strategyTab = 'exit'"
        >
          Exit
        </button>
        <button 
          :class="['tab', { active: strategyTab === 'parameters' }]" 
          @click="strategyTab = 'parameters'"
        >
          Strategy Parameters
        </button>
      </div>

      <div class="tab-content">
        <!-- General Tab -->
        <div v-if="strategyTab === 'general'" class="tab-pane">
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

          <!-- Stock List Input -->
          <div class="form-group">
            <label for="stock-list">Stock List</label>
            <textarea 
              id="stock-list"
              v-model="stockList"
              placeholder="Enter stock symbols separated by commas (e.g., AAPL, TSLA, MSFT) 
or use Strategy Parameters: Screening > stock universe settings"
              rows="4"
            ></textarea> 
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
        </div>


        <!-- Entry Tab - Condition Builder -->
        <div v-if="strategyTab === 'entry'" class="tab-pane">
          <div class="condition-builder">
            <h4>Entry Conditions</h4>
            <p class="section-description">Add multiple conditions with AND/OR logic between them</p>
            
            <div class="conditions-list">
              <div v-for="(condition, index) in parameters.entryConditions" :key="condition.id" class="condition-group">
                <!-- Logic divider for conditions after the first one -->
                <div v-if="index > 0" class="logic-divider">
                  <div class="divider-line"></div>
                  <button 
                    class="logic-pill" 
                    :class="{ active: condition.logic === 'AND' }"
                    @click="toggleLogic(condition.id)"
                    type="button"
                  >
                    {{ condition.logic }}
                  </button>
                  <div class="divider-line"></div>
                </div>
                
                <!-- Condition row -->
                <div class="condition-row">
                  <!-- Indicator select -->
                  <div class="form-group compact">
                    <label class="field-label">Indicator</label>
                    <select 
                      class="indicator-select"
                      :value="condition.indicator"
                      @change="updateConditionField(condition.id, 'indicator', $event.target.value)"
                    >
                      <option v-for="ind in INDICATORS" :key="ind.id" :value="ind.id">
                        {{ ind.label }}
                      </option>
                    </select>
                  </div>
                  
                  <!-- Period input (if indicator has period) -->
                  <div v-if="getIndicatorMeta(condition.indicator).hasPeriod" class="form-group compact period-group">
                    <label class="field-label">Period</label>
                    <input
                      type="number"
                      class="period-input"
                      :value="condition.period"
                      @change="updateConditionField(condition.id, 'period', $event.target.value)"
                      min="1"
                      max="200"
                    >
                  </div>
                  
                  <!-- Operator select -->
                  <div class="form-group compact">
                    <label class="field-label">Operator</label>
                    <select 
                      class="operator-select"
                      :value="condition.op"
                      @change="updateConditionField(condition.id, 'op', $event.target.value)"
                    >
                      <option v-for="op in getAvailableOperators(condition.indicator)" :key="op" :value="op">
                        {{ op }}
                      </option>
                    </select>
                  </div>
                  
                  <!-- Value input -->
                  <div class="form-group compact">
                    <label class="field-label">Value</label>
                    <template v-if="getIndicatorMeta(condition.indicator).valueType === 'select'">
                      <select 
                        class="value-select"
                        :value="condition.value"
                        @change="updateConditionField(condition.id, 'value', $event.target.value)"
                      >
                        <option v-for="opt in getIndicatorMeta(condition.indicator).options" :key="opt" :value="opt">
                          {{ opt.replace(/_/g, ' ') }}
                        </option>
                      </select>
                    </template>
                    <template v-else>
                      <input
                        type="number"
                        class="value-input"
                        :value="condition.value"
                        @change="updateConditionField(condition.id, 'value', $event.target.value)"
                        :placeholder="getIndicatorMeta(condition.indicator).valuePlaceholder"
                      >
                    </template>
                  </div>
                  
                  <!-- Remove button -->
                  <button 
                    class="remove-btn"
                    @click="removeCondition(condition.id)"
                    type="button"
                    title="Remove condition"
                    v-if="parameters.entryConditions.length > 1"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Add condition button -->
            <button class="add-condition-btn" @click="addCondition" type="button">
              + Add condition
            </button>
            
            <!-- Preview box -->
            <div class="preview-box">
              <h5>Condition Summary</h5>
              <div class="preview-content" v-html="conditionsPreview"></div>
            </div>
          </div>
        </div>

        <!-- Exit Tab -->
        <div v-if="strategyTab === 'exit'" class="tab-pane">
          <div class="strategy-rules-grid">
            <!-- Exit Rule -->
            <div class="strategy-rule-group">
              <h4>Exit Rule</h4>
              <div class="form-group">
                <label for="exit-indicator">Indicator</label>
                <select 
                  id="exit-indicator"
                  v-model="exitIndicator"
                >
                  <option value="RSI">RSI</option>
                  <option value="Close">Close</option>
                  <option value="SMA">SMA</option>
                  <option value="EMA">EMA</option>
                  <option value="MACD">MACD</option>
                  <option value="Volume">Volume</option>
                </select>
              </div>
              <div class="form-group">
                <label for="exit-operator">Operator</label>
                <select 
                  id="exit-operator"
                  v-model="exitOperator"
                >
                  <option value="<"><</option>
                  <option value=">">></option>
                  <option value="crosses above">crosses above</option>
                  <option value="crosses below">crosses below</option>
                  <option value=">=">>=</option>
                  <option value="<="><=</option>
                  <option value="==">==</option>
                </select>
              </div>
              <div class="form-group">
                <label for="exit-value">Value</label>
                <input
                  id="exit-value"
                  v-model="exitValue"
                  type="number"
                  step="0.01"
                  placeholder="Enter value"
                >
              </div>
            </div>

            <!-- Stop Loss -->
            <div class="strategy-rule-group">
              <h4>Stop Loss</h4>
              <div class="form-group">
                <label for="stop-loss-type">Type</label>
                <select 
                  id="stop-loss-type"
                  v-model="stopLossType"
                >
                  <option value="percent">Percent</option>
                  <option value="fixed">Fixed Amount</option>
                </select>
              </div>
              <div class="form-group">
                <label for="stop-loss-value">Value</label>
                <input
                  id="stop-loss-value"
                  v-model="stopLossValue"
                  type="number"
                  step="0.01"
                  placeholder="Enter value"
                >
                <small class="form-help" v-if="stopLossType === 'percent'">
                  Percentage loss from entry price
                </small>
                <small class="form-help" v-else>
                  Fixed amount loss from entry price
                </small>
              </div>
            </div>

            <!-- Take Profit -->
            <div class="strategy-rule-group">
              <h4>Take Profit</h4>
              <div class="form-group">
                <label for="take-profit-type">Type</label>
                <select 
                  id="take-profit-type"
                  v-model="takeProfitType"
                >
                  <option value="percent">Percent</option>
                  <option value="fixed">Fixed Amount</option>
                </select>
              </div>
              <div class="form-group">
                <label for="take-profit-value">Value</label>
                <input
                  id="take-profit-value"
                  v-model="takeProfitValue"
                  type="number"
                  step="0.01"
                  placeholder="Enter value"
                >
                <small class="form-help" v-if="takeProfitType === 'percent'">
                  Percentage gain from entry price
                </small>
                <small class="form-help" v-else>
                  Fixed amount gain from entry price
                </small>
              </div>
            </div>
          </div>

          <!-- Signal Mapping Display -->
          <div class="signal-mapping-section">
            <h4>Signal Mapping (Auto-generated)</h4>
            <div class="signal-mapping-grid">
              <div class="signal-mapping-item">
                <strong>Buy Trigger:</strong> {{ parameters.signalMapping?.buyTrigger || 'Not set' }}
              </div>
              <div class="signal-mapping-item">
                <strong>Sell Trigger:</strong> {{ parameters.signalMapping?.sellTrigger || 'Not set' }}
              </div>
              <div class="signal-mapping-item">
                <strong>Stop Loss:</strong> 
                <span v-if="parameters.signalMapping?.stopLoss">
                  {{ parameters.signalMapping.stopLoss.lossType }}: {{ parameters.signalMapping.stopLoss.value }}
                </span>
                <span v-else>Not set</span>
              </div>
              <div class="signal-mapping-item">
                <strong>Take Profit:</strong>
                <span v-if="parameters.signalMapping?.takeProfit">
                  {{ parameters.signalMapping.takeProfit.profitType }}: {{ parameters.signalMapping.takeProfit.value }}
                </span>
                <span v-else>Not set</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Strategy Parameters Tab -->
        <div v-if="strategyTab === 'parameters'" class="tab-pane">
          <div class="parameters-section">
            <h3>Strategy Parameters</h3>
            
            <!-- Tab Navigation -->
            <div class="parameter-tabs">
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
                    @change="updateParametersFromJson"
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
        </div>
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

/* New tab styles from AssetTrade.vue */
.tabs {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
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

/* Existing parameter tab styles */
.parameter-tabs {
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

.strategy-rules-section {
  margin-top: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 1.5rem;
  background: #f8f9fa;
}

.strategy-rules-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #495057;
}

.strategy-rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.strategy-rule-group {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 1rem;
}

.strategy-rule-group h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #495057;
  border-bottom: 1px solid #e9ecef;
  padding-bottom: 0.5rem;
}

.signal-mapping-section {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 1rem;
  margin-top: 1rem;
}

.signal-mapping-section h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #495057;
}

.signal-mapping-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.signal-mapping-item {
  padding: 0.75rem;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  font-size: 0.9rem;
}

.signal-mapping-item strong {
  color: #495057;
  margin-right: 0.5rem;
}

/* Condition Builder Styles */
.condition-builder {
  margin-top: 1rem;
}

.condition-builder h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #495057;
}

.section-description {
  color: #6c757d;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.conditions-list {
  margin-bottom: 1.5rem;
}

.condition-group {
  margin-bottom: 1rem;
}

.logic-divider {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0;
}

.divider-line {
  flex: 1;
  border: none;
  border-top: 1px solid #dee2e6;
}

.logic-pill {
  font-size: 11px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 99px;
  border: 1px solid #dee2e6;
  color: #6c757d;
  cursor: pointer;
  background: #f8f9fa;
  user-select: none;
  transition: all 0.2s;
}

.logic-pill:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.logic-pill.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.condition-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.form-group.compact {
  margin-bottom: 0;
}

.form-group.compact label {
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.form-group.compact select{
  padding: 0 0.5rem;
}

.field-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: #495057;
  margin-bottom: 0.25rem;
  display: block;
}

.indicator-select,
.operator-select,
.value-select,
.value-input,
.period-input {
  height: 36px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background: white;
  color: #333;
  padding: 0 8px;
  font-size: 14px;
  font-family: inherit;
  box-sizing: border-box;
}

.indicator-select,
.operator-select,
.value-select {
  padding-right: 24px; /* Space for dropdown arrow */
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 16px;
}

.indicator-select {
  width: 130px;
}

.operator-select {
  width: 80px;
}

.value-select,
.value-input {
  width: 100px;
}

.period-input {
  width: 70px;
}

.period-group {
  display: flex;
  flex-direction: column;
}

.period-label {
  font-size: 0.8rem;
  color: #6c757d;
  margin-bottom: 0.25rem;
}

.remove-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid #ddd;
  background: transparent;
  color: #6c757d;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 1;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: #dc3545;
  color: white;
  border-color: #dc3545;
}

.add-condition-btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background: transparent;
  color: #333;
  font-size: 14px;
  cursor: pointer;
  margin-top: 8px;
  transition: all 0.2s;
}

.add-condition-btn:hover {
  background: #f8f9fa;
  border-color: #adb5bd;
}

.preview-box {
  margin-top: 24px;
  padding: 16px;
  border-radius: 4px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
}

.preview-box h5 {
  margin-top: 0;
  margin-bottom: 12px;
  color: #495057;
  font-size: 1rem;
}

.preview-content {
  font-size: 14px;
  line-height: 1.6;
}

.tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin: 2px;
  font-weight: 500;
}

.tag-indicator {
  background: #cfe2ff;
  color: #084298;
}

.tag-op {
  background: #fff3cd;
  color: #664d03;
}

.tag-val {
  background: #d1e7dd;
  color: #0a3622;
}

.tag-logic {
  background: #e2e3e5;
  color: #41464b;
  font-weight: 600;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 768px) {
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
  
  .strategy-rules-grid {
    grid-template-columns: 1fr;
  }
  
  .signal-mapping-grid {
    grid-template-columns: 1fr;
  }
  
  .condition-row {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .indicator-select,
  .operator-select,
  .value-select,
  .value-input,
  .period-input {
    width: 100%;
  }
  
  .period-group {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }
  
  .period-label {
    margin-bottom: 0;
    min-width: 60px;
  }
}
</style>
