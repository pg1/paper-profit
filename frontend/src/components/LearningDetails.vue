<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'

const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['navigate'])

const dayData = ref(null)
const quizData = ref(null)
const studyData = ref(null)
const exerciseData = ref(null)
const activeTab = ref('study')
const isLoading = ref(false)
const error = ref(null)
const userAnswers = ref({})
const showResults = ref(false)
const score = ref(0)
const imageError = ref(false)
const currentQuestionIndex = ref(0)
const quizCompleted = ref(false)
const exerciseContainer = ref(null)

// Extract day number from navigation params
const dayNumber = computed(() => {
  return props.navigationParams.day || 1
})

// Compute quiz title from quiz data (handles both 'chapter' and 'topic' fields)
const quizTitle = computed(() => {
  if (!quizData.value) return ''
  return quizData.value.chapter || quizData.value.topic || 'Quiz'
})

// Learning days data - will be fetched from API
const learningDays = ref([])

// Fetch learning days from API
const fetchLearningDays = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/learning-days')
    
    if (!response.ok) {
      throw new Error(`Failed to fetch learning days: ${response.status}`)
    }
    
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
  } catch (err) {
    console.error('Error fetching learning days:', err)
   
  }
}

// Fetch study data for the day
const fetchStudyData = async (day) => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch(`http://localhost:5000/api/learning-days/${day}/study`)
    
    if (!response.ok) {
      // If no study exists, set studyData to null
      if (response.status === 404) {
        studyData.value = null
        return
      }
      throw new Error(`Failed to fetch study: ${response.status}`)
    }
    
    const data = await response.json()
    studyData.value = data
  } catch (err) {
    console.error('Error fetching study:', err)
    // For demo purposes, we'll use mock study data if API fails
    studyData.value = getMockStudyData(day)
  } finally {
    isLoading.value = false
  }
}

// Mock study data for demo
const getMockStudyData = (day) => {
  return {
    day: day,
    content: `This is mock study content for Day ${day}. In the real application, this would be loaded from the study.txt file in the neumann/${day}/ directory.`
  }
}

// Fetch quiz data for the day
const fetchQuizData = async (day) => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch(`http://localhost:5000/api/learning-days/${day}/quiz`)
    
    if (!response.ok) {
      // If no quiz exists, set quizData to null
      if (response.status === 404) {
        quizData.value = null
        return
      }
      throw new Error(`Failed to fetch quiz: ${response.status}`)
    }
    
    const data = await response.json()
    quizData.value = data
  } catch (err) {
    console.error('Error fetching quiz:', err)
    // For demo purposes, we'll use mock quiz data if API fails
    //quizData.value = getMockQuizData(day)
  } finally {
    isLoading.value = false
  }
}

// Fetch exercise data for the day (legacy function - kept for compatibility)
const fetchExerciseData = async (day) => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch(`http://localhost:5000/api/learning-days/${day}/exercise`)
    
    if (!response.ok) {
      // If no exercise exists, set exerciseData to null
      if (response.status === 404) {
        exerciseData.value = null
        return
      }
      throw new Error(`Failed to fetch exercise: ${response.status}`)
    }
    
    const data = await response.json()
    exerciseData.value = data
  } catch (err) {
    console.error('Error fetching exercise:', err)
    // For demo purposes, we'll use mock exercise data if API fails
    exerciseData.value = getMockExerciseData(day)
  } finally {
    isLoading.value = false
  }
}

// Mock exercise data for demo
const getMockExerciseData = (day) => {
  return {
    day: day,
    content: `<div class="mock-exercise">
      <h2>Exercise for Day ${day}</h2>
      <p>This is a mock exercise. In the real application, this would be loaded from the exercise.html file in the neumann/${day}/ directory.</p>
      <p>Practice what you've learned by applying the concepts to real-world scenarios.</p>
    </div>`
  }
}

