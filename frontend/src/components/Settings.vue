<script setup>
import { ref, onMounted, computed } from 'vue'

const emit = defineEmits(['navigate'])

// Settings data from API
const settings = ref([])
const loading = ref(false)
const error = ref(null)

// Service list data
const serviceList = ref([])
const selectedService = ref(null)

// Editing state
const editingSetting = ref(null)
const editedParameters = ref('')
const editedSettingStatus = ref(true)

// Service editing state
const editedServiceParameters = ref('')
const editedServiceStatus = ref(true)

// Group settings by category
const groupedSettings = computed(() => {
  const groups = {}
  
  settings.value.forEach(setting => {
    const category = setting.category || 'Uncategorized'
    if (!groups[category]) {
      groups[category] = []
    }
    groups[category].push(setting)
  })
  
  // Convert to array format for template
  return Object.keys(groups).map(category => ({
    name: category,
    settings: groups[category]
  }))
})

// Fetch settings from API
const fetchSettings = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await fetch('http://localhost:5000/api/settings')
    if (!response.ok) {
      throw new Error(`Failed to fetch settings: ${response.statusText}`)
    }
    settings.value = await response.json()
  } catch (err) {
    error.value = err.message
    console.error('Error fetching settings:', err)
  } finally {
    loading.value = false
  }
}

// Start editing a setting
const startEditing = (setting) => {
  editingSetting.value = setting.name
  editedParameters.value = typeof setting.parameters === 'string' 
    ? setting.parameters 
    : JSON.stringify(setting.parameters, null, 2)
  editedSettingStatus.value = setting.is_active !== false
}

// Cancel editing
const cancelEditing = () => {
  editingSetting.value = null
  editedParameters.value = ''
}

// Update setting via API
const updateSetting = async (settingName) => {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`http://localhost:5000/api/settings/${settingName}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        parameters: editedParameters.value,
        is_active: editedSettingStatus.value
      })
    })
    
    if (!response.ok) {
      throw new Error(`Failed to update setting: ${response.statusText}`)
    }
    
    // Refresh the settings list
    await fetchSettings()
    editingSetting.value = null
    editedParameters.value = ''
  } catch (err) {
    error.value = err.message
    console.error('Error updating setting:', err)
  } finally {
    loading.value = false
  }
}

// Fetch service list from API
const fetchServiceList = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/service-list')
    if (!response.ok) {
      throw new Error(`Failed to fetch service list: ${response.statusText}`)
    }
    serviceList.value = await response.json()
  } catch (err) {
    console.error('Error fetching service list:', err)
  }
}

// Handle service selection
const handleServiceSelect = (serviceValue) => {
  if (!serviceValue) {
    selectedService.value = null
    editedServiceParameters.value = ''
    editedServiceStatus.value = true
    return
  }
  // Parse the service object from the string value
  try {
    selectedService.value = JSON.parse(serviceValue)
    // Populate form fields with service data - use predefined parameters from YAML
    editedServiceParameters.value = selectedService.value.parameters || ''
    editedServiceStatus.value = selectedService.value.status !== false
  } catch (err) {
    console.error('Error parsing service:', err)
    selectedService.value = null
    editedServiceParameters.value = ''
    editedServiceStatus.value = true
  }
}

// Cancel service editing
const cancelServiceEditing = () => {
  selectedService.value = null
  editedServiceParameters.value = ''
  editedServiceStatus.value = true
}

// Save service - either create new or update existing
const saveService = async () => {
  loading.value = true
  error.value = null
  try {
    // Check if service already exists in settings
    const existingSetting = settings.value.find(setting => 
      setting.name === selectedService.value.name
    )

    if (existingSetting) {
      // Update existing setting
      const response = await fetch(`http://localhost:5000/api/settings/${selectedService.value.name}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          parameters: editedServiceParameters.value,
          is_active: editedServiceStatus.value
        })
      })
      
      if (!response.ok) {
        throw new Error(`Failed to update service: ${response.statusText}`)
      }
    } else {
      // Find the category for this service from the service list
      let serviceCategory = 'services'
      for (const category of serviceList.value) {
        const serviceInCategory = category.services.find(service => service.name === selectedService.value.name)
        if (serviceInCategory) {
          serviceCategory = category.name
          break
        }
      }
      
      // Create new setting
      const response = await fetch('http://localhost:5000/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: selectedService.value.name,
          parameters: editedServiceParameters.value,
          category: serviceCategory,
          is_active: editedServiceStatus.value
        })
      })
      
      if (!response.ok) {
        throw new Error(`Failed to create service: ${response.statusText}`)
      }
    }
    
    // Refresh settings and service list
    await fetchSettings()
    await fetchServiceList()
    selectedService.value = null
    editedServiceParameters.value = ''
    editedServiceStatus.value = true
  } catch (err) {
    error.value = err.message
    console.error('Error saving service:', err)
  } finally {
    loading.value = false
  }
}

