/**
 * Strategy Parameters Configuration
 * Extracted from backend/app/config/strategy-parameters.yaml
 */

export const strategyParameters = {
  // ==================== STRATEGY ====================
  category: {
    type: 'string',
    description: 'Strategy category that drives signal logic',
    typical_values: 'swing, long_term, day_trading, mean_reversion, famous_investors',
    values: ['swing', 'long_term', 'day_trading', 'mean_reversion', 'famous_investors'],
    group: 'configuration'
  },
  diversification_mode: {
    type: 'string',
    description: 'How to spread capital across positions',
    typical_values: 'diversified, sector_focused, concentrated, equal_weight',
    values: ['diversified', 'sector_focused', 'concentrated', 'equal_weight'],
    group: 'portfolio'
  },
  rebalance: {
    type: 'boolean',
    description: 'Enable automatic rebalancing of portfolio',
    typical_values: 'true/false',
    values: [true, false],
    group: 'portfolio'
  },
  use_ai_signals: {
    type: 'boolean',
    description: 'Enhance signals with AI sentiment/news',
    typical_values: 'true/false',
    values: [true, false],
    group: 'configuration'
  },
  run_frequency_minutes: {
    type: 'integer',
    description: 'How often the bot runs (in minutes) during market hours',
    typical_values: '5',
    group: 'configuration'
  },
  signal_min_confidence: {
    type: 'number',
    description: 'Minimum confidence (0–1) required to act on a signal',
    typical_values: '0.6',
    group: 'configuration'
  },
  conviction_score_minimum: {
    type: 'integer',
    description: 'Minimum conviction score for a trade (0–100)',
    typical_values: '75',
    group: 'configuration'
  },
  narrative_match_required: {
    type: 'boolean',
    description: 'Require growth narrative match (for famous investors)',
    typical_values: 'true/false',
    values: [true, false],
    group: 'configuration'
  },

  // ==================== FUNDAMENTAL ====================
  min_quality_score: {
    type: 'integer',
    description: 'Minimum fundamental quality score (0–100)',
    typical_values: '70',
    group: 'fundamental'
  },
  sell_on_fundamental_shift: {
    type: 'boolean',
    description: 'Sell if fundamentals deteriorate significantly',
    typical_values: 'true/false',
    values: [true, false],
    group: 'fundamental'
  },
  min_dividend_growth_rate: {
    type: 'percentage',
    description: 'Minimum annual dividend growth rate',
    typical_values: '5%',
    group: 'fundamental'
  },
  max_payout_ratio: {
    type: 'percentage',
    description: 'Maximum dividend payout ratio',
    typical_values: '70%',
    group: 'fundamental'
  },
  min_dividend_yield: {
    type: 'percentage',
    description: 'Minimum dividend yield',
    typical_values: '2%',
    group: 'fundamental'
  },
  auto_reinvest_dividends: {
    type: 'boolean',
    description: 'Automatically reinvest dividends',
    typical_values: 'true/false',
    values: [true, false],
    group: 'execution'
  },
  max_pe: {
    type: 'number',
    description: 'Maximum trailing P/E ratio',
    typical_values: '15-20',
    group: 'fundamental'
  },
  max_pb: {
    type: 'number',
    description: 'Maximum price/book ratio',
    typical_values: '1.5-2',
    group: 'fundamental'
  },
  discount_to_intrinsic_value: {
    type: 'percentage',
    description: 'Required discount to estimated intrinsic value',
    typical_values: '20%',
    group: 'fundamental'
  },
  min_revenue_growth: {
    type: 'percentage',
    description: 'Minimum year-over-year revenue growth',
    typical_values: '15%',
    group: 'fundamental'
  },
  min_eps_growth: {
    type: 'percentage',
    description: 'Minimum EPS growth',
    typical_values: '10-15%',
    group: 'fundamental'
  },
  max_pe_ratio: {
    type: 'number',
    description: 'Maximum P/E ratio for growth strategies',
    typical_values: '70',
    group: 'fundamental'
  },
  max_peg: {
    type: 'number',
    description: 'Maximum PEG ratio (P/E / growth)',
    typical_values: '1',
    group: 'fundamental'
  },
  minimum_roe_percent: {
    type: 'percentage',
    description: 'Minimum return on equity',
    typical_values: '10%',
    group: 'fundamental'
  },
  net_net_discount_percent: {
    type: 'percentage',
    description: 'Discount to net-net working capital (deep value)',
    typical_values: '20%',
    group: 'fundamental'
  },

  // ==================== PORTFOLIO / ALLOCATION ====================
  allocation_percent: {
    type: 'percentage',
    description: 'Portfolio allocation percentage for this strategy',
    typical_values: '100%',
    group: 'portfolio'
  },
  investment_amount: {
    type: 'number',
    description: 'Fixed dollar amount to invest per trade',
    typical_values: '100',
    group: 'execution'
  },
  target_stock_allocation: {
    type: 'percentage',
    description: 'Target allocation to stocks (multi-asset)',
    typical_values: '30-60%',
    group: 'portfolio'
  },
  target_bond_allocation: {
    type: 'percentage',
    description: 'Target allocation to bonds',
    typical_values: '40-55%',
    group: 'portfolio'
  },
  gold_allocation_percent: {
    type: 'percentage',
    description: 'Allocation to gold',
    typical_values: '7.5%',
    group: 'portfolio'
  },
  commodities_allocation_percent: {
    type: 'percentage',
    description: 'Allocation to commodities',
    typical_values: '7.5%',
    group: 'portfolio'
  },

  // ==================== RISK MANAGEMENT ====================
  max_position_pct: {
    type: 'percentage',
    description: 'Maximum percentage of portfolio in a single stock',
    typical_values: '5%',
    group: 'risk'
  },
  max_positions: {
    type: 'integer',
    description: 'Maximum number of open positions',
    typical_values: '20',
    group: 'risk'
  },
  cash_reserve_pct: {
    type: 'percentage',
    description: 'Minimum cash reserve percentage',
    typical_values: '10%',
    group: 'risk'
  },
  max_sector_pct: {
    type: 'percentage',
    description: 'Maximum percentage of portfolio in any single sector',
    typical_values: '20%',
    group: 'risk'
  },
  sector_cap_strictness: {
    type: 'string',
    description: 'How to handle sector cap breaches (hard = reject, soft = reduce)',
    typical_values: 'hard, soft',
    group: 'risk'
  },
  max_drawdown_pct: {
    type: 'percentage',
    description: 'Maximum drawdown before halting new BUYs',
    typical_values: '15%',
    group: 'risk'
  },
  stop_loss_pct: {
    type: 'percentage',
    description: 'Automatic stop loss percentage from entry',
    typical_values: '8%',
    group: 'risk'
  },
  take_profit_pct: {
    type: 'percentage',
    description: 'Automatic take profit percentage',
    typical_values: '20%',
    group: 'risk'
  },
  trailing_stop_pct: {
    type: 'percentage',
    description: 'Trailing stop percentage (0 = disabled)',
    typical_values: '0%',
    group: 'risk'
  },
  halt_on_drawdown: {
    type: 'boolean',
    description: 'Halt BUY orders when drawdown limit is exceeded',
    typical_values: 'true/false',
    values: [true, false],
    group: 'risk'
  },
  enable_stop_loss: {
    type: 'boolean',
    description: 'Master switch for stop loss logic',
    typical_values: 'true/false',
    values: [true, false],
    group: 'risk'
  },
  enable_take_profit: {
    type: 'boolean',
    description: 'Master switch for take profit logic',
    typical_values: 'true/false',
    values: [true, false],
    group: 'risk'
  },
  required_margin_of_safety_percent: {
    type: 'percentage',
    description: 'Required margin of safety for value investments',
    typical_values: '25%',
    group: 'risk'
  },

  // ==================== TECHNICAL ====================
  sma_short: {
    type: 'integer',
    description: 'Short simple moving average period',
    typical_values: '20',
    group: 'technical'
  },
  sma_long: {
    type: 'integer',
    description: 'Long simple moving average period',
    typical_values: '200',
    group: 'technical'
  },
  rsi_period: {
    type: 'integer',
    description: 'RSI calculation period',
    typical_values: '14',
    group: 'technical'
  },
  rsi_overbought: {
    type: 'integer',
    description: 'RSI overbought threshold',
    typical_values: '70',
    group: 'technical'
  },
  rsi_oversold: {
    type: 'integer',
    description: 'RSI oversold threshold',
    typical_values: '30',
    group: 'technical'
  },
  atr_period: {
    type: 'integer',
    description: 'Average True Range period',
    typical_values: '14',
    group: 'technical'
  },

  // ==================== SCREENING / STOCK PICKER ====================
  stock_universe: {
    type: 'string',
    description: 'Source of candidate stocks',
    typical_values: 'strategy_list, sector_filters, watchlist, screener',
    group: 'screening'
  },
  sector_include: {
    type: 'list',
    description: 'Sectors to include (from stock-bucketing taxonomy)',
    typical_values: 'Technology, Healthcare',
    group: 'screening'
  },
  sector_exclude: {
    type: 'list',
    description: 'Sectors to exclude',
    typical_values: 'Energy',
    group: 'screening'
  },
  sector_strength_threshold: {
    type: 'integer',
    description: 'Minimum sector strength score (0–100)',
    typical_values: '60',
    group: 'screening'
  },
  score_threshold: {
    type: 'integer',
    description: 'Minimum overall score (0–100) for a stock to be considered',
    typical_values: '50',
    group: 'screening'
  },
  risk_score_max: {
    type: 'integer',
    description: 'Maximum allowed risk score (0–100, lower is safer)',
    typical_values: '40',
    group: 'screening'
  },
  top_n_candidates: {
    type: 'integer',
    description: 'Number of top-ranked stocks to pass to strategy engine',
    typical_values: '10',
    group: 'screening'
  },
  enable_fundamental_filter: {
    type: 'boolean',
    description: 'Use fundamental metrics in screening (PE, yield, etc.)',
    typical_values: 'true/false',
    values: [true, false],
    group: 'screening'
  },
  min_volume: {
    type: 'integer',
    description: 'Minimum average daily volume (liquidity filter)',
    typical_values: '100000',
    group: 'screening'
  },
  liquidity_filter: {
    type: 'string',
    description: 'Liquidity requirement description',
    typical_values: 'e.g., avg volume > 1M',
    group: 'screening'
  },

  // ==================== EXECUTION / REBALANCING ====================
  min_order_value: {
    type: 'number',
    description: 'Minimum order value in dollars (ignore smaller)',
    typical_values: '100',
    group: 'execution'
  },
  round_shares: {
    type: 'boolean',
    description: 'Round to whole shares',
    typical_values: 'true/false',
    values: [true, false],
    group: 'execution'
  },
  rebalance_threshold: {
    type: 'percentage',
    description: 'Deviation from target weight that triggers rebalance',
    typical_values: '5%',
    group: 'portfolio'
  },
  order_type: {
    type: 'string',
    description: 'Default order type for bot executions',
    typical_values: 'MARKET, LIMIT, STOP',
    group: 'execution'
  },
  cost_ratio_max: {
    type: 'percentage',
    description: 'Maximum allowed cost ratio (expenses)',
    typical_values: '0.05%',
    group: 'execution'
  },

  // ==================== MACRO / QUALITY ====================
  macro_signal_strength_threshold: {
    type: 'integer',
    description: 'Minimum macro signal strength (0–100)',
    typical_values: '70',
    group: 'fundamental'
  },
  underlying_quality_required: {
    type: 'boolean',
    description: 'Require high underlying quality (moat, balance sheet)',
    typical_values: 'true/false',
    values: [true, false],
    group: 'fundamental'
  },
  preferred_industry_moat: {
    type: 'string',
    description: 'Preferred industry moat strength',
    typical_values: 'strong',
    group: 'fundamental'
  }
};

