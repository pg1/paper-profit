<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
    default: false
  },
  message: {
    type: String,
    required: true,
    default: ""
  },
  duration: {
    type: Number,
    default: 2000 // 2 seconds default
  }
})

const emit = defineEmits(['close'])
const isVisible = ref(false)
let timeoutId = null

const handleClose = () => {
  clearTimeout(timeoutId)
  isVisible.value = false
  setTimeout(() => {
    emit('close')
  }, 300) // Wait for fade-out animation
}

// Watch for show prop changes
watch(() => props.show, (newValue) => {
  //console.log('SuccessBanner: show prop changed to:', newValue, 'message:', props.message)
  if (newValue) {
    isVisible.value = true
    // Clear any existing timeout
    clearTimeout(timeoutId)
    // Set new timeout to auto-hide
    timeoutId = setTimeout(() => {
      handleClose()
    }, props.duration)
  } else {
    isVisible.value = false
    clearTimeout(timeoutId)
  }
})

// Cleanup on component unmount
onUnmounted(() => {
  clearTimeout(timeoutId)
})

// Handle initial state
onMounted(() => {
  if (props.show) {
    isVisible.value = true
    timeoutId = setTimeout(() => {
      handleClose()
    }, props.duration)
  }
})
</script>

<template>
  <div v-if="show" class="success-banner" :class="{ 'success-banner--visible': isVisible }">
    <div class="success-banner-content">
      <div class="success-banner-icon">✓</div>
      <div class="success-banner-message">{{ message }}</div>
      <button class="success-banner-close" @click="handleClose">×</button>
    </div>
  </div>
</template>

<style scoped>
.success-banner {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #10b981;
  color: white;
  border-radius: 8px;
  padding: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1001;
  transform: translateX(100%);
  opacity: 0;
  transition: all 0.3s ease-out;
  max-width: 400px;
  min-width: 300px;
}

.success-banner--visible {
  transform: translateX(0);
  opacity: 1;
}

.success-banner-content {
  display: flex;
  align-items: center;
  padding: 1rem 1.25rem;
  gap: 0.75rem;
}

.success-banner-icon {
  font-size: 1.25rem;
  font-weight: bold;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.success-banner-message {
  flex: 1;
  font-weight: 500;
  line-height: 1.4;
  margin: 0;
}

.success-banner-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.8;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.success-banner-close:hover {
  opacity: 1;
}

/* Animation for auto-hide */
@keyframes fade-out {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}

.success-banner--hiding {
  animation: fade-out 0.3s ease-out forwards;
}
</style>
