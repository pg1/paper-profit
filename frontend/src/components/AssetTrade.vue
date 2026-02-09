<script setup>
import { ref, watch } from 'vue'
import AssetBuy from './AssetBuy.vue'
import AssetSell from './AssetSell.vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['navigate'])

const activeTab = ref('buy')

const handleNavigation = (page, params = {}) => {
  emit('navigate', page, params)
}

// Pass navigation params to child components
const buyNavigationParams = ref({ ...props.navigationParams })
const sellNavigationParams = ref({ ...props.navigationParams })

// Watch for changes in navigation params
watch(() => props.navigationParams, (newParams) => {
  buyNavigationParams.value = { ...newParams }
  sellNavigationParams.value = { ...newParams }
}, { deep: true })
</script>

<template>
    <!-- Tabs Navigation -->
    <div class="tabs">
      <button 
        :class="['tab', { active: activeTab === 'buy' }]" 
        @click="activeTab = 'buy'"
      >
        Buy
      </button>
      <button 
        :class="['tab', { active: activeTab === 'sell' }]" 
        @click="activeTab = 'sell'"
      >
        Sell
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <div v-if="activeTab === 'buy'" >
        <AssetBuy 
          @navigate="handleNavigation"
          :navigation-params="buyNavigationParams"
        />
      </div>
      <div v-if="activeTab === 'sell'" >
        <AssetSell 
          @navigate="handleNavigation"
          :navigation-params="sellNavigationParams"
        />
      </div>
    </div>
</template>

<style scoped>


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
  
}


@media (max-width: 768px) {
  
  
  .tab {
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
  }
  
  .tab-pane {
    padding: 1rem;
  }
}
</style>