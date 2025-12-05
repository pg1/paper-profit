<script setup>
import { ref, watch, onMounted } from 'vue'
import Popup from './ui/Popup.vue'

const accountType = ref('')
const accountName = ref('')
const initialBalance = ref(10000)
const selectedStrategy = ref('')
const strategies = ref([])
const isLoading = ref(false)
const showAlpacaPopup = ref(false)

const emit = defineEmits(['navigate'])

const handleBack = () => {
  emit('navigate', 'welcome')
}

// Watch for account type changes
watch(accountType, (newValue) => {
  if (newValue === 'alpaca') {
    showAlpacaPopup.value = true
  }
})

const closeAlpacaPopup = () => {
  showAlpacaPopup.value = false
  accountType.value = ''
}

// Fetch available strategies
const fetchStrategies = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/strategies')
    if (response.ok) {
      const data = await response.json()
      strategies.value = data
    } else {
      console.error('Failed to fetch strategies')
    }
  } catch (error) {
    console.error('Error fetching strategies:', error)
  }
}

const handleAddAccount = async () => {
  if (!accountName.value.trim()) {
    alert('Please enter an account name')
    return
  }

  if (!initialBalance.value || initialBalance.value <= 0) {
    alert('Please enter a valid initial balance')
    return
  }

  isLoading.value = true

  try {
    const accountData = {
      account_id: accountName.value,
      cash_balance: initialBalance.value
    }

    // Add strategy_id if a strategy is selected
    if (selectedStrategy.value) {
      accountData.strategy_id = parseInt(selectedStrategy.value)
    }

    const response = await fetch('http://localhost:5000/api/accounts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(accountData)
    })

    if (response.ok) {
      // Navigate to welcome page with success state
      emit('navigate', 'welcome', { 
        showSuccess: true, 
        successMessage: 'Account added successfully!' 
      })
      
      // Reset form
      accountName.value = ''
      initialBalance.value = 10000
      accountType.value = ''
      selectedStrategy.value = ''
    } else {
      throw new Error('Failed to add account')
    }
  } catch (error) {
    console.error('Error adding account:', error)
    alert('Failed to add account. Please try again.')
  } finally {
    isLoading.value = false
  }
}

// Fetch strategies when component mounts
onMounted(() => {
  fetchStrategies()
})
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>Add Account</h2>
        <p>Create a new trading account</p>
      </div>
      <button class="btn-secondary" @click="handleBack">Back</button>
    </div>

    <div class="input-form">
      <div class="form-group">
        <label for="account-type">Account Type</label>
        <select 
          id="account-type" 
          v-model="accountType"
        >
          <option value="" disabled>Select account type</option>
          <option value="virtual">Create New Virtual Account</option>
          <option value="alpaca">Link an Alpaca account</option>
        </select>
      </div>

      <div class="form-group">
        <label for="strategy">Trading Strategy (Optional)</label>
        <select 
          id="strategy" 
          v-model="selectedStrategy"
        >
          <option value="">No strategy (manual trading)</option>
          <option 
            v-for="strategy in strategies" 
            :key="strategy.id" 
            :value="strategy.id"
          >
            {{ strategy.name }} ({{ strategy.strategy_type }})
          </option>
        </select>
      </div>

      <div class="form-group">
        <label for="account-name">Account Name</label>
        <input 
          id="account-name"
          v-model="accountName"
          type="text" 
          placeholder="Enter account name"
        >
      </div>

      <div class="form-group">
        <label for="initial-balance">Initial Balance</label>
        <input 
          id="initial-balance"
          v-model.number="initialBalance"
          type="number" 
          placeholder="Enter initial balance"
          min="0"
          step="0.01"
        >
      </div>

      <div class="form-actions">
        <button 
          class="btn-primary" 
          @click="handleAddAccount"
          :disabled="isLoading"
        >
          {{ isLoading ? 'Adding...' : 'Add Account' }}
        </button>
      </div>
    </div>

    <!-- Alpaca Popup -->
    <Popup
      :show="showAlpacaPopup"
      title="TODO"
      message="Alpaca account integration is not yet implemented. This feature is currently under development."
      @close="closeAlpacaPopup"
    />

  </section>
</template>

<style scoped>
</style>