/**
 * Get all parameter names
 */
export function getAllParameterNames() {
  return Object.keys(strategyParameters);
}

/**
 * Get parameters grouped by their group field
 */
export function getParametersByGroup() {
  const groups = {};
  
  Object.entries(strategyParameters).forEach(([name, config]) => {
    const group = config.group;
    if (!groups[group]) {
      groups[group] = [];
    }
    groups[group].push({
      name,
      ...config
    });
  });
  
  return groups;
}

/**
 * Get all unique groups in the specified order
 */
export function getAllGroups() {
  const groups = new Set();
  Object.values(strategyParameters).forEach(param => {
    groups.add(param.group);
  });
  
  // Define the desired order
  const desiredOrder = ['screening', 'configuration', 'technical', 'fundamental', 'portfolio', 'risk', 'execution'];
  
  // Filter and sort groups according to desired order
  const orderedGroups = desiredOrder.filter(group => groups.has(group));
  
  // Add any remaining groups that aren't in the desired order
  const remainingGroups = Array.from(groups).filter(group => !desiredOrder.includes(group));
  
  return [...orderedGroups, ...remainingGroups];
}

/**
 * Create empty parameter object with all fields
 */
export function createEmptyParameters() {
  const params = {};
  Object.entries(strategyParameters).forEach(([key, config]) => {
    params[key] = getDefaultValueForType(config.type);
  });
  
  // Add entry conditions array for multiple conditions
  params.entryConditions = [
    {
      id: 1,
      indicator: 'RSI',
      period: 14,
      op: '>',
      value: '30',
      logic: 'AND'
    }
  ];
  
  // Keep existing strategy structure for exit, stopLoss, takeProfit
  params.strategy = [
    {
      type: 'exit',
      parameters: {
        indicator: 'RSI',
        operator: '<',
        value: ''
      }
    },
    {
      type: 'stopLoss',
      parameters: {
        lossType: 'percent',
        value: ''
      }
    },
    {
      type: 'takeProfit',
      parameters: {
        profitType: 'percent',
        value: ''
      }
    }
  ];
  
  params.signalMapping = {
    buyTrigger: '',
    sellTrigger: '',
    stopLoss: {
      lossType: 'percent',
      value: ''
    },
    takeProfit: {
      profitType: 'percent',
      value: ''
    }
  };
  
  return params;
}

