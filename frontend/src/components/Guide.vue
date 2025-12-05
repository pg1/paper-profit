<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// Reactive state
const isVisible = ref(false)
const currentChapter = ref(0)
const currentSection = ref(0)
const guideData = ref(null)
const isLoading = ref(true)
const isChaptersOpen = ref(false)
const isSectionsOpen = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const showSearchResults = ref(false)
const pendingSection = ref(null)

// Computed properties
const chapters = computed(() => guideData.value?.chapters || [])
const currentChapterData = computed(() => chapters.value[currentChapter.value] || {})
const sections = computed(() => currentChapterData.value.sections || [])
const currentSectionData = computed(() => sections.value[currentSection.value] || {})

// Methods
const toggleGuide = () => {
  isVisible.value = !isVisible.value
}

// Open guide to a specific section by keyword or title
const openGuideToSection = (sectionParam) => {
  if (!guideData.value) {
    // Store the section parameter to apply once data is loaded
    pendingSection.value = sectionParam
    // Still open the guide
    isVisible.value = true
    return
  }
  
  const param = sectionParam.toLowerCase().trim()
  
  // Search through chapters and sections
  for (let chapterIndex = 0; chapterIndex < guideData.value.chapters.length; chapterIndex++) {
    const chapter = guideData.value.chapters[chapterIndex]
    
    // Check chapter keywords
    if (chapter.keywords?.some(keyword => keyword.toLowerCase().includes(param))) {
      currentChapter.value = chapterIndex
      currentSection.value = 0
      isVisible.value = true
      return
    }
    
    // Check sections within chapter
    for (let sectionIndex = 0; sectionIndex < chapter.sections.length; sectionIndex++) {
      const section = chapter.sections[sectionIndex]
      
      // Check section title
      if (section.title.toLowerCase().includes(param)) {
        currentChapter.value = chapterIndex
        currentSection.value = sectionIndex
        isVisible.value = true
        return
      }
      
      // Check section keywords
      if (section.keywords?.some(keyword => keyword.toLowerCase().includes(param))) {
        currentChapter.value = chapterIndex
        currentSection.value = sectionIndex
        isVisible.value = true
        return
      }
    }
  }
  
  // If no match found, just open the guide
  isVisible.value = true
}

const selectChapter = (index) => {
  currentChapter.value = index
  currentSection.value = 0
  isChaptersOpen.value = false
}

const selectSection = (index) => {
  currentSection.value = index
  isSectionsOpen.value = false
}

const nextSection = () => {
  if (currentSection.value < sections.value.length - 1) {
    currentSection.value++
  } else if (currentChapter.value < chapters.value.length - 1) {
    currentChapter.value++
    currentSection.value = 0
  }
}

const prevSection = () => {
  if (currentSection.value > 0) {
    currentSection.value--
  } else if (currentChapter.value > 0) {
    currentChapter.value--
    currentSection.value = sections.value.length - 1
  }
}

const toggleChapters = () => {
  isChaptersOpen.value = !isChaptersOpen.value
  if (isChaptersOpen.value) {
    isSectionsOpen.value = false
  }
}

const toggleSections = () => {
  isSectionsOpen.value = !isSectionsOpen.value
  if (isSectionsOpen.value) {
    isChaptersOpen.value = false
  }
}

// Simple markdown to HTML converter for bold text
const markdownToHtml = (text) => {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    //.replace(/\n/g, '<br>')
}

// Search functionality
const performSearch = () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    showSearchResults.value = false
    return
  }

  const query = searchQuery.value.toLowerCase().trim()
  const results = []

  // Search through chapters and sections
  guideData.value?.chapters?.forEach((chapter, chapterIndex) => {
    // Search chapter title
    if (chapter.title.toLowerCase().includes(query)) {
      results.push({
        type: 'chapter',
        chapterIndex,
        sectionIndex: null,
        chapter,
        section: null,
        match: 'title'
      })
    }

    // Search chapter keywords
    if (chapter.keywords?.some(keyword => keyword.toLowerCase().includes(query))) {
      results.push({
        type: 'chapter',
        chapterIndex,
        sectionIndex: null,
        chapter,
        section: null,
        match: 'keywords'
      })
    }

    // Search sections within chapter
    chapter.sections?.forEach((section, sectionIndex) => {
      // Search section title
      if (section.title.toLowerCase().includes(query)) {
        results.push({
          type: 'section',
          chapterIndex,
          sectionIndex,
          chapter,
          section,
          match: 'title'
        })
      }

      // Search section keywords
      if (section.keywords?.some(keyword => keyword.toLowerCase().includes(query))) {
        results.push({
          type: 'section',
          chapterIndex,
          sectionIndex,
          chapter,
          section,
          match: 'keywords'
        })
      }

      // Search section description
      if (section.description?.toLowerCase().includes(query)) {
        results.push({
          type: 'section',
          chapterIndex,
          sectionIndex,
          chapter,
          section,
          match: 'description'
        })
      }
    })
  })

  searchResults.value = results
  showSearchResults.value = results.length > 0
}

