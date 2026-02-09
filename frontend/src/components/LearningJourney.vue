<script setup>
import { ref, onMounted, computed } from 'vue'
import LearningStatus from './ui/LearningStatus.vue'

const emit = defineEmits(['navigate'])

// Declare learningDays as a reactive property
const learningDays = ref([])
const learningProgress = ref({
  currentDay: 1,
  daysCompleted: 0,
  totalXP: 0,
  streak: 0
})

const fetchLearningDays = async () => {
   try {
     const response = await fetch('http://localhost:5000/api/learning-days')
     const data = await response.json()
     
     // Transform the YAML data structure to array format expected by frontend
     // The YAML has keys like "day_1", "day_2", etc.
     const transformedData = Object.entries(data).map(([key, value]) => {
       // Extract day number from key (e.g., "day_1" -> 1)
       const dayNumber = parseInt(key.replace('day_', ''))
       return {
         day: dayNumber,
         title: value.title,
         description: value.description
       }
     }).sort((a, b) => a.day - b.day) // Sort by day number
     
     learningDays.value = transformedData
   } catch (error) {
     console.error('Error fetching learning days:', error)
     // For development, use mock data if API is not available
     learningDays.value = generateMockLearningDays()
  }
}

const fetchLearningProgress = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/settings/learning_journey')
    const data = await response.json()
    
    // Parse the parameters JSON string
    if (data.parameters) {
      const params = JSON.parse(data.parameters)
      let daysCompleted = params.day

      //1st day completed
      if(daysCompleted == 0) daysCompleted = 1;

      learningProgress.value = {
        currentDay: (daysCompleted+1),
        daysCompleted: daysCompleted,
        totalXP: daysCompleted * 55,
        streak: 0
      }
    
    }
    console.log(learningProgress.value);

  } catch (error) {
    console.error('Error fetching learning progress:', error)
    // If setting doesn't exist, create it with default values
    await createDefaultLearningProgress()
  }
}

const createDefaultLearningProgress = async () => {
  try {
    const defaultProgress = {
      currentDay: 1,
      daysCompleted: 0,
      totalXP: 0,
      streak: 0
    }
    
    const response = await fetch('http://localhost:5000/api/settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: 'learning_journey',
        parameters: JSON.stringify(defaultProgress),
        category: 'learning',
        is_active: true
      })
    })
    
    if (response.ok) {
      learningProgress.value = defaultProgress
    }
  } catch (error) {
    console.error('Error creating default learning progress:', error)
  }
}

// Generate mock data for development
const generateMockLearningDays = () => {
  const mockDays = []
  for (let i = 1; i <= 21; i++) {
    mockDays.push({
      day: i,
      title: `Learning Day ${i}`,
      description: `This is the description for learning day ${i}. Follow this structured path to build your investing and trading knowledge.`
    })
  }
  return mockDays
}

// Handle day card click
const handleDayClick = (day) => {
  emit('navigate', 'learning-details', { day: day.day })
}

// Handle continue learning button click
const handleContinueLearning = () => {
  emit('navigate', 'learning-details', { day: learningProgress.value.currentDay })
}

// Handle review progress button click  
const handleReviewProgress = () => {
  // Could navigate to a progress review page or show a modal
  // For now, just navigate to the current day
  emit('navigate', 'learning-details', { day: learningProgress.value.currentDay })
}

onMounted(() => {
  fetchLearningDays()
  fetchLearningProgress()
})
</script>