/**
 * Convert parameters object to JSON string
 */
export function parametersToJson(parameters) {
  // Auto-generate signal mapping before converting to JSON
  const paramsWithGeneratedMapping = { ...parameters };
  
  // Generate buy trigger from entry conditions
  if (paramsWithGeneratedMapping.entryConditions && Array.isArray(paramsWithGeneratedMapping.entryConditions)) {
    paramsWithGeneratedMapping.signalMapping = paramsWithGeneratedMapping.signalMapping || {};
    
    // Create a readable summary of entry conditions
    const conditionStrings = paramsWithGeneratedMapping.entryConditions.map((cond, idx) => {
      const periodStr = cond.period ? `(${cond.period})` : '';
      const logicStr = idx < paramsWithGeneratedMapping.entryConditions.length - 1 ? ` ${cond.logic} ` : '';
      return `${cond.indicator}${periodStr} ${cond.op} ${cond.value}${logicStr}`;
    }).join('');
    
    paramsWithGeneratedMapping.signalMapping.buyTrigger = conditionStrings || '';
  }
  
  if (paramsWithGeneratedMapping.strategy && Array.isArray(paramsWithGeneratedMapping.strategy)) {
    const exitRule = paramsWithGeneratedMapping.strategy.find(s => s.type === 'exit');
    const stopLossRule = paramsWithGeneratedMapping.strategy.find(s => s.type === 'stopLoss');
    const takeProfitRule = paramsWithGeneratedMapping.strategy.find(s => s.type === 'takeProfit');
    
    if (exitRule && exitRule.parameters) {
      paramsWithGeneratedMapping.signalMapping = paramsWithGeneratedMapping.signalMapping || {};
      paramsWithGeneratedMapping.signalMapping.sellTrigger = 
        `${exitRule.parameters.indicator} ${exitRule.parameters.operator} ${exitRule.parameters.value}`;
    }
    
    if (stopLossRule && stopLossRule.parameters) {
      paramsWithGeneratedMapping.signalMapping = paramsWithGeneratedMapping.signalMapping || {};
      paramsWithGeneratedMapping.signalMapping.stopLoss = { ...stopLossRule.parameters };
    }
    
    if (takeProfitRule && takeProfitRule.parameters) {
      paramsWithGeneratedMapping.signalMapping = paramsWithGeneratedMapping.signalMapping || {};
      paramsWithGeneratedMapping.signalMapping.takeProfit = { ...takeProfitRule.parameters };
    }
  }
  
  return JSON.stringify(paramsWithGeneratedMapping, null, 2);
}