// Navigate to search result
const navigateToResult = (result) => {
  currentChapter.value = result.chapterIndex
  if (result.type === 'section') {
    currentSection.value = result.sectionIndex
  } else {
    currentSection.value = 0
  }
  searchQuery.value = ''
  searchResults.value = []
  showSearchResults.value = false
  isChaptersOpen.value = false
  isSectionsOpen.value = false
}

// Handle search input
const handleSearchInput = () => {
  if (searchQuery.value.trim()) {
    performSearch()
  } else {
    searchResults.value = []
    showSearchResults.value = false
  }
}

// Load guide data
const loadGuideData = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/guide')
    if (response.ok) {
      guideData.value = await response.json()
      
      // If there's a pending section to open, apply it now
      if (pendingSection.value) {
        const sectionParam = pendingSection.value
        pendingSection.value = null
        // Use setTimeout to ensure the guide data is fully processed
        setTimeout(() => {
          openGuideToSection(sectionParam)
        }, 100)
      }
    } else {
      console.error('Failed to load guide data')
    }
  } catch (error) {
    console.error('Error loading guide data:', error)
  } finally {
    isLoading.value = false
  }
}

// Handle open-guide event
const handleOpenGuideEvent = (event) => {
  const { section } = event.detail || {}
  if (section) {
    openGuideToSection(section)
  }
}

onMounted(() => {
  loadGuideData()
  window.addEventListener('open-guide', handleOpenGuideEvent)
})

onUnmounted(() => {
  window.removeEventListener('open-guide', handleOpenGuideEvent)
})
</script>