// Function to execute scripts from HTML content
const executeScriptsFromHTML = (htmlContent) => {
  if (!htmlContent) return
    
  // Create a temporary div to parse the HTML
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = htmlContent
  
  // Find all script tags
  const scripts = tempDiv.querySelectorAll('script')
  
  // Store references to added scripts for cleanup
  const addedScripts = []
  
  // Execute each script
  scripts.forEach((script) => {
    // Create a new script element
    const newScript = document.createElement('script')
    
    // Copy attributes
    Array.from(script.attributes).forEach(attr => {
      newScript.setAttribute(attr.name, attr.value)
    })
    
    // Handle inline scripts
    if (script.textContent) {
      // For inline scripts, we need to execute them with proper context
      try {
        // First, append the script to the DOM so it can access elements
        newScript.textContent = script.textContent
        
        // Add to document head to execute
        document.head.appendChild(newScript)
        addedScripts.push(newScript)
        
        // Remove immediately after execution to avoid cluttering the DOM
        setTimeout(() => {
          if (newScript.parentNode) {
            newScript.parentNode.removeChild(newScript)
          }
        }, 0)
      } catch (error) {
        console.error('Error executing inline script:', error)
      }
    } else if (script.src) {
      // For external scripts, we need to load them
      newScript.onload = () => console.log('External script loaded:', script.src)
      newScript.onerror = (error) => console.error('Error loading external script:', script.src, error)
      
      // Append to document head to load and execute
      document.head.appendChild(newScript)
      addedScripts.push(newScript)
    }
  })
  
  // Also need to handle event handlers in HTML (onclick, etc.)
  // These need to be re-attached after the DOM is updated
  
  // Wait for next tick to ensure DOM is updated with the HTML content
  nextTick(() => {
    // Find the exercise container in the DOM
    const exerciseContainer = document.querySelector('.exercise-html')
    if (exerciseContainer) {
      // Re-attach event handlers for elements with onclick attributes
      const elementsWithHandlers = exerciseContainer.querySelectorAll('[onclick]')
      elementsWithHandlers.forEach(element => {
        const onclickAttr = element.getAttribute('onclick')
        if (onclickAttr) {
          // Remove the onclick attribute to prevent duplicate handlers
          element.removeAttribute('onclick')
          
          // Attach the event listener
          element.addEventListener('click', () => {
            try {
              // Execute the onclick code
              // Use eval in a controlled way since we trust the content
              // (it comes from our own backend)
              const handler = new Function(onclickAttr)
              handler.call(element) // Call with element as 'this' context
            } catch (error) {
              console.error('Error executing onclick handler:', error)
            }
          })
        }
      })
      
      // Also handle other event attributes like onchange, oninput, etc.
      const eventAttributes = ['onchange', 'oninput', 'onsubmit', 'onload', 'onmouseover', 'onmouseout']
      eventAttributes.forEach(attr => {
        const elements = exerciseContainer.querySelectorAll(`[${attr}]`)
        elements.forEach(element => {
          const handlerCode = element.getAttribute(attr)
          if (handlerCode) {
            element.removeAttribute(attr)
            const eventName = attr.replace('on', '')
            element.addEventListener(eventName, () => {
              try {
                const handler = new Function(handlerCode)
                handler.call(element)
              } catch (error) {
                console.error(`Error executing ${attr} handler:`, error)
              }
            })
          }
        })
      })
    }
  })
  
  // Return the added scripts for cleanup
  return addedScripts
}

// Function to load exercise content with JavaScript execution
const loadExerciseContent = async (day) => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch(`http://localhost:5000/api/learning-days/${day}/exercise`)
    
    if (!response.ok) {
      // If no exercise exists, set exerciseData to null
      if (response.status === 404) {
        exerciseData.value = null
        return
      }
      throw new Error(`Failed to fetch exercise: ${response.status}`)
    }
    
    const data = await response.json()
    exerciseData.value = data
    
    // Wait for next tick to ensure DOM is updated
    await nextTick()
    
    // Execute scripts from the exercise content
    if (data.content) {
      // Wait a bit more to ensure DOM is fully rendered
      setTimeout(() => {
        executeScriptsFromHTML(data.content)
      }, 100)
    }
  } catch (err) {
    console.error('Error fetching exercise:', err)
    // For demo purposes, we'll use mock exercise data if API fails
    exerciseData.value = getMockExerciseData(day)
    
    // Wait for next tick and execute scripts for mock data too
    await nextTick()
    setTimeout(() => {
      if (exerciseData.value.content) {
        executeScriptsFromHTML(exerciseData.value.content)
      }
    }, 100)
  } finally {
    isLoading.value = false
  }
}