/**
 * Parse JSON string to parameters object
 */
export function jsonToParameters(jsonString) {
  try {
    if (!jsonString || jsonString.trim() === '') {
      return createEmptyParameters();
    }
    const parsed = JSON.parse(jsonString);
    
    // Ensure all expected parameters exist
    const result = createEmptyParameters();
    
    // Copy flat parameters
    Object.keys(result).forEach(key => {
      if (parsed[key] !== undefined && key !== 'strategy' && key !== 'signalMapping' && key !== 'entryConditions') {
        result[key] = parsed[key];
      }
    });
    
    // Copy entry conditions if they exist
    if (parsed.entryConditions && Array.isArray(parsed.entryConditions)) {
      result.entryConditions = parsed.entryConditions;
    }
    
    // Copy nested strategy structure if it exists
    if (parsed.strategy && Array.isArray(parsed.strategy)) {
      result.strategy = parsed.strategy;
    }
    
    // Copy signal mapping if it exists
    if (parsed.signalMapping && typeof parsed.signalMapping === 'object') {
      result.signalMapping = parsed.signalMapping;
    }
    
    return result;
  } catch (error) {
    console.error('Error parsing JSON parameters:', error);
    return createEmptyParameters();
  }
}

/**
 * Get default value based on parameter type
 */
export function getDefaultValueForType(type) {
  switch (type) {
    case 'string':
      return '';
    case 'boolean':
      return false;
    case 'number':
    case 'integer':
    case 'percentage':
      return '';
    case 'list':
      return [];
    default:
      return '';
  }
}