<template>
  <!-- Floating Guide Button -->
  <button 
    class="guide-toggle-btn"
    @click="toggleGuide"
    :class="{ 'guide-toggle-btn--active': isVisible }"
  >
    <span class="guide-toggle-icon">📚</span>
    <span class="guide-toggle-text">Guide</span>
  </button>

  
  <div class="guide-panel" :class="{ 'guide-panel--visible': isVisible }">
    <!-- Header -->
    <div class="guide-header">
      <h2 class="guide-title">
        {{ guideData?.title || 'Investment Guide' }}
      </h2>
      
      <!-- Search Bar in Header -->
      <div class="guide-search-container">
        <div class="guide-search">
          <input
            type="text"
            v-model="searchQuery"
            @input="handleSearchInput"
            @focus="showSearchResults = searchResults.length > 0"
            placeholder="Search guide by keyword..."
            class="guide-search-input"
          />
          
          <!-- Search Results Dropdown -->
          <div class="guide-search-results" v-if="showSearchResults && searchResults.length > 0">
            <div class="guide-search-results-header">
              <span class="guide-search-results-count">
                {{ searchResults.length }} result{{ searchResults.length > 1 ? 's' : '' }} found
              </span>
            </div>
            <div class="guide-search-results-list">
              <button
                v-for="(result, index) in searchResults"
                :key="index"
                class="guide-search-result-item"
                @click="navigateToResult(result)"
              >
                <div class="guide-search-result-type">
                  <span class="guide-search-result-badge" :class="result.type">
                    {{ result.type === 'chapter' ? 'Chapter' : 'Section' }}
                  </span>
                </div>
                <div class="guide-search-result-content">
                  <div class="guide-search-result-title">
                    {{ result.type === 'chapter' ? result.chapter.title : result.section.title }}
                  </div>
                  <div class="guide-search-result-path">
                    {{ result.chapter.number }}. {{ result.chapter.title }}
                    <span v-if="result.type === 'section'">
                      → {{ result.section.number }}. {{ result.section.title }}
                    </span>
                  </div>
                  <div class="guide-search-result-match">
                    Matched in: {{ result.match }}
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      <button class="guide-close-btn" @click="toggleGuide">
        ✕
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="guide-loading">
      <div class="guide-loading-spinner"></div>
      <p>Loading guide...</p>
    </div>

    <!-- Content -->
    <div v-else class="guide-content">

      <!-- Chapter Dropdown -->
      <div class="guide-chapters-dropdown">
        <button class="guide-dropdown-btn" @click="toggleChapters">
          <span class="guide-dropdown-text">
            {{ currentChapterData.number }}. {{ currentChapterData.title }}
          </span>
          <span class="guide-dropdown-arrow" :class="{ 'guide-dropdown-arrow--open': isChaptersOpen }">
            ▼
          </span>
        </button>
        
        <div class="guide-dropdown-list" v-if="isChaptersOpen">
          <button
            v-for="(chapter, index) in chapters"
            :key="chapter.number"
            class="guide-dropdown-item"
            :class="{ 'guide-dropdown-item--active': currentChapter === index }"
            @click="selectChapter(index)"
          >
            <span class="guide-chapter-number">{{ chapter.number }}.</span>
            <span class="guide-chapter-title">{{ chapter.title }}</span>
          </button>
        </div>
      </div>

      <!-- Section Dropdown -->
      <div class="guide-sections-dropdown">
        <button class="guide-dropdown-btn" @click="toggleSections">
          <span class="guide-dropdown-text">
            {{ currentSectionData.title || 'Select Section' }}
          </span>
          <span class="guide-dropdown-arrow" :class="{ 'guide-dropdown-arrow--open': isSectionsOpen }">
            ▼
          </span>
        </button>
        
        <div class="guide-dropdown-list" v-if="isSectionsOpen">
          <button
            v-for="(section, index) in sections"
            :key="section.title"
            class="guide-dropdown-item"
            :class="{ 'guide-dropdown-item--active': currentSection === index }"
            @click="selectSection(index)"
          >
            {{ section.title }}
          </button>
        </div>
      </div>

      <!-- Current Section Content -->
      <div class="guide-section-content">
        <div class="guide-section-header">
          <h4 class="guide-section-title">{{ currentSectionData.title }}</h4>
          <div class="guide-section-navigation">
            <button 
              class="guide-nav-btn guide-nav-btn--prev"
              @click="prevSection"
              :disabled="currentChapter === 0 && currentSection === 0"
            >
              ← Previous
            </button>
            <button 
              class="guide-nav-btn guide-nav-btn--next"
              @click="nextSection"
              :disabled="currentChapter === chapters.length - 1 && currentSection === sections.length - 1"
            >
              Next →
            </button>
          </div>
        </div>

        <div class="guide-section-description">
          {{ currentSectionData.description }}
        </div>

        <div 
          class="guide-section-body"
          v-html="markdownToHtml(currentSectionData.content)"
        ></div>

        <!-- Keywords -->
        <div v-if="currentSectionData.keywords" class="guide-keywords">
          <strong>Keywords:</strong>
          <div class="guide-keywords-list">
            <span 
              v-for="keyword in currentSectionData.keywords" 
              :key="keyword"
              class="guide-keyword"
            >
              {{ keyword }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Floating Toggle Button */
.guide-toggle-btn {
  position: fixed;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  background: #000000;
  color: #ffffff;
  border: none;
  border-radius: 8px 0 0 8px;
  padding: 1rem 0.75rem;
  cursor: pointer;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.guide-toggle-btn:hover {
  background: #333333;
  padding-right: 1rem;
}

.guide-toggle-btn--active {
  background: #333333;
}

.guide-toggle-icon {
  font-size: 1.25rem;
}

.guide-toggle-text {
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

/* Overlay */
.guide-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1998;
}

/* Guide Panel */
.guide-panel {
  position: fixed;
  top: 0;
  right: -600px;
  width: 600px;
  height: 100vh;
  background: #ffffff;
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.1);
  z-index: 1999;
  transition: right 0.3s ease;
  display: flex;
  flex-direction: column;
}

.guide-panel--visible {
  right: 0;
}

/* Header */
.guide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #f0f0f0;
  background: #f9f9f9;
  gap: 1rem;
}

.guide-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #000000;
  margin: 0;
  flex-shrink: 0;
}

.guide-close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.25rem;
  color: #666666;
  transition: color 0.2s ease;
  flex-shrink: 0;
}

.guide-close-btn:hover {
  color: #000000;
}

/* Header Search Container */
.guide-header .guide-search-container {
  padding: 0;
  border-bottom: none;
  background: transparent;
  flex: 1;
  max-width: 300px;
}

.guide-header .guide-search-input {
  width: 100%;
  padding: 0.5rem 2rem 0.5rem 0.75rem;
  font-size: 0.8rem;
}

.guide-header .guide-search-icon {
  right: 0.75rem;
  font-size: 0.9rem;
}

/* Loading State */
.guide-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #666666;
}

.guide-loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f0f0f0;
  border-top: 3px solid #000000;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Content Layout */
.guide-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Dropdown Styles */
.guide-chapters-dropdown,
.guide-sections-dropdown {
  position: relative;
  border-bottom: 1px solid #f0f0f0;
  background: #f9f9f9;
}

