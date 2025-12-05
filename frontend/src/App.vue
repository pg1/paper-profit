<script setup>
import { ref } from 'vue'
import Header from './components/Header.vue'
import WelcomePage from './components/WelcomePage.vue'
import AccountAdd from './components/AccountAdd.vue'
import AccountList from './components/AccountList.vue'
import Portfolio from './components/Portfolio.vue'
import AssetBuy from './components/AssetBuy.vue'
import AssetSell from './components/AssetSell.vue'
import AssetTransaction from './components/AssetTransaction.vue'
import StrategyList from './components/StrategyList.vue'
import StrategyAdd from './components/StrategyAdd.vue'
import StrategyEdit from './components/StrategyEdit.vue'
import Settings from './components/Settings.vue'
import InstrumentDetail from './components/InstrumentDetail.vue'
import AccountEdit from './components/AccountEdit.vue'
import Guide from './components/Guide.vue'

const currentPage = ref('welcome')
const navigationParams = ref({})

const handleNavigation = (page, params = {}) => {
  currentPage.value = page
  navigationParams.value = params
}
</script>

<template>
    
    <Header @navigate="handleNavigation" />

    <main class="container">
        <WelcomePage 
          v-if="currentPage === 'welcome'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <AccountAdd 
          v-else-if="currentPage === 'account-add'" 
          @navigate="handleNavigation"
        />
        <AccountList 
          v-else-if="currentPage === 'account-list'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <AccountEdit 
          v-else-if="currentPage === 'account-edit'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <Portfolio 
          v-else-if="currentPage === 'portfolio'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <AssetBuy 
          v-else-if="currentPage === 'asset-buy'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <AssetSell 
          v-else-if="currentPage === 'asset-sell'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <AssetTransaction 
          v-else-if="currentPage === 'asset-transaction'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <StrategyList 
          v-else-if="currentPage === 'strategy-list'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <StrategyAdd 
          v-else-if="currentPage === 'strategy-add'" 
          @navigate="handleNavigation"
        />
        <StrategyEdit 
          v-else-if="currentPage === 'strategy-edit'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
        <Settings 
          v-else-if="currentPage === 'settings'" 
          @navigate="handleNavigation"
        />
        <InstrumentDetail 
          v-else-if="currentPage === 'instrument-detail'" 
          @navigate="handleNavigation"
          :navigation-params="navigationParams"
        />
    </main>

    <Guide />

</template>
