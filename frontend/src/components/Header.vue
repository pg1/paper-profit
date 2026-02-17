<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['navigate'])

const currentPage = ref('welcome')
const accounts = ref([])
const isLoading = ref(false)
const showPortfolioDropdown = ref(false)
const portfolioDropdownRef = ref(null)

const navigationItems = [
  { id: 'learning', label: 'Learning' },
  { id: 'list', label: 'List' },
  { id: 'welcome', label: 'Accounts' },
 // { id: 'portfolio', label: 'Portfolio' },
  { id: 'trade', label: 'Trade' },
  { id: 'strategy-list', label: 'Strategies' }
]

// Fetch accounts from API
/*const fetchAccounts = async () => {
  isLoading.value = true
  try {
    const response = await fetch('http://localhost:5000/api/accounts')
    if (response.ok) {
      const data = await response.json()
      accounts.value = data
    }
  } catch (err) {
    console.error('Error fetching accounts:', err)
  } finally {
    isLoading.value = false
  }
}*/

const handleNavigation = (page, params = {}) => {
  currentPage.value = page
  showPortfolioDropdown.value = false
  emit('navigate', page, params)
}

const isActive = computed(() => (page) => {
  return currentPage.value === page
})

/*const togglePortfolioDropdown = (event) => {
  event.stopPropagation() // Prevent event from bubbling up to document
  if (accounts.value.length > 1) {
    showPortfolioDropdown.value = !showPortfolioDropdown.value
  } else if (accounts.value.length === 1) {
    // If only one account, navigate directly to portfolio
    handleNavigation('portfolio', { accountName: accounts.value[0].account_id })
  } else {
    // If no accounts, navigate to welcome page to add accounts
    handleNavigation('welcome')
  }
}

const handleAccountSelect = (account) => {
  handleNavigation('portfolio', { accountName: account.account_id })
  showPortfolioDropdown.value = false
}

const closePortfolioDropdown = () => {
  showPortfolioDropdown.value = false
}

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  showPortfolioDropdown.value = false
}
*/
const props = defineProps({
  navigationParams: {
    type: Object,
    default: () => ({})
  }
})

const openSettings = () => {
  handleNavigation('settings')
}

/*onMounted(() => {
  fetchAccounts()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})*/
</script>

<template>
  
  <nav class="navbar">
        <div class="nav-container">
            <div class="logo">PaperProfit</div>
            <!-- TODO: fix hamburger menu -->
            <button class="hamburger" id="hamburger-btn" aria-label="Open menu" aria-expanded="false" aria-controls="nav-menu">
                <span class="bar"></span>
                <span class="bar"></span>
                <span class="bar"></span>
            </button>
            <ul class="nav-menu" id="nav-menu">
              <li 
                v-for="item in navigationItems" 
                :key="item.id"      
                :class="['nav-link', { active: isActive(item.id) }]"
                @click="handleNavigation(item.id)"
              >
                {{ item.label }}
               
                
              </li> 
            </ul>
            <button class="settings-button" @click="openSettings" aria-label="Settings">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
              </svg>
            </button>
        </div>
    </nav>

</template>

<style scoped>
  .nav-menu li:hover{
      cursor: pointer; 
  }

  .settings-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 4px;
    color: #333;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-left: 1rem;
  }

  .settings-button:hover {
    color: #ddd;
  }

  .settings-button:focus {
    outline: 2px solid #ddd;
    outline-offset: 2px;
  }

  /* Portfolio dropdown styles */
  .nav-link {
    position: relative;
  }

  .portfolio-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    min-width: 200px;
    z-index: 1000;
    margin-top: 0.5rem;
  }

  .dropdown-loading,
  .dropdown-empty {
    padding: 1rem;
    text-align: center;
    color: #666;
  }

  .dropdown-add-btn {
    background: #ddd;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    margin-top: 0.5rem;
    font-size: 0.9rem;
  }

  .dropdown-add-btn:hover {
    background: #0056b3;
  }

  .dropdown-accounts {
    max-height: 300px;
    overflow-y: auto;
  }

  .dropdown-account {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .dropdown-account:hover {
    background-color: #f8f9fa;
  }

  .dropdown-account:last-child {
    border-bottom: none;
  }

  .account-id {
    font-weight: 600;
    color: #333;
  }

  .account-balance {
    color: #28a745;
    font-size: 0.9rem;
  }
</style>