// Handle answer selection
const handleAnswerSelect = (questionId, answerIndex) => {
  userAnswers.value[questionId] = answerIndex
}

// Move to next question
const nextQuestion = () => {
  if (currentQuestionIndex.value < quizData.value.quiz.questions.length - 1) {
    currentQuestionIndex.value++
  } else {
    // Last question answered, show results
    submitQuiz()
  }
}

// Move to previous question
const prevQuestion = () => {
  if (currentQuestionIndex.value > 0) {
    currentQuestionIndex.value--
  }
}

// Get question ID (use index if no id field)
const getQuestionId = (question, index) => {
  return question.id || `question-${index}`
}

// Check if current question is answered
const isCurrentQuestionAnswered = computed(() => {
  if (!quizData.value) return false
  const question = quizData.value.quiz.questions[currentQuestionIndex.value]
  const questionId = getQuestionId(question, currentQuestionIndex.value)
  return userAnswers.value[questionId] !== undefined
})

// Get current question
const currentQuestion = computed(() => {
  if (!quizData.value) return null
  return quizData.value.quiz.questions[currentQuestionIndex.value]
})

// Get current question ID
const currentQuestionId = computed(() => {
  if (!currentQuestion.value) return null
  return getQuestionId(currentQuestion.value, currentQuestionIndex.value)
})

// Get total questions count
const totalQuestions = computed(() => {
  if (!quizData.value) return 0
  return quizData.value.quiz.questions.length
})

// Submit quiz and calculate score
const submitQuiz = async () => {
  if (!quizData.value) return
  
  let correctCount = 0
  const questions = quizData.value.quiz.questions
  
  questions.forEach((question, index) => {
    const questionId = getQuestionId(question, index)
    if (userAnswers.value[questionId] === question.correct) {
      correctCount++
    }
  })
  
  score.value = Math.round((correctCount / questions.length) * 100)
  showResults.value = true
  quizCompleted.value = true
  
  // Save success to settings if score is 80% or higher
  if (score.value >= 80) {
    await saveLearningJourneySuccess()
  }
}

// Save learning journey success to settings
const saveLearningJourneySuccess = async () => {
  try {
    const settingData = {
      name: 'learning_journey',
      category: 'System',
      parameters: JSON.stringify({ day: dayNumber.value }),
      is_active: false
    }
    
    // First, check if the setting already exists
    const checkResponse = await fetch(`http://localhost:5000/api/settings/learning_journey`)
    
    let response;
    if (checkResponse.ok) {
      // Setting exists, update it using PUT
      response = await fetch('http://localhost:5000/api/settings/learning_journey', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settingData)
      })
    } else {
      // Setting doesn't exist, create it using POST
      response = await fetch('http://localhost:5000/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settingData)
      })
    }
    
    if (!response.ok) {
      console.error('Failed to save learning journey success:', response.status)
    } else {
      console.log('Learning journey success saved to settings')
    }
  } catch (error) {
    console.error('Error saving learning journey success:', error)
  }
}

// Reset quiz
const resetQuiz = () => {
  userAnswers.value = {}
  showResults.value = false
  score.value = 0
  currentQuestionIndex.value = 0
  quizCompleted.value = false
}

// Navigate back to learning journey
const handleBack = () => {
  emit('navigate', 'learning')
}

// Get image URL for the day
const getImageUrl = (day) => {
  return `http://localhost:5000/api/learning-days/${day}/image`
}

// Handle image loading error
const handleImageError = () => {
  imageError.value = true
}

// Initialize component
onMounted(async () => {
  // Fetch learning days data first
  await fetchLearningDays()
  
  // Find the day data
  const day = learningDays.value.find(d => d.day === dayNumber.value)
  if (day) {
    dayData.value = day
  }
  
  // Fetch study data
  fetchStudyData(dayNumber.value)
  
  // Fetch quiz data
  fetchQuizData(dayNumber.value)
  
  // Load exercise content with JavaScript execution
  loadExerciseContent(dayNumber.value)
})