.guide-dropdown-btn {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  background: none;
  border: none;
  padding: 1rem 1.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: #000000;
  transition: background-color 0.2s ease;
}

.guide-dropdown-btn:hover {
  background: #e8e8e8;
}

.guide-dropdown-text {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guide-dropdown-arrow {
  transition: transform 0.2s ease;
  font-size: 0.75rem;
  color: #666666;
}

.guide-dropdown-arrow--open {
  transform: rotate(180deg);
}

.guide-dropdown-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-top: none;
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.guide-dropdown-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  width: 100%;
  background: none;
  border: none;
  padding: 0.75rem 1.5rem;
  text-align: left;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s ease;
  border-bottom: 1px solid #f0f0f0;
}

.guide-dropdown-item:last-child {
  border-bottom: none;
}

.guide-dropdown-item:hover {
  background: #f5f5f5;
}

.guide-dropdown-item--active {
  background: #000000;
  color: #ffffff;
}

.guide-chapter-number {
  font-weight: 600;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.guide-chapter-title {
  font-size: 0.875rem;
  line-height: 1.4;
}

/* Section Content */
.guide-section-content {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.guide-section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.guide-section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #000000;
  margin: 0;
  flex: 1;
}

.guide-section-navigation {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.guide-nav-btn {
  background: #f0f0f0;
  border: 1px solid #e0e0e0;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s ease;
}

.guide-nav-btn:hover:not(:disabled) {
  background: #e0e0e0;
}

.guide-nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.guide-section-description {
  font-size: 0.95rem;
  color: #666666;
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

.guide-section-body {
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.guide-section-body :deep(p) {
  margin-bottom: 1rem;
}

.guide-section-body :deep(strong) {
  font-weight: 600;
}

.guide-section-body :deep(em) {
  font-style: italic;
}



/* Keywords */
.guide-keywords {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #f0f0f0;
}

.guide-keywords strong {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #666666;
}

.guide-keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.guide-keyword {
  background: #f0f0f0;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  color: #666666;
}

/* Responsive Design */
@media (max-width: 768px) {
  .guide-panel {
    width: 100%;
    right: -100%;
  }

  .guide-toggle-btn {
    padding: 0.75rem 0.5rem;
    font-size: 0.75rem;
  }

  .guide-toggle-icon {
    font-size: 1rem;
  }
}

.guide-section-body :deep(li) {
  margin-left:25px;
}

/* Search Styles */
.guide-search-container {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #f0f0f0;
  background: #f9f9f9;
}

.guide-search {
  position: relative;
}

.guide-search-input {
  width: 100%;
  padding: 0.75rem 2.5rem 0.75rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.875rem;
  background: #ffffff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.guide-search-input:focus {
  outline: none;
  border-color: #000000;
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1);
}

.guide-search-input::placeholder {
  color: #999999;
}

.guide-search-icon {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #666666;
  font-size: 1rem;
}

.guide-search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 0 0 8px 8px;
  max-height: 320px;
  overflow-y: auto;
  z-index: 20;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  margin-top: 0.25rem;
}

.guide-search-results-header {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f0f0f0;
  background: #f9f9f9;
}

.guide-search-results-count {
  font-size: 0.75rem;
  color: #666666;
  font-weight: 500;
}

.guide-search-results-list {
  max-height: 250px;
  overflow-y: auto;
}

.guide-search-result-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  width: 100%;
  background: none;
  border: none;
  padding: 1rem;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-bottom: 1px solid #f0f0f0;
}

.guide-search-result-item:last-child {
  border-bottom: none;
}

.guide-search-result-item:hover {
  background: #f5f5f5;
}

.guide-search-result-type {
  flex-shrink: 0;
}

.guide-search-result-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.guide-search-result-badge.chapter {
  background: #e3f2fd;
  color: #1976d2;
}

.guide-search-result-badge.section {
  background: #e8f5e8;
  color: #2e7d32;
}

.guide-search-result-content {
  flex: 1;
  min-width: 0;
}

.guide-search-result-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 0.25rem;
  line-height: 1.3;
}

.guide-search-result-path {
  font-size: 0.75rem;
  color: #666666;
  margin-bottom: 0.25rem;
  line-height: 1.3;
}

.guide-search-result-match {
  font-size: 0.7rem;
  color: #999999;
  text-transform: capitalize;
}

/* Responsive Design for Search */
@media (max-width: 768px) {
  .guide-search-container {
    padding: 1rem;
  }
  
  .guide-search-results {
    max-height: 250px;
  }
}
</style>