// Delete service
const deleteService = async () => {
  if (!confirm(`Are you sure you want to delete the service "${selectedService.value.name}"?`)) {
    return
  }
  
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`http://localhost:5000/api/settings/${selectedService.value.name}`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      throw new Error(`Failed to delete service: ${response.statusText}`)
    }
    
    // Refresh settings and service list
    await fetchSettings()
    await fetchServiceList()
    selectedService.value = null
    editedServiceParameters.value = ''
    editedServiceStatus.value = true
  } catch (err) {
    error.value = err.message
    console.error('Error deleting service:', err)
  } finally {
    loading.value = false
  }
}

// Delete setting
const deleteSetting = async (settingName) => {
  if (!confirm(`Are you sure you want to delete the setting "${settingName}"?`)) {
    return
  }
  
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`http://localhost:5000/api/settings/${settingName}`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      throw new Error(`Failed to delete setting: ${response.statusText}`)
    }
    
    // Refresh the settings list
    await fetchSettings()
    editingSetting.value = null
  } catch (err) {
    error.value = err.message
    console.error('Error deleting setting:', err)
  } finally {
    loading.value = false
  }
}

// Load settings and service list on component mount
onMounted(() => {
  fetchSettings()
  fetchServiceList()
})
</script>

<template>
  <div class="settings-container">
    <h1>Settings</h1>
    
    <!-- Service Selection Dropdown -->
    <div class="service-selection">
      <label for="service-dropdown">Add a new service:</label>
      <select 
        id="service-dropdown"
        v-model="selectedService"
        @change="handleServiceSelect($event.target.value)"
        class="service-dropdown"
      >
        <option :value="null">-- Select --</option>
        <optgroup 
          v-for="category in serviceList" 
          :key="category.name" 
          :label="category.name"
        >
          <option 
            v-for="service in category.services" 
            :key="service.name" 
            :value="JSON.stringify(service)"
          >
            {{ service.name }}
          </option>
        </optgroup>
      </select>
    </div>

    <!-- Selected Service Display -->
    <div v-if="selectedService" class="selected-service-section">
      <div class="category-section">
        <div class="category-items">
          <div class="setting-item">
            <div class="setting-content">
              <h3 class="setting-title">{{ selectedService.name }}</h3>
              
              <!-- Edit mode - always show when service is selected -->
              <div class="setting-edit">
                <div class="edit-form">
                  <label for="service-parameters">Parameters:</label>
                  <textarea
                    id="service-parameters"
                    v-model="editedServiceParameters"
                    class="parameters-input"
                    rows="4"
                    placeholder="Enter parameters (JSON format recommended)"
                  ></textarea>
                  
                  <div class="status-toggle">
                    <label for="service-status">Status:</label>
                    <input
                      id="service-status"
                      type="checkbox"
                      v-model="editedServiceStatus"
                      class="status-checkbox"
                    >
                    <span class="status-label">{{ editedServiceStatus ? 'Active' : 'Inactive' }}</span>
                  </div>
                  
                  <div class="edit-actions">
                    <button 
                      @click="saveService" 
                      class="update-button"
                      :disabled="loading"
                    >
                      {{ loading ? 'Saving...' : 'Save Service' }}
                    </button>
                    <button 
                      @click="cancelServiceEditing" 
                      class="cancel-button"
                      :disabled="loading"
                    >
                      Cancel
                    </button>
                    <button 
                      @click="deleteService" 
                      class="delete-button"
                      :disabled="loading"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <p>Loading settings...</p>
    </div>
    
    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">Error: {{ error }}</p>
      <button @click="fetchSettings" class="retry-button">Retry</button>
    </div>
    
    <!-- Settings grouped by category -->
    <div v-else class="settings-categories">
      <div
        v-for="category in groupedSettings"
        :key="category.name"
        class="category-section"
      >
        <h2 class="category-header">{{ category.name }}</h2>
        
        <div class="category-items">
          <div
            v-for="setting in category.settings"
            :key="setting.name"
            class="setting-item"
          >
            <div class="setting-content">
              <h3 class="setting-title">{{ setting.name }}</h3>
              
              <!-- Display mode -->
              <div v-if="editingSetting !== setting.name" class="setting-display">
                <p class="setting-parameters">
                  <strong>Parameters:</strong> 
                  <span class="parameters-text" @click="startEditing(setting)">
                    {{ setting.parameters || 'No parameters set' }}
                  </span>
                </p>
                <p class="setting-status" @click="startEditing(setting)">
                  <strong>Status:</strong> 
                  <span class="status-text">
                    {{ setting.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </p>
              </div>
              
              <!-- Edit mode -->
              <div v-else class="setting-edit">
                <div class="edit-form">
                  <label for="parameters">Parameters:</label>
                  <textarea
                    id="parameters"
                    v-model="editedParameters"
                    class="parameters-input"
                    rows="4"
                    placeholder="Enter parameters (JSON format recommended)"
                  ></textarea>
                  
                  <div class="status-toggle">
                    <label for="setting-status">Status:</label>
                    <input
                      id="setting-status"
                      type="checkbox"
                      v-model="editedSettingStatus"
                      class="status-checkbox"
                    >
                    <span class="status-label">{{ editedSettingStatus ? 'Active' : 'Inactive' }}</span>
                  </div>
                  
                  <div class="edit-actions">
                    <button 
                      @click="updateSetting(setting.name)" 
                      class="update-button"
                      :disabled="loading"
                    >
                      {{ loading ? 'Updating...' : 'Update' }}
                    </button>
                    <button 
                      @click="cancelEditing" 
                      class="cancel-button"
                      :disabled="loading"
                    >
                      Cancel
                    </button>
                    <button 
                      @click="deleteSetting(setting.name)" 
                      class="delete-button"
                      :disabled="loading"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Empty state -->
      <div v-if="settings.length === 0" class="empty-state">
        <p>No settings found.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.settings-container h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #333;
}

/* Service selection styles */
.service-selection {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.service-selection label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
  font-size: 1rem;
}

.service-dropdown {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  background: white;
  cursor: pointer;
}

.service-dropdown:focus {
  outline: none;
  border-color: #eee;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

/* Status toggle styles */
.status-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 1rem 0;
}

.status-toggle label {
  font-weight: 600;
  color: #333;
  margin: 0;
}

.status-checkbox {
  width: 1.2rem;
  height: 1.2rem;
  cursor: pointer;
}

.status-label {
  font-size: 0.9rem;
  color: #666;
}

/* Selected service section */
.selected-service-section {
  margin-bottom: 2rem;
}

/* Loading and error states */
.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 2rem;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.error-message {
  color: #dc3545;
  margin-bottom: 1rem;
}

.retry-button {
  background: #eee;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.retry-button:hover {
  background: #0056b3;
}

/* Settings categories layout */
.settings-categories {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.category-section {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.category-header {
  background: #f8f9fa;
  margin: 0;
  padding: 1rem 1.5rem;
  font-size: 1.3rem;
  font-weight: 600;
  color: #333;
  border-bottom: 1px solid #e0e0e0;
}

.category-items {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.setting-item {
  padding: 1.5rem;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.setting-item:hover {
  background: #f8f9fa;
  border-color: #eee;
  box-shadow: 0 2px 8px rgba(0, 123, 255, 0.1);
}

.setting-content {
  width: 100%;
}

.setting-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.setting-category {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: #666;
  font-style: italic;
}

/* Display mode */
.setting-display {
  margin-top: 1rem;
}

.setting-parameters,
.setting-status {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.parameters-text {
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.parameters-text:hover {
  background-color: #e9ecef;
}

/* Edit mode */
.setting-edit {
  margin-top: 1rem;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-form label {
  font-weight: 600;
  color: #333;
}

.parameters-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  resize: vertical;
}

.parameters-input:focus {
  outline: none;
  border-color: #eee;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.edit-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: space-between;
  align-items: center;
}

.update-button,
.cancel-button,
.delete-button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s ease;
}

.update-button {
  background: #28a745;
  color: white;
}

.update-button:hover:not(:disabled) {
  background: #218838;
}

.update-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.cancel-button {
  background: #6c757d;
  color: white;
}

.cancel-button:hover:not(:disabled) {
  background: #5a6268;
}

.cancel-button:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

.delete-button {
  background: #dc3545;
  color: white;
}

.delete-button:hover:not(:disabled) {
  background: #c82333;
}

.delete-button:disabled {
  background: #e4606d;
  cursor: not-allowed;
}
</style>