// Watch for changes in navigation params
import { watch } from 'vue'
watch(() => props.navigationParams, (newParams) => {
  if (newParams.day) {
    const day = learningDays.value.find(d => d.day === newParams.day)
    if (day) {
      dayData.value = day
    }
    fetchStudyData(newParams.day)
    fetchQuizData(newParams.day)
    // Load exercise content with JavaScript execution
    loadExerciseContent(newParams.day)
    resetQuiz()
    imageError.value = false
  }
}, { immediate: true })
</script>

<template>
  <!--<button 
    class="btn btn-gradient"
    @click="saveLearningJourneySuccess()"
  >
    Test
  </button>-->
  <div class="learning-details-page">
    <div class="card-container">
     
      <!-- Day header -->
      <div class="day-header-section" v-if="dayData">
        <div class="day-header-row">
          <div class="day-badge">Day {{ dayData.day }}</div> 
          <h1 class="day-title">{{ dayData.title }}</h1>
        </div>
        <!--<p class="day-description">{{ dayData.description }}</p>-->
      </div>
      
      <!-- Tabs navigation -->
      <div class="tabs-navigation">
        <button 
          class="tab-button" 
          :class="{ 'active': activeTab === 'study' }"
          @click="activeTab = 'study'"
        >
          Study
        </button>
        <button 
          class="tab-button" 
          :class="{ 'active': activeTab === 'quiz' }"
          @click="activeTab = 'quiz'"
        >
          Quiz
        </button>
        <button 
          class="tab-button" 
          :class="{ 'active': activeTab === 'action' }"
          @click="activeTab = 'action'"
        >
          Exercise
        </button>
      </div>
      
      <!-- Loading state -->
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Loading content...</p>
      </div>
      
      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button class="btn btn-gradient btn-small" @click="fetchStudyData(dayNumber)">Retry</button>
      </div>
      
      <!-- Study tab -->
      <div v-else-if="activeTab === 'study'" class="study-tab">
        <div class="study-content">
          <div class="study-text" v-if="studyData">
            <div class="study-text-content">
              <p v-for="(paragraph, index) in studyData.content.split('\n')" :key="index">
                {{ paragraph }}
              </p>
            </div>
          </div>
          
          <div class="study-image" v-if="dayNumber">
            <h3 class="image-title"></h3>
            <div class="image-container">
              <img 
                :src="getImageUrl(dayNumber)" 
                :alt="`Day ${dayNumber} illustration`"
                class="study-image-content"
                @error="handleImageError"
              />
              <div v-if="imageError" class="image-error">
                <p>Image not available for Day {{ dayNumber }}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div class="study-tips" v-if="!studyData">
          <h3>Study Tips:</h3>
          <ul>
            <li>Review the main concepts</li>
            <li>Take notes on key points</li>
            <li>Practice with paper trading</li>
            <li>Discuss with other learners</li>
          </ul>
        </div>
        
        <!-- Go to Quiz button -->
        <div class="study-actions" v-if="studyData">
          <button class="btn btn-gradient" @click="activeTab = 'quiz'">
            Go to Quiz
          </button>
        </div>
      </div>
      
      <!-- Quiz tab -->
      <div v-else-if="activeTab === 'quiz'" class="quiz-tab">
        <div v-if="quizData" class="quiz-section">
          
          
          <!-- Current question -->
          <div v-if="!showResults && currentQuestion" class="quiz-questions">
            <div class="question-card">
              <h3 class="question-text">{{ currentQuestion.question }}</h3>
              <div class="options-grid">
                <button
                  v-for="(option, index) in currentQuestion.options"
                  :key="index"
                  class="option-button"
                  :class="{
                    'selected': userAnswers[currentQuestionId] === index
                  }"
                  @click="handleAnswerSelect(currentQuestionId, index)"
                >
                  <span class="option-letter">{{ String.fromCharCode(65 + index) }}</span>
                  <span class="option-text">{{ option }}</span>
                </button>
              </div>
            </div>
          </div>
          
          <!-- Quiz navigation -->
          <div v-if="!showResults" class="quiz-navigation">
            <button 
              class="btn btn-outline"
              @click="prevQuestion"
              :disabled="currentQuestionIndex === 0"
            >
              Previous
            </button>
            <!-- Quiz progress indicator - dotted line with one dot per question -->
          <div class="quiz-progress" v-if="!showResults">
            <div class="progress-dots">
              <div 
                v-for="index in totalQuestions" 
                :key="index"
                class="progress-dot"
                :class="{
                  'completed': index <= currentQuestionIndex,
                  'current': index === currentQuestionIndex + 1,
                  'upcoming': index > currentQuestionIndex + 1
                }"
                :title="`Question ${index}`"
              ></div>
            </div>
            <div class="progress-text">
              Question {{ currentQuestionIndex + 1 }} of {{ totalQuestions }}
            </div>
          </div>
            <button 
              class="btn btn-gradient"
              @click="nextQuestion"
              :disabled="!isCurrentQuestionAnswered"
            >
              {{ currentQuestionIndex === totalQuestions - 1 ? 'Finish Quiz' : 'Next' }}
            </button>
          </div>
          
          <!-- Quiz results -->
          <div v-if="showResults" class="quiz-results">
            <div class="score-display">
              <h3>Your Score: {{ score }}%</h3>
              <p v-if="score >= 80" class="score-message success">Excellent! You've mastered this lesson.</p>
              <p v-else-if="score >= 60" class="score-message warning">Good job! Review the material and try again.</p>
              <p v-else class="score-message error">Keep learning! Review the lesson and retry the quiz.</p>
            </div>
            
            <!-- Question-by-question review -->
            <div class="questions-review">
              <h4>Review Your Answers:</h4>
              <div 
                v-for="(question, qIndex) in quizData.quiz.questions" 
                :key="getQuestionId(question, qIndex)"
                class="review-item"
                :class="{
                  'correct': userAnswers[getQuestionId(question, qIndex)] === question.correct,
                  'incorrect': userAnswers[getQuestionId(question, qIndex)] !== question.correct
                }"
              >
                <div class="review-question">
                  <span class="review-number">{{ qIndex + 1 }}.</span>
                  <span class="review-text">{{ question.question }}</span>
                  <span class="review-status">
                    <span v-if="userAnswers[getQuestionId(question, qIndex)] === question.correct" class="correct-indicator">✓ Correct</span>
                    <span v-else class="incorrect-indicator">✗ Incorrect</span>
                  </span>
                </div>
                <div class="review-answer">
                  <strong>Your answer:</strong> 
                  <span v-if="userAnswers[getQuestionId(question, qIndex)] !== undefined">
                    {{ String.fromCharCode(65 + userAnswers[getQuestionId(question, qIndex)]) }}. {{ question.options[userAnswers[getQuestionId(question, qIndex)]] }}
                  </span>
                  <span v-else class="not-answered">Not answered</span>
                </div>
                <div class="review-correct-answer" v-if="userAnswers[getQuestionId(question, qIndex)] !== question.correct">
                  <strong>Correct answer:</strong> 
                  {{ String.fromCharCode(65 + question.correct) }}. {{ question.options[question.correct] }}
                </div>
                <div class="review-explanation">
                  <strong>Explanation:</strong> {{ question.explanation }}
                </div>
              </div>
            </div>
            
            <div class="results-actions">
              <button class="btn btn-outline" @click="score >= 80 ? activeTab = 'action' : resetQuiz()">
                {{ score >= 80 ? 'Go To Exercise' : 'Try Again' }}
              </button>
            </div>
          </div>
        </div>
        
        <!-- No quiz available -->
        <div v-else class="no-quiz-section">
          <div class="no-quiz-card">
            <h3>No Quiz Available</h3>
            <p>This lesson doesn't have a quiz yet. Focus on understanding the concepts and practice applying them.</p>
            <div class="study-tips">
              <h4>Study Tips:</h4>
              <ul>
                <li>Review the main concepts</li>
                <li>Take notes on key points</li>
                <li>Practice with paper trading</li>
                <li>Discuss with other learners</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Action tab (Exercise) -->
      <div v-else-if="activeTab === 'action'" class="action-tab">
        <div class="exercise-content" v-if="exerciseData">
          <div class="exercise-html" v-html="exerciseData.content"></div>
        </div>
        <div v-else class="no-exercise-section">
          <div class="no-exercise-card">
            <h3>No Exercise Available</h3>
            <p>This lesson doesn't have an exercise yet. Focus on understanding the concepts and practice applying them.</p>
            
          </div>
        </div>
      </div>
    </div>
           <!-- Back button -->
      <button class="btn-back" @click="handleBack">← Back to Learning Journey</button>

  </div>