<template>
  <div class="learning-journey">
    <h2 class="section-title">21-Day Learning Journey</h2>
     <p class="section-description">
        Follow this structured path to build your investing and trading knowledge step by step.
      </p>
      
    <div class="learning-status-container">
      <div class="learning-status-main">
        <LearningStatus 
          :height="400"
          :showControls="true"
          :currentDay="learningProgress.currentDay"
          :daysCompleted="learningProgress.daysCompleted"
        />
      </div>
      <div class="learning-status-sidebar">
        <div class="sidebar-content">
          <h3 class="sidebar-title">Progress Overview</h3>
          <div class="progress-stats">
            <div class="stat-item">
              <span class="stat-label">Current Day</span>
              <span class="stat-value">Day {{ learningProgress.currentDay }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Days Completed</span>
              <span class="stat-value">{{ learningProgress.daysCompleted }} / 21</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Total XP</span>
              <span class="stat-value">{{ learningProgress.totalXP }}</span>
            </div>
          </div>
          <div class="sidebar-actions">
            <button class="action-button primary" @click="handleContinueLearning">Continue Learning</button>
          </div>
          
        </div>
      </div>
    </div>

    <div class="learning-days-section">
      
     
      <div class="learning-days-grid">
        <div 
          v-for="day in learningDays" 
          :key="day.day"
          class="learning-day-card"
          :class="{ 
            'current-day': day.day === learningProgress.currentDay,
            'completed-day': day.day < learningProgress.currentDay,
            'future-day': day.day > learningProgress.currentDay
          }"
          @click="day.day <= learningProgress.currentDay ? handleDayClick(day) : null"
        >
          <div class="day-header">
            <span class="day-number">Day {{ day.day }}</span>
            <span class="day-status" v-if="day.day === learningProgress.currentDay">Current</span>
            <span class="day-status locked" v-else-if="day.day > learningProgress.currentDay">Locked</span>
          </div>
          <h3 class="day-title">{{ day.title }}</h3>
          <p class="day-description">{{ day.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// Empty script block for Vue 2 compatibility if needed
</script>

<style scoped>
.learning-journey {
  padding: 2rem 0;
}

.learning-status-container {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;

}

.learning-status-main {
  flex: 2; /* 2/3 width */
  min-width: 0; /* Important for flex children to respect overflow */
}

.learning-status-sidebar {
  flex: 1; /* 1/3 width */
  min-width: 0;
}

.sidebar-content {
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 1.5rem;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}

.progress-stats {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background-color: #f9f9f9;
  border-radius: 6px;
}

.stat-label {
  font-size: 0.875rem;
  color: #000000;
  opacity: 0.8;
}

.stat-value {
  font-size: 1rem;
  font-weight: 600;
  color: #000000;
}

.sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.action-button {
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.action-button.primary {
  background-color: #000000;
  color: #ffffff;
}

.action-button.primary:hover {
  background-color: #333333;
}

.action-button.secondary {
  background-color: #f0f0f0;
  color: #000000;
}

.action-button.secondary:hover {
  background-color: #e0e0e0;
}

.sidebar-tips {
  margin-top: auto;
}

.tips-title {
  font-size: 1rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 0.75rem;
}

.tips-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.tips-list li {
  font-size: 0.875rem;
  color: #000000;
  opacity: 0.8;
  padding: 0.5rem 0;
  padding-left: 1.25rem;
  position: relative;
  line-height: 1.4;
}

.tips-list li:before {
  content: "•";
  position: absolute;
  left: 0;
  color: #000000;
}

.learning-days-section {
  margin-top: 3rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: #000000;
}

.section-description {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
  margin-bottom: 2rem;
}

.learning-days-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.learning-day-card {
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.learning-day-card.completed-day,
.learning-day-card.current-day {
  cursor: pointer;
}

.learning-day-card.future-day {
  cursor: not-allowed;
  opacity: 0.7;
}

.learning-day-card.completed-day:hover,
.learning-day-card.current-day:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  border-color: #000000;
}

.learning-day-card.current-day {
  border-color: #000000;
  background-color: #f9f9f9;
}

.learning-day-card.completed-day {
  border-color: #39c86a;
  background-color: #f9f9f9;
}

.learning-day-card.future-day {
  border-color: #e0e0e0;
  background-color: #fafafa;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.day-number {
  font-size: 0.875rem;
  font-weight: 600;
  color: #000000;
  background-color: #f0f0f0;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}

.day-status {
  font-size: 0.75rem;
  font-weight: 600;
  color: #ffffff;
  background-color: #000000;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.day-status.locked {
  background-color: #a8adaf;
}

.day-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 0.75rem;
  line-height: 1.4;
}

.day-description {
  font-size: 0.95rem;
  color: #000000;
  opacity: 0.8;
  line-height: 1.5;
}

/* Responsive design */
@media (max-width: 768px) {
  .learning-status-container {
    flex-direction: column;
    gap: 1.5rem;
  }
  
  .learning-status-main,
  .learning-status-sidebar {
    width: 100%;
  }
  
  .learning-days-grid {
    grid-template-columns: 1fr;
  }
  
  .section-title {
    font-size: 1.5rem;
  }
  
  .learning-day-card {
    padding: 1.25rem;
  }
}
</style>
