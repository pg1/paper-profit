<script setup>
import { ref } from 'vue'
import StockPriceGraph from './ui/StockPriceGraph.vue'

const demoSymbol = ref('AAPL')
const demoPeriod = ref('1m')
const symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']

const handlePeriodChange = (period) => {
  demoPeriod.value = period
}
</script>

<template>
  <section class="section">
    <div class="section-header">
      <h1>Stock Price Graph Demo</h1>
      <p>Interactive stock price line graph with multiple time periods</p>
    </div>

    <div class="demo-controls">
      <div class="control-group">
        <label for="symbol-select">Select Symbol:</label>
        <select id="symbol-select" v-model="demoSymbol" class="select-input">
          <option v-for="symbol in symbols" :key="symbol" :value="symbol">
            {{ symbol }}
          </option>
        </select>
      </div>
    </div>

    <StockPriceGraph 
      :symbol="demoSymbol"
      :period="demoPeriod"
      :height="400"
      :showControls="true"
      @period-change="handlePeriodChange"
    />

    <div class="demo-info">
      <h3>Features:</h3>
      <ul>
        <li>Interactive line chart with hover tooltips</li>
        <li>Multiple time periods (1D, 1W, 1M, 3M, 6M, YTD, 1Y)</li>
        <li>Responsive design</li>
        <li>Loading and error states</li>
        <li>Price change calculations</li>
        <li>Volume data display</li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.section-header {
  text-align: center;
  margin-bottom: 2rem;
}

.section-header h1 {
  font-size: 2.5rem;
  font-weight: 700;
  color: #000000;
  margin-bottom: 0.5rem;
}

.section-header p {
  font-size: 1.1rem;
  color: #6c757d;
}

.demo-controls {
  display: flex;
  justify-content: center;
  margin-bottom: 2rem;
  gap: 2rem;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.control-group label {
  font-weight: 600;
  color: #000000;
}

.select-input {
  padding: 0.5rem 1rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  background-color: #ffffff;
  color: #000000;
  font-size: 1rem;
  cursor: pointer;
}

.select-input:focus {
  outline: none;
  border-color: #007bff;
}

.demo-info {
  background-color: #f8f9fa;
  padding: 2rem;
  border-radius: 8px;
  margin-top: 2rem;
  border: 1px solid #e9ecef;
}

.demo-info h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #000000;
  margin-bottom: 1rem;
}

.demo-info ul {
  list-style-type: none;
  padding: 0;
}

.demo-info li {
  padding: 0.5rem 0;
  color: #000000;
  position: relative;
  padding-left: 1.5rem;
}

.demo-info li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #28a745;
  font-weight: bold;
}

@media (max-width: 768px) {
  .section {
    padding: 1rem;
  }
  
  .section-header h1 {
    font-size: 2rem;
  }
  
  .demo-controls {
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }
}
</style>
