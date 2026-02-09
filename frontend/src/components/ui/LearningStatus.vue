<template>
  <div class="chart-container">
    <svg
      class="learning-chart"
      width="100%"
      height="100%"
      viewBox="0 0 220 130"
      preserveAspectRatio="none"
    >
      <!-- Horizontal lines (12 lines) -->
      <g class="horizontal-lines">
        <line
          v-for="i in 12"
          :key="'h' + i"
          x1="0"
          :y1="i * 10"
          x2="215"
          :y2="i * 10"
          stroke="#a8adaf"
          stroke-width="0.1"
        />
      </g>

      <!-- Vertical lines (21 lines) -->
      <g class="vertical-lines">
        <line
          v-for="i in 21"
          :key="'v' + i"
          :x1="i * 10"
          y1="0"
          :x2="i * 10"
          y2="125"
          stroke="#a8adaf"
          stroke-width="0.1"
        />
      </g>

      <!-- Y-axis labels (XP 0..1200) -->
      <g class="y-axis-labels">
        <text
          v-for="i in 13"
          :key="'y' + i"
          x="218"
          :y="(i - 1) * 10"
          class="axis-label"
          text-anchor="end"
          dominant-baseline="middle"
          fill="#666"
        >
          {{ 1200 - (i - 1) * 100 }}
        </text>
      </g>

      <!-- X-axis labels (days 1..21) -->
      <g class="x-axis-labels">
        <text
          v-for="i in 21"
          :key="'x' + i"
          :x="i * 10"
          y="128"
          class="axis-label"
          text-anchor="middle"
          fill="#666"
        >
          {{ i }}
        </text>
      </g>

      <!-- Candlesticks -->
      <g class="candlesticks">
        <g
          v-for="(candle, index) in candles"
          :key="index"
          :transform="`translate(${candle.x}, 0)`"
        >
          <!-- High-Low line -->
          <line
            :x1="0.5"
            :y1="candle.high"
            :x2="0.5"
            :y2="candle.low"
            :stroke="candle.color"
            stroke-width="0.2"
          />
          <!-- Body rectangle -->
          <rect
            :x="0"
            :y="Math.min(candle.open, candle.close)"
            :width="1"
            :height="Math.abs(candle.close - candle.open)"
            :fill="candle.color"
            stroke="none"
          />
        </g>
      </g>

      <!-- Wave overlay -->
      <path
        class="wave"
        :d="wavePath"
        fill="none"
        stroke="#666"
        stroke-width="0.5"
        stroke-dasharray="3,1"
      />

      <!-- Yellow zigzag line -->
      <path
        class="zigzag"
        :d="zigzagPath"
        fill="none"
        stroke="blue"
        stroke-width="0.5"
      />

      <!-- Circles along zigzag line -->
      <g class="zigzag-circles">
        <circle
          v-for="(point, index) in zigzagCircles"
          :key="index"
          :cx="point[0]"
          :cy="point[1]"
          r="1.5"
          :fill="getCircleFill(index)"
          :stroke="getCircleStroke(index)"
          stroke-width="0.5"
          :class="{ 'blinking-circle': isCurrentDay(index) }"
        />
      </g>
    </svg>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  height: {
    type: Number,
    default: 400
  },
  showControls: {
    type: Boolean,
    default: false
  },
  currentDay: {
    type: Number,
    default: 1
  },
  daysCompleted: {
    type: Number,
    default: 0
  }
})

// Generate wave path (sine wave)
const wavePath = computed(() => {
  const points = []
  const amplitude = 50
  const frequency = 0.023
  const centerY = 65
  
  for (let x = 0; x <= 210; x += 2) {
    const y = centerY + amplitude * Math.sin(frequency * x)
    points.push(`${x},${y}`)
  }
  
  return `M ${points.join(' L ')}`
})

const zigzagPath = computed(() => {
    const points = [
      "0,121",
      "10,117",
      "20,110",
      "30,105",
      "40,102",
      "50,96",
      "60,95",
      "70,92",
      "80,82",
      "90,78",
      "100,70",
      "110,71",
      "120,66",
      "130,62",
      "140,50",
      "150,50",
      "160,47",
      "170,41",
      "180,34",
      "190,26",
      "200,20",
      "210,10"
  ];
  
  return `M ${points.join(' L ')}`
})

// Circle positions along the zigzag line (21 points, skipping the first at x=0)
const zigzagCircles = computed(() => {
  const points = [
    [10, 117],
    [20, 110],
    [30, 105],
    [40, 102],
    [50, 96],
    [60, 95],
    [70, 92],
    [80, 82],
    [90, 78],
    [100, 70],
    [110, 71],
    [120, 66],
    [130, 62],
    [140, 50],
    [150, 50],
    [160, 47],
    [170, 41],
    [180, 34],
    [190, 26],
    [200, 20],
    [210, 10]
  ]
  return points
})

// Create candles 
let candleData = [];
let oldR = 0;
let color = '#39c86a';
let offset = 0;
for(let i = 0;i<102;i +=2){
  let r = Math.floor(Math.random() * 30);
  let r2 = Math.floor(Math.random() * 10);
  
  if(i>10 && i<35) offset = -20;
  else offset = r2;
  if(i>80) offset = 20;
  if(oldR<r) color = '#39c86a';
  else color = '#ff8a65';
  candleData.push(
    { x: 5+(i*2), open: (110-(i/2))-r-offset, high: (120-(i/2))-r-offset, low: (78-(i/2))-r2-offset, close: (82-(i/2))-r2-offset, color: color }
  );
  oldR = r;

}
const candles = ref(candleData);

// Helper methods for circle styling
const getCircleFill = (index) => {
  // index is 0-based, day is 1-based
  const dayNumber = index + 1;
  
  // Completed days should be filled with blue
  if (dayNumber < props.currentDay) {
    return '#3498db'; // Blue fill for completed days
  }
  
  // Current day should have white fill (will blink via animation)
  if (dayNumber === props.currentDay) {
    return '#ffffff'; // White fill for current day
  }
  
  // Future days remain white
  return '#ffffff';
}

const getCircleStroke = (index) => {
  // index is 0-based, day is 1-based
  const dayNumber = index + 1;
  
  // All circles have blue stroke
  return '#3498db';
}

const isCurrentDay = (index) => {
  // index is 0-based, day is 1-based
  const dayNumber = index + 1;
  return dayNumber === props.currentDay;
}
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
  background: transparent;
}

.learning-chart {
  display: block;
}

.wave {
  opacity: 0.7;
}

.zigzag {
  stroke: #3498db;
}

.zigzag-circles circle {
  stroke: #3498db;
  stroke-width: 0.5;
  filter: drop-shadow(0 0 1px rgba(52, 152, 219, 0.5));
}

.axis-label {
  font-size: 3px;
  fill: #666;
  font-family: Arial, sans-serif;
}

/* Blinking animation for current day circle */
@keyframes blink {
  0%, 100% {
    fill: #ffffff;
    stroke: #3498db;
    stroke-width: 0.5;
    r: 1.5;
  }
  50% {
    fill: #3498db;
    stroke: #3498db;
    stroke-width: 0.8;
    r: 2;
  }
}

.blinking-circle {
  animation: blink 1.5s ease-in-out infinite;
  filter: drop-shadow(0 0 2px rgba(52, 152, 219, 0.8));
}
</style>