</template>

<style scoped>
.learning-details-page {
}

.card-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

/* Back button */
.btn-back {
  background: none;
  border: none;
  color: #000000;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.5rem 0;
  margin-bottom: 2rem;
  transition: opacity 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-back:hover {
  opacity: 0.6;
}

/* Day header */
.day-header-section {
  margin-bottom: 2.5rem;
}

.day-header-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.day-badge {
  display: inline-block;
  background-color: #000000;
  color: #ffffff;
  font-size: 0.875rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  flex-shrink: 0;
}

.day-title {
  font-size: 2rem;
  font-weight: 700;
  color: #000000;
  line-height: 1.3;
  margin: 0;
}

.day-description {
  font-size: 1.125rem;
  color: #000000;
  opacity: 0.8;
  line-height: 1.6;
  max-width: 800px;
}

/* Tabs navigation */
.tabs-navigation {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2.5rem;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 0.5rem;
}

.tab-button {
  background: none;
  border: none;
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #000000;
  opacity: 0.6;
  cursor: pointer;
  border-radius: 6px 6px 0 0;
  transition: all 0.2s ease;
  position: relative;
}

.tab-button:hover {
  opacity: 0.8;
  background-color: #f9f9f9;
}

.tab-button.active {
  opacity: 1;
  color: #000000;
}

.tab-button.active::after {
  content: '';
  position: absolute;
  bottom: -0.5rem;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #000000;
}

/* Loading state */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid #f0f0f0;
  border-top-color: #000000;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1.5rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-state p {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
}

