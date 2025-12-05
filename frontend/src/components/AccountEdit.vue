<script setup>
import { ref, onMounted } from 'vue'

const accountName = ref('')
const selectedStrategy = ref(null)
const strategies = ref([])
const isLoading = ref(false)
const isEditing = ref(false)

const emit = defineEmits(['navigate'])

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const handleBack = () => {
  emit('navigate', 'welcome')
}

const fetchStrategies = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/strategies')
    
    if (!response.ok) {
      throw new Error(`Failed to fetch strategies: ${response.status}`)
    }
    
    const data = await response.json()
    strategies.value = data
  } catch (err) {
    console.error('Error fetching strategies:', err)
  }
}

const fetchAccount = async (accountId) => {
  isLoading.value = true
  try {
    const response = await fetch(`http://localhost:5000/api/accounts/${accountId}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch account: ${response.status}`)
    }
    
    const account = await response.json()
    accountName.value = account.account_name || account.account_id
    selectedStrategy.value = account.strategy_id
    isEditing.value = true
  } catch (err) {
    console.error('Error fetching account:', err)
    alert('Failed to load account. Please try again.')
  } finally {
    isLoading.value = false
  }
}

const handleUpdateAccount = async () => {
  if (!accountName.value.trim()) {
    alert('Please enter an account name')
    return
  }

  isLoading.value = true

  try {
    const accountId = props.navigationParams.accountId
    const updateData = {
      account_name: accountName.value
    }

    // Only include strategy_id if a strategy is selected
    if (selectedStrategy.value) {
      updateData.strategy_id = selectedStrategy.value
    }

    const response = await fetch(`http://localhost:5000/api/accounts/${accountId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updateData)
    })

    if (response.ok) {
      // Navigate to welcome page with success state
      emit('navigate', 'welcome', { 
        showSuccess: true, 
        successMessage: 'Account updated successfully!' 
      })
    } else {
      throw new Error('Failed to update account')
    }
  } catch (error) {
    console.error('Error updating account:', error)
    alert('Failed to update account. Please try again.')
  } finally {
    isLoading.value = false
  }
}

// Watch for navigation params to load account data
onMounted(() => {
  fetchStrategies()
  if (props.navigationParams.accountId) {
    fetchAccount(props.navigationParams.accountId)
  }
})
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>{{ isEditing ? 'Edit Account' : 'Add Account' }}</h2>
        <p>{{ isEditing ? 'Update your trading account details' : 'Create a new trading account' }}</p>
      </div>
      <button class="btn-secondary" @click="handleBack">Back</button>
    </div>

    <div v-if="isLoading && !isEditing" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading account...</p>
    </div>

    <div v-else class="input-form">
      <div class="form-group">
        <label for="account-name">Account Name</label>
        <input 
          id="account-name"
          v-model="accountName"
          type="text" 
          placeholder="Enter account name"
          :disabled="isLoading"
        >
      </div>

      <div class="form-group">
        <label for="strategy">Trading Strategy</label>
        <select 
          id="strategy"
          v-model="selectedStrategy"
          :disabled="isLoading"
        >
          <option :value="null">No Strategy</option>
          <option 
            v-for="strategy in strategies" 
            :key="strategy.id" 
            :value="strategy.id"
          >
            {{ strategy.name }}
          </option>
        </select>
      </div>

      <div class="form-actions">
        <button 
          class="btn-primary" 
          @click="handleUpdateAccount"
          :disabled="isLoading"
        >
          {{ isLoading ? 'Updating...' : 'Update Account' }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.section {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.section-header h2 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 1.8rem;
}

.section-header p {
  margin: 0;
  color: #666;
  font-size: 1rem;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}

.btn-secondary:hover {
  background: #5a6268;
}

.input-form {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.form-group input:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
}

.form-actions {
  text-align: center;
  margin-top: 2rem;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
}
</style>
