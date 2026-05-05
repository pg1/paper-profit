<script setup>
import { ref } from 'vue'

const strategyName = ref('')
const isLoading = ref(false)

const emit = defineEmits(['navigate'])

const handleBack = () => {
  emit('navigate', 'strategy-list')
}

const handleAddStrategy = async () => {
  if (!strategyName.value.trim()) {
    alert('Please enter a strategy name')
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
        name: strategyName.value
      })
    })

    if (response.ok) {
      const data = await response.json()
      // Navigate to edit the newly created strategy
      emit('navigate', 'strategy-edit', {
        strategyId: data.id
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
      <div class="form-group">
        <label for="strategy-name">Strategy Name</label>
        <input 
          id="strategy-name"
          v-model="strategyName"
          type="text" 
          placeholder="Enter strategy name"
        >
      </div>

      <div class="form-actions">
        <button 
          class="btn-primary" 
          @click="handleAddStrategy"
          :disabled="isLoading"
        >
          {{ isLoading ? 'Creating...' : 'Create Strategy' }}
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

.form-group input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.form-actions {
  margin-top: 2rem;
}
</style>