/* Error state */
.error-state {
  padding: 3rem 2rem;
  text-align: center;
  background-color: #f9f9f9;
  border-radius: 8px;
  margin: 2rem 0;
}

.error-message {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
  margin-bottom: 1.5rem;
}

/* Tab content */
.study-tab,
.quiz-tab,
.action-tab {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Study tab */
.study-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  margin-bottom: 2rem;
}

.study-text {
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 2rem;
}

.study-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #000000;
  margin-bottom: 1.5rem;
}

.study-text-content {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
  line-height: 1.6;
}

.study-text-content p {
  margin-bottom: 1rem;
}

.study-text-content p:last-child {
  margin-bottom: 0;
}

.study-image {
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 2rem;
}

.image-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1.5rem;
}

.image-container {
  width: 100%;
  background-color: #f9f9f9;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.study-image-content {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.image-error {
  padding: 2rem;
  text-align: center;
  color: #000000;
  opacity: 0.6;
}

.study-tips {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 2rem;
  margin-top: 2rem;
}

.study-tips h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1rem;
}

.study-tips ul {
  list-style-type: none;
  padding-left: 0;
}

.study-tips li {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
  margin-bottom: 0.75rem;
  padding-left: 1.5rem;
  position: relative;
}

.study-tips li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #000000;
  font-size: 1.5rem;
  line-height: 1;
}

/* Study actions */
.study-actions {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #f0f0f0;
}

.study-actions .btn {
  padding: 0.875rem 2rem;
  font-size: 1rem;
  font-weight: 600;
}

/* Quiz tab */
.quiz-section {
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 2rem;
}

.quiz-header {
  margin-bottom: 2rem;
}

.quiz-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #000000;
  margin-bottom: 0.5rem;
}

.quiz-instructions {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
}

/* Quiz progress - dotted line */
.quiz-progress {
  margin-bottom: 2rem;
}

.progress-dots {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.progress-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #f0f0f0;
  transition: all 0.3s ease;
  position: relative;
}

.progress-dot.completed {
  background-color: #000000;
  transform: scale(1.1);
}

.progress-dot.current {
  background-color: #000000;
  transform: scale(1.3);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1);
}

.progress-dot.upcoming {
  background-color: #f0f0f0;
}

.progress-dot:hover {
  transform: scale(1.2);
}

.progress-text {
  font-size: 0.875rem;
  color: #000000;
  opacity: 0.8;
  text-align: center;
  margin-top: 0.5rem;
}

.quiz-questions {
  margin-bottom: 2rem;
}

.question-card {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.question-card:last-child {
  margin-bottom: 0;
}

.question-text {
  font-size: 1.125rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1.25rem;
}

.options-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
}

.option-button {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background-color: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.option-button:hover:not(:disabled) {
  border-color: #000000;
  background-color: #f9f9f9;
}

.option-button.selected {
  border-color: #000000;
  background-color: #f0f0f0;
}

.option-button.correct {
  border-color: #10b981;
  background-color: rgba(16, 185, 129, 0.1);
}

.option-button.incorrect {
  border-color: #ef4444;
  background-color: rgba(239, 68, 68, 0.1);
}

.option-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.option-letter {
  font-size: 0.875rem;
  font-weight: 600;
  color: #000000;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f0f0;
  border-radius: 4px;
}

.option-text {
  flex: 1;
  font-size: 0.95rem;
  color: #000000;
}

.correct-indicator,
.incorrect-indicator {
  font-size: 1.25rem;
  font-weight: 700;
}

.correct-indicator {
  color: #10b981;
}

.incorrect-indicator {
  color: #ef4444;
}

/* Quiz navigation */
.quiz-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #f0f0f0;
}

.btn {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.btn-gradient {
  background-color: #000000;
  color: #ffffff;
  border: none;
}

.btn-gradient:hover:not(:disabled) {
  opacity: 0.8;
}

.btn-gradient:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-outline {
  background-color: transparent;
  color: #000000;
  border: 1px solid #000000;
}

.btn-outline:hover {
  background-color: #000000;
  color: #ffffff;
}

.btn-small {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

/* Quiz results */
.quiz-results {
  text-align: left;
}

.score-display {
  margin-bottom: 2rem;
  text-align: center;
}

.score-display h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #000000;
  margin-bottom: 0.75rem;
}

.score-message {
  font-size: 1rem;
  margin-bottom: 1.5rem;
}

.score-message.success {
  color: #10b981;
}

.score-message.warning {
  color: #f59e0b;
}

.score-message.error {
  color: #ef4444;
}

/* Questions review */
.questions-review {
  margin-bottom: 2rem;
}

.questions-review h4 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1.5rem;
}

.review-item {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  border-left: 4px solid #e0e0e0;
}

.review-item.correct {
  border-left-color: #10b981;
}

.review-item.incorrect {
  border-left-color: #ef4444;
}

.review-question {
  display: flex;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.review-number {
  font-weight: 600;
  color: #000000;
  margin-right: 0.5rem;
  flex-shrink: 0;
}

.review-text {
  flex: 1;
  font-weight: 600;
  color: #000000;
}

.review-status {
  margin-left: 1rem;
  flex-shrink: 0;
}

.review-answer,
.review-correct-answer,
.review-explanation {
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
  color: #000000;
  opacity: 0.8;
}

.review-answer strong,
.review-correct-answer strong,
.review-explanation strong {
  color: #000000;
  opacity: 1;
  margin-right: 0.5rem;
}

.not-answered {
  color: #ef4444;
  font-style: italic;
}

.results-actions {
  text-align: center;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #f0f0f0;
}

/* No quiz section */
.no-quiz-section {
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
}

.no-quiz-card h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #000000;
  margin-bottom: 1rem;
}

.no-quiz-card p {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
  margin-bottom: 2rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

/* Action tab (Exercise) */
.exercise-content {
  background-color: #ffffff;
  padding: 0 2rem;
  overflow: hidden;
}

.exercise-html {
  width: 100%;
}


.exercise-html :deep(body) {
  font-family: inherit;
  background: transparent;
}

.exercise-html :deep(.container) {
  max-width: 100%;
  padding: 2rem;
}

/* No exercise section */
.no-exercise-section {
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
}

.no-exercise-card h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #000000;
  margin-bottom: 1rem;
}

.no-exercise-card p {
  font-size: 1rem;
  color: #000000;
  opacity: 0.8;
  margin-bottom: 2rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

/* Responsive design */
@media (max-width: 768px) {
  .card-container {
    padding: 0 1rem;
  }
  
  .day-title {
    font-size: 1.5rem;
  }
  
  .day-description {
    font-size: 1rem;
  }
  
  .tabs-navigation {
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .tab-button {
    width: 100%;
    text-align: left;
    border-radius: 6px;
  }
  
  .tab-button.active::after {
    display: none;
  }
  
  .study-content {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
  
  .action-cards {
    grid-template-columns: 1fr;
  }
}
</style>
