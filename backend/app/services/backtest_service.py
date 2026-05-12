"""
Backtest Service - Strategy Backtesting Engine

Simulates trading a strategy over historical market data to evaluate performance.
Uses the same signal generation logic as the live trading bot but operates on
historical data from the market_data table.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from storage.repositories import RepositoryFactory
from storage.models import Strategy, Instrument, MarketData, BacktestResult
from jobs.trading_bot.strategy_signal import StrategySignal
from octopus.data_providers.yahoo_finance import YahooFinanceService

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Engine for running strategy backtests on historical data"""

    def __init__(self, db: Session, repo_factory: RepositoryFactory):
        self.db = db
        self.repo_factory = repo_factory
        self.strategy_signal = StrategySignal(db, repo_factory)

    def run_backtest(
        self,
        strategy_id: int,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        commission_pct: float = 0.0,
        slippage_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Run a full backtest for a strategy over a date range.

        Args:
            strategy_id: ID of the strategy to backtest
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting capital
            commission_pct: Commission as a fraction of trade value (e.g. 0.001 for 0.1%)
            slippage_pct: Slippage as a fraction of fill price (e.g. 0.001 for 0.1%)

        Returns:
            Dict with backtest results including performance metrics
        """
        # Convert string dates to datetime objects for SQLAlchemy DateTime columns
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # Create backtest result record
        backtest_record = self.repo_factory.backtest_results.create({
            'strategy_id': strategy_id,
            'start_date': start_dt,
            'end_date': end_dt,
            'initial_capital': initial_capital,
            'status': 'running',
        })

        try:
            # Get strategy
            strategy = self.repo_factory.strategies.get_by_id(strategy_id)
            if not strategy:
                raise ValueError(f"Strategy {strategy_id} not found")

            strategy_params = self.strategy_signal.parse_strategy_parameters(strategy)

            # Get stock list from strategy
            stock_symbols = self._get_strategy_stocks(strategy)
            if not stock_symbols:
                raise ValueError(f"No stocks configured for strategy '{strategy.name}'")

            logger.info(f"Running backtest for strategy '{strategy.name}' on {len(stock_symbols)} stocks "
                       f"from {start_date} to {end_date}")

            # Run the simulation
            result = self._simulate(
                strategy=strategy,
                strategy_params=strategy_params,
                stock_symbols=stock_symbols,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct,
            )

            # Update backtest record with results
            update_data = {
                'status': 'completed',
                'total_return': result['total_return'],
                'total_return_pct': result['total_return_pct'],
                'annualized_return': result['annualized_return'],
                'max_drawdown': result['max_drawdown'],
                'max_drawdown_pct': result['max_drawdown_pct'],
                'sharpe_ratio': result['sharpe_ratio'],
                'sortino_ratio': result['sortino_ratio'],
                'max_drawdown_duration_days': result['max_drawdown_duration_days'],
                'volatility': result['volatility'],
                'win_rate': result['win_rate'],
                'total_trades': result['total_trades'],
                'winning_trades': result['winning_trades'],
                'losing_trades': result['losing_trades'],
                'profit_factor': result['profit_factor'],
                'equity_curve': json.dumps(result['equity_curve']),
                'trade_log': json.dumps(result['trade_log']),
                'monthly_returns': json.dumps(result['monthly_returns']),
            }

            self.repo_factory.backtest_results.update(backtest_record.id, update_data)

            logger.info(f"Backtest completed: {result['total_trades']} trades, "
                       f"return={result['total_return_pct']:.2f}%, "
                       f"sharpe={result['sharpe_ratio']:.2f}")

            return result

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            self.repo_factory.backtest_results.update(backtest_record.id, {
                'status': 'failed',
                'error_message': str(e),
            })
            raise

    def _get_strategy_stocks(self, strategy: Strategy) -> List[str]:
        """Get the list of stock symbols for a strategy"""
        stock_list = strategy.stock_list
        if not stock_list:
            return []

        # Parse comma-separated or newline-separated list
        symbols = []
        for line in stock_list.split('\n'):
            for sym in line.split(','):
                sym = sym.strip().upper()
                if sym and sym not in symbols:
                    symbols.append(sym)
        return symbols

    # ------------------------------------------------------------------
    # Indicator helpers (pure-math, no I/O)
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_rsi(closes: List[float], period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [c if c > 0 else 0.0 for c in changes]
        losses = [-c if c < 0 else 0.0 for c in changes]
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _calc_ema(closes: List[float], period: int) -> Optional[float]:
        if len(closes) < period:
            return None
        k = 2.0 / (period + 1)
        ema = sum(closes[:period]) / period
        for price in closes[period:]:
            ema = price * k + ema * (1.0 - k)
        return ema

    @staticmethod
    def _calc_sma(closes: List[float], period: int) -> Optional[float]:
        if len(closes) < period:
            return None
        return sum(closes[-period:]) / period

    @staticmethod
    def _calc_atr(bars: List[Tuple], period: int = 14) -> Optional[float]:
        """bars: list of (high, low, close) tuples in chronological order"""
        if len(bars) < period + 1:
            return None
        trs = []
        for i in range(1, len(bars)):
            h, l, prev_c = bars[i][0], bars[i][1], bars[i - 1][2]
            trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
        return sum(trs[-period:]) / period

    # ------------------------------------------------------------------
    # Pre-load price history for the full backtest period + lookback
    # ------------------------------------------------------------------

    def _preload_price_histories(
        self, symbols: List[str], start_dt: datetime, end_dt: datetime
    ) -> Dict[str, List[Dict]]:
        """
        Returns {symbol: [{date, close, high, low, open}, ...]} sorted oldest-first.
        Includes a 300-day lookback before start_dt so indicators are warm.
        If no data is found in the database, fetches historical data from Yahoo Finance
        and saves it to the database for future use.
        """
        lookback_start = start_dt - timedelta(days=300)
        histories: Dict[str, List[Dict]] = {}
        yahoo_service = YahooFinanceService(self.db)

        for symbol in symbols:
            instrument = self.repo_factory.instruments.get_by_symbol(symbol)
            if not instrument:
                histories[symbol] = []
                continue

            rows = self.repo_factory.market_data.get_by_timestamp_range(
                instrument.id, '1day',
                lookback_start.strftime('%Y-%m-%d'),
                end_dt.strftime('%Y-%m-%d'),
            )
            if rows:
                histories[symbol] = [
                    {
                        'date': md.timestamp.date(),
                        'close': float(md.close),
                        'high': float(md.high),
                        'low': float(md.low),
                        'open': float(md.open),
                    }
                    for md in rows if md.close
                ]
            else:
                # No data in DB — fetch from Yahoo Finance
                logger.info(f"No 1day data in DB for {symbol}, fetching from Yahoo Finance...")
                try:
                    # Calculate how many months of data we need (lookback + backtest period)
                    total_days = (end_dt - lookback_start).days
                    # Map days to yfinance periods: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max
                    if total_days <= 30:
                        period = "1mo"
                    elif total_days <= 90:
                        period = "3mo"
                    elif total_days <= 180:
                        period = "6mo"
                    elif total_days <= 365:
                        period = "1y"
                    elif total_days <= 730:
                        period = "2y"
                    elif total_days <= 1825:
                        period = "5y"
                    else:
                        period = "10y"

                    historical_data = yahoo_service.fetch_historical_data(symbol, period)
                    if historical_data:
                        # Save to database for future use
                        yahoo_service.save_historical_data(symbol, period)

                        # Build history dict from fetched data
                        bars = []
                        for dp in historical_data:
                            dt = datetime.strptime(dp['date'], '%Y-%m-%d')
                            if lookback_start <= dt <= end_dt:
                                bars.append({
                                    'date': dt.date(),
                                    'close': float(dp['close_price']),
                                    'high': float(dp['high_price']),
                                    'low': float(dp['low_price']),
                                    'open': float(dp['open_price']),
                                })
                        histories[symbol] = bars
                        logger.info(f"Fetched {len(bars)} daily bars for {symbol} from Yahoo Finance")
                    else:
                        logger.warning(f"No historical data available for {symbol} from Yahoo Finance")
                        histories[symbol] = []
                except Exception as e:
                    logger.error(f"Error fetching historical data for {symbol}: {e}")
                    histories[symbol] = []

        return histories

    def _extract_indicator_requirements(
        self, strategy_params: Dict[str, Any]
    ) -> List[Tuple[str, int]]:
        """Return list of (INDICATOR, period) pairs needed by entry/exit conditions."""
        defaults = {'RSI': 14, 'EMA': 20, 'SMA': 20, 'ATR': 14, 'MACD': 12,
                    'BB_UPPER': 20, 'BB_LOWER': 20, 'STOCH': 14}
        reqs: set = set()

        conditions = list(strategy_params.get('entryConditions', []))
        for rule in strategy_params.get('strategy', []):
            params = rule.get('parameters', {})
            ind = params.get('indicator', '').upper()
            if ind:
                conditions.append({'indicator': ind, 'period': params.get('period')})

        for cond in conditions:
            ind = cond.get('indicator', '').upper()
            if not ind:
                continue
            period = cond.get('period')
            try:
                period = int(period) if period else defaults.get(ind)
            except (ValueError, TypeError):
                period = defaults.get(ind)
            if period:
                reqs.add((ind, period))

        return list(reqs)

    # ------------------------------------------------------------------
    # Pre-compute all indicators once per ticker (FIX #1: O(n²) -> O(n))
    # ------------------------------------------------------------------

    def _precompute_all_indicators(
        self,
        price_histories: Dict[str, List[Dict]],
        requirements: List[Tuple[str, int]],
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Pre-compute all required indicators for every symbol on every date.
        
        Returns: {symbol: {date_str: {indicator_key: value, ...}, ...}, ...}
        
        This eliminates the O(n²) recomputation in the original _compute_indicators_for_day
        which re-sliced and recomputed the full history on every single day × ticker.
        """
        result: Dict[str, Dict[str, Dict[str, float]]] = {}

        for symbol, bars in price_histories.items():
            if not bars:
                result[symbol] = {}
                continue

            closes = [b['close'] for b in bars]
            ohlc_tuples = [(b['high'], b['low'], b['close']) for b in bars]
            dates = [b['date'] for b in bars]

            symbol_indicators: Dict[str, Dict[str, float]] = {}

            for ind, period in requirements:
                if ind == 'RSI':
                    self._precompute_rsi(symbol_indicators, closes, dates, period)
                elif ind == 'EMA':
                    self._precompute_ema(symbol_indicators, closes, dates, period)
                elif ind == 'SMA':
                    self._precompute_sma(symbol_indicators, closes, dates, period)
                elif ind == 'ATR':
                    self._precompute_atr(symbol_indicators, ohlc_tuples, dates, period)
                elif ind in ('BB_UPPER', 'BB_LOWER'):
                    self._precompute_bollinger(symbol_indicators, closes, dates, period, ind)

            result[symbol] = symbol_indicators

        return result

    @staticmethod
    def _precompute_rsi(
        indicator_map: Dict[str, Dict[str, float]],
        closes: List[float],
        dates: List[Any],
        period: int,
    ) -> None:
        """Pre-compute RSI for every date and store in indicator_map."""
        key = f"rsi_{period}"
        key_short = "rsi"

        if len(closes) < period + 1:
            return

        # Compute all changes first
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        # Wilder's smoothed RSI: first average is simple, then smoothed
        gains = [c if c > 0 else 0.0 for c in changes]
        losses = [-c if c < 0 else 0.0 for c in changes]

        # First values (simple average)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Store RSI for the first valid date (index = period, since we need period+1 closes)
        for idx in range(period, len(closes)):
            if idx > period:
                # Smoothed update
                avg_gain = (avg_gain * (period - 1) + gains[idx - 1]) / period
                avg_loss = (avg_loss * (period - 1) + losses[idx - 1]) / period

            date_str = str(dates[idx])
            if avg_loss == 0:
                rsi_val = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_val = 100.0 - (100.0 / (1.0 + rs))

            if date_str not in indicator_map:
                indicator_map[date_str] = {}
            indicator_map[date_str][key] = rsi_val
            indicator_map[date_str].setdefault(key_short, rsi_val)

    @staticmethod
    def _precompute_ema(
        indicator_map: Dict[str, Dict[str, float]],
        closes: List[float],
        dates: List[Any],
        period: int,
    ) -> None:
        """Pre-compute EMA for every date and store in indicator_map."""
        key = f"ema_{period}"
        key_short = "ema"

        if len(closes) < period:
            return

        k = 2.0 / (period + 1)
        ema = sum(closes[:period]) / period

        # Store EMA starting from index = period - 1 (first date with enough data)
        date_str = str(dates[period - 1])
        if date_str not in indicator_map:
            indicator_map[date_str] = {}
        indicator_map[date_str][key] = ema
        indicator_map[date_str].setdefault(key_short, ema)

        # Continue for remaining dates
        for idx in range(period, len(closes)):
            ema = closes[idx] * k + ema * (1.0 - k)
            date_str = str(dates[idx])
            if date_str not in indicator_map:
                indicator_map[date_str] = {}
            indicator_map[date_str][key] = ema
            indicator_map[date_str].setdefault(key_short, ema)

    @staticmethod
    def _precompute_sma(
        indicator_map: Dict[str, Dict[str, float]],
        closes: List[float],
        dates: List[Any],
        period: int,
    ) -> None:
        """Pre-compute SMA for every date and store in indicator_map."""
        key = f"sma_{period}"
        key_short = "sma"

        if len(closes) < period:
            return

        running_sum = sum(closes[:period])

        for idx in range(period - 1, len(closes)):
            if idx > period - 1:
                running_sum = running_sum - closes[idx - period] + closes[idx]
            sma_val = running_sum / period
            date_str = str(dates[idx])
            if date_str not in indicator_map:
                indicator_map[date_str] = {}
            indicator_map[date_str][key] = sma_val
            indicator_map[date_str].setdefault(key_short, sma_val)

    @staticmethod
    def _precompute_atr(
        indicator_map: Dict[str, Dict[str, float]],
        ohlc_tuples: List[Tuple],
        dates: List[Any],
        period: int,
    ) -> None:
        """Pre-compute ATR for every date and store in indicator_map."""
        key = f"atr_{period}"
        key_short = "atr"

        if len(ohlc_tuples) < period + 1:
            return

        # Compute all true ranges
        trs = []
        for i in range(1, len(ohlc_tuples)):
            h, l, prev_c = ohlc_tuples[i][0], ohlc_tuples[i][1], ohlc_tuples[i - 1][2]
            trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))

        # First ATR is simple average
        atr_val = sum(trs[:period]) / period

        # Store first valid ATR (index = period, since we need period+1 bars)
        date_str = str(dates[period])
        if date_str not in indicator_map:
            indicator_map[date_str] = {}
        indicator_map[date_str][key] = atr_val
        indicator_map[date_str].setdefault(key_short, atr_val)

        # Continue with smoothed ATR
        for idx in range(period + 1, len(ohlc_tuples)):
            atr_val = (atr_val * (period - 1) + trs[idx - 1]) / period
            date_str = str(dates[idx])
            if date_str not in indicator_map:
                indicator_map[date_str] = {}
            indicator_map[date_str][key] = atr_val
            indicator_map[date_str].setdefault(key_short, atr_val)

    @staticmethod
    def _precompute_bollinger(
        indicator_map: Dict[str, Dict[str, float]],
        closes: List[float],
        dates: List[Any],
        period: int,
        band_type: str,
    ) -> None:
        """Pre-compute Bollinger Bands for every date and store in indicator_map."""
        upper_key = f"bb_upper_{period}"
        lower_key = f"bb_lower_{period}"

        if len(closes) < period:
            return

        running_sum = sum(closes[:period])

        for idx in range(period - 1, len(closes)):
            if idx > period - 1:
                running_sum = running_sum - closes[idx - period] + closes[idx]
            sma_val = running_sum / period
            variance = sum((closes[j] - sma_val) ** 2 for j in range(idx - period + 1, idx + 1)) / period
            std = math.sqrt(variance)

            date_str = str(dates[idx])
            if date_str not in indicator_map:
                indicator_map[date_str] = {}

            if band_type == 'BB_UPPER':
                val = sma_val + 2 * std
                indicator_map[date_str][upper_key] = val
                indicator_map[date_str].setdefault('bb_upper', val)
            else:
                val = sma_val - 2 * std
                indicator_map[date_str][lower_key] = val
                indicator_map[date_str].setdefault('bb_lower', val)

    def _lookup_indicators_for_day(
        self,
        symbol: str,
        day: datetime,
        precomputed_indicators: Dict[str, Dict[str, Dict[str, float]]],
    ) -> Dict[str, float]:
        """O(1) lookup of pre-computed indicators for a symbol on a given day."""
        day_date = day.date() if isinstance(day, datetime) else day
        day_str = str(day_date)

        symbol_indicators = precomputed_indicators.get(symbol, {})
        return symbol_indicators.get(day_str, {})

    # ------------------------------------------------------------------
    # Core simulation
    # ------------------------------------------------------------------

    def _simulate(
        self,
        strategy: Strategy,
        strategy_params: Dict[str, Any],
        stock_symbols: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float,
        commission_pct: float = 0.0,
        slippage_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Core simulation engine.

        Walks through each trading day, evaluates entry/exit conditions,
        executes trades, and tracks portfolio value.

        Fixes applied:
        1. O(n²) indicator computation → pre-compute all indicators once per ticker
        2. Lookahead bias → signal on day N close, execute at day N+1 open
        3. Commission & slippage → deduct on every fill
        4. Integer share quantities → use fractional quantities
        """
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # Pre-load OHLC history (with lookback) and indicator requirements
        price_histories = self._preload_price_histories(stock_symbols, start_dt, end_dt)
        indicator_requirements = self._extract_indicator_requirements(strategy_params)

        logger.info(f"Indicator requirements: {indicator_requirements}")
        for sym, hist in price_histories.items():
            logger.info(f"  {sym}: {len(hist)} daily bars loaded (incl. lookback)")

        # FIX #1: Pre-compute all indicators once per ticker before the simulation loop
        logger.info("Pre-computing indicators for all symbols...")
        precomputed_indicators = self._precompute_all_indicators(
            price_histories, indicator_requirements
        )
        logger.info("Indicator pre-computation complete.")

        # State
        cash = float(initial_capital)
        positions = {}  # symbol -> {'quantity': float, 'avg_price': float}
        equity_curve = []  # List of {'date': str, 'equity': float, 'cash': float, 'holdings_value': float}
        trade_log = []  # List of trade records
        monthly_returns = {}  # month_key -> list of daily returns

        # Get all trading days from market data for these symbols
        trading_days = self._get_trading_days(stock_symbols, start_dt, end_dt)

        if not trading_days:
            logger.warning("No trading days found in date range")
            return self._empty_result(initial_capital)

        # Get max positions limit
        max_positions = int(strategy_params.get('max_positions', 10))
        max_position_pct = float(strategy_params.get('max_position_pct', 20.0)) / 100.0

        previous_equity = float(initial_capital)
        peak_equity = float(initial_capital)
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        max_drawdown_duration_days = 0  # FIX #7: track longest drawdown duration
        current_drawdown_start_day = None  # day_idx when current drawdown began

        # Track daily returns for volatility/sharpe/sortino calculation
        daily_returns = []
        risk_free_rate = 0.0  # Default 0% risk-free rate; can be parameterized


        # FIX #2: Build a mapping of signals generated on day N to be executed on day N+1
        # pending_signals: {symbol: {'action': 'BUY'|'SELL', 'price': float, 'reasons': ..., ...}}
        pending_signals: Dict[str, Dict[str, Any]] = {}

        for day_idx, day in enumerate(trading_days):
            day_str = day.strftime('%Y-%m-%d')
            day_equity = cash
            holdings_value = 0.0

            # ---------------------------------------------------------------
            # STEP 1: Execute any pending signals from the previous day
            # (FIX #2: signal on day N close, execute at day N+1 open)
            # ---------------------------------------------------------------
            if pending_signals:
                for symbol in list(pending_signals.keys()):
                    signal = pending_signals.pop(symbol)
                    action = signal['action']

                    # Get the open price for today (day N+1) for execution
                    market_data_today = self._get_market_data_for_day(symbol, day)
                    if not market_data_today:
                        continue

                    # Use open price for execution (FIX #2: avoid lookahead bias)
                    execution_price = float(market_data_today.open)

                    # Apply slippage (FIX #3)
                    if slippage_pct > 0:
                        if action == 'BUY':
                            execution_price *= (1.0 + slippage_pct)
                        else:
                            execution_price *= (1.0 - slippage_pct)

                    if action == 'BUY':
                        # Calculate position size
                        position_value = cash * max_position_pct
                        # FIX #4: Use fractional quantities instead of int()
                        quantity = position_value / execution_price

                        if quantity > 0 and cash >= quantity * execution_price:
                            cost = quantity * execution_price
                            # FIX #3: Deduct commission
                            commission = cost * commission_pct
                            total_cost = cost + commission

                            if cash >= total_cost:
                                cash -= total_cost

                                positions[symbol] = {
                                    'quantity': quantity,
                                    'avg_price': execution_price,
                                    'entry_date': day_str,
                                }

                                trade_log.append({
                                    'date': day_str,
                                    'symbol': symbol,
                                    'action': 'BUY',
                                    'price': round(execution_price, 2),
                                    'quantity': round(quantity, 4),
                                    'value': round(cost, 2),
                                    'commission': round(commission, 2),
                                    'slippage': round(cost * slippage_pct, 2) if slippage_pct > 0 else 0,
                                    'reasons': signal.get('reasons', []),
                                })

                                logger.debug(
                                    f"  BUY {symbol} @ ${execution_price:.2f} x {quantity:.4f} "
                                    f"(comm: ${commission:.2f}) on {day_str}"
                                )

                    elif action == 'SELL':
                        pos = positions.get(symbol)
                        if pos:
                            proceeds = pos['quantity'] * execution_price
                            # FIX #3: Deduct commission on sell
                            commission = proceeds * commission_pct
                            net_proceeds = proceeds - commission

                            pnl = net_proceeds - (pos['quantity'] * pos['avg_price'])
                            pnl_pct = ((execution_price - pos['avg_price']) / pos['avg_price']) * 100

                            cash += net_proceeds
                            del positions[symbol]

                            trade_log.append({
                                'date': day_str,
                                'symbol': symbol,
                                'action': 'SELL',
                                'price': round(execution_price, 2),
                                'quantity': round(pos['quantity'], 4),
                                'value': round(proceeds, 2),
                                'commission': round(commission, 2),
                                'slippage': round(proceeds * slippage_pct, 2) if slippage_pct > 0 else 0,
                                'pnl': round(pnl, 2),
                                'pnl_pct': round(pnl_pct, 2),
                                'reason': signal.get('reason', ''),
                                'entry_date': pos['entry_date'],
                                'holding_days': (day - datetime.strptime(pos['entry_date'], '%Y-%m-%d')).days,
                            })

                            logger.debug(
                                f"  SELL {symbol} @ ${execution_price:.2f} "
                                f"(pnl: ${pnl:.2f}, comm: ${commission:.2f}) on {day_str}"
                            )

            # ---------------------------------------------------------------
            # STEP 2: Evaluate signals for today (to be executed tomorrow)
            # ---------------------------------------------------------------
            for symbol in stock_symbols:
                # Get market data for this symbol on this day
                market_data = self._get_market_data_for_day(symbol, day)
                if not market_data:
                    continue

                # Use close price for signal evaluation (FIX #2: signal on close)
                signal_price = float(market_data.close)
                has_position = symbol in positions

                # Update position current value (mark-to-market using close)
                if has_position:
                    pos = positions[symbol]
                    pos_value = pos['quantity'] * signal_price
                    holdings_value += pos_value

                # --- ENTRY SIGNAL EVALUATION (on close) ---
                if not has_position and len(positions) < max_positions:
                    # O(1) lookup from pre-computed indicators (FIX #1)
                    computed_indicators = self._lookup_indicators_for_day(
                        symbol, day, precomputed_indicators
                    )
                    should_enter, entry_reasons = self._check_entry_conditions(
                        strategy, strategy_params, symbol, market_data, day,
                        computed_indicators
                    )

                    if should_enter:
                        # Store signal for execution at next day's open
                        pending_signals[symbol] = {
                            'action': 'BUY',
                            'price': signal_price,
                            'reasons': entry_reasons,
                        }

                # --- EXIT SIGNAL EVALUATION (on close) ---
                elif has_position:
                    # O(1) lookup from pre-computed indicators (FIX #1)
                    computed_indicators = self._lookup_indicators_for_day(
                        symbol, day, precomputed_indicators
                    )
                    should_exit, exit_reason = self._check_exit_conditions(
                        strategy_params, symbol, market_data, positions[symbol], day,
                        computed_indicators
                    )

                    if should_exit:
                        # Store signal for execution at next day's open
                        pending_signals[symbol] = {
                            'action': 'SELL',
                            'price': signal_price,
                            'reason': exit_reason,
                        }

            # Calculate end-of-day equity
            day_equity = cash + holdings_value
            equity_curve.append({
                'date': day_str,
                'equity': round(day_equity, 2),
                'cash': round(cash, 2),
                'holdings_value': round(holdings_value, 2),
            })

            # Track drawdown (FIX #7: also track duration)
            if day_equity > peak_equity:
                peak_equity = day_equity
                # Recovered from drawdown — reset the timer
                if current_drawdown_start_day is not None:
                    duration = day_idx - current_drawdown_start_day
                    if duration > max_drawdown_duration_days:
                        max_drawdown_duration_days = duration
                    current_drawdown_start_day = None
            else:
                # Still in drawdown or new drawdown
                if current_drawdown_start_day is None:
                    current_drawdown_start_day = day_idx

            drawdown = peak_equity - day_equity
            drawdown_pct = (drawdown / peak_equity) * 100 if peak_equity > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct


            # Track daily return
            if day_idx > 0 and previous_equity > 0:
                daily_return = (day_equity - previous_equity) / previous_equity
                daily_returns.append(daily_return)

                # Monthly aggregation
                month_key = day_str[:7]  # YYYY-MM
                if month_key not in monthly_returns:
                    monthly_returns[month_key] = []
                monthly_returns[month_key].append(daily_return)

            previous_equity = day_equity

        # --- CALCULATE PERFORMANCE METRICS ---
        total_return = day_equity - initial_capital
        total_return_pct = (total_return / initial_capital) * 100

        # Annualized return
        num_days = len(trading_days)
        years = num_days / 252.0  # Approximate trading days per year
        if years > 0 and initial_capital > 0:
            annualized_return = ((day_equity / initial_capital) ** (1.0 / years) - 1) * 100
        else:
            annualized_return = 0.0

        # Volatility (annualized) — FIX #5: use sample std of daily returns
        if len(daily_returns) > 1:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            daily_volatility = math.sqrt(variance)
            volatility = daily_volatility * math.sqrt(252) * 100  # Annualized %
        else:
            volatility = 0.0

        # FIX #5: Correct Sharpe ratio — mean of daily excess returns / std of daily excess returns, annualized
        if len(daily_returns) > 1:
            risk_free_daily = (1.0 + risk_free_rate) ** (1.0 / 252.0) - 1.0
            excess_returns = [r - risk_free_daily for r in daily_returns]
            mean_excess = sum(excess_returns) / len(excess_returns)
            excess_variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
            excess_std = math.sqrt(excess_variance)
            if excess_std > 0:
                sharpe_ratio = (mean_excess / excess_std) * math.sqrt(252)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # FIX #6: Sortino ratio — same as Sharpe but uses only negative excess returns (downside deviation)
        if len(daily_returns) > 1:
            risk_free_daily = (1.0 + risk_free_rate) ** (1.0 / 252.0) - 1.0
            excess_returns = [r - risk_free_daily for r in daily_returns]
            mean_excess = sum(excess_returns) / len(excess_returns)
            # Downside deviation: only negative excess returns
            negative_excess = [r for r in excess_returns if r < 0]
            if negative_excess:
                downside_variance = sum(r ** 2 for r in negative_excess) / len(excess_returns)
                downside_std = math.sqrt(downside_variance)
                if downside_std > 0:
                    sortino_ratio = (mean_excess / downside_std) * math.sqrt(252)
                else:
                    sortino_ratio = 0.0
            else:
                # No negative returns — Sortino is effectively infinite
                sortino_ratio = 999.0
        else:
            sortino_ratio = 0.0

        # Win rate
        winning_trades = sum(1 for t in trade_log if t.get('action') == 'SELL' and t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in trade_log if t.get('action') == 'SELL' and t.get('pnl', 0) <= 0)
        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # FIX #8: Profit factor — use infinity sentinel when no losing trades
        gross_profit = sum(t['pnl'] for t in trade_log if t.get('action') == 'SELL' and t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t['pnl'] for t in trade_log if t.get('action') == 'SELL' and t.get('pnl', 0) < 0))
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = 999.0  # Capped sentinel for infinity (no losing trades)
        else:
            profit_factor = 0.0

        # Aggregate monthly returns
        aggregated_monthly = {}
        for month, returns in monthly_returns.items():
            if returns:
                aggregated_monthly[month] = round(sum(returns) * 100, 2)  # As percentage

        # FIX #7: Finalize drawdown duration — if still in drawdown at end, count it
        if current_drawdown_start_day is not None:
            final_duration = len(trading_days) - 1 - current_drawdown_start_day
            if final_duration > max_drawdown_duration_days:
                max_drawdown_duration_days = final_duration

        return {
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return_pct, 2),
            'annualized_return': round(annualized_return, 2),
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'max_drawdown_duration_days': max_drawdown_duration_days,
            'sharpe_ratio': round(sharpe_ratio, 4),
            'sortino_ratio': round(sortino_ratio, 4),
            'volatility': round(volatility, 4),
            'win_rate': round(win_rate, 2),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'profit_factor': round(profit_factor, 4),
            'equity_curve': equity_curve,
            'trade_log': trade_log,
            'monthly_returns': aggregated_monthly,
            'final_equity': round(day_equity, 2),
        }


    def _get_trading_days(self, symbols: List[str], start: datetime, end: datetime) -> List[datetime]:
        """Get all unique trading days across the given symbols.
        
        Tries '1day' interval first, falls back to aggregating '1min' data.
        """
        trading_days = set()

        for symbol in symbols:
            instrument = self.repo_factory.instruments.get_by_symbol(symbol)
            if not instrument:
                continue

            # Try 1day interval first
            data = self.repo_factory.market_data.get_by_timestamp_range(
                instrument.id, '1day', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
            )
            if data:
                for md in data:
                    trading_days.add(md.timestamp.date())
            else:
                # Fall back to 1min data - extract unique dates
                min_data = self.repo_factory.market_data.get_by_timestamp_range(
                    instrument.id, '1min', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
                )
                for md in min_data:
                    trading_days.add(md.timestamp.date())

        return sorted([datetime.combine(d, datetime.min.time()) for d in trading_days])

    def _get_market_data_for_day(self, symbol: str, day: datetime) -> Optional[MarketData]:
        """Get market data for a symbol on a specific day.
        
        Tries '1day' interval first, falls back to aggregating '1min' data.
        Returns a MarketData-like object with aggregated OHLCV values.
        """
        instrument = self.repo_factory.instruments.get_by_symbol(symbol)
        if not instrument:
            return None

        # Try 1day interval first
        data = self.repo_factory.market_data.get_by_timestamp_range(
            instrument.id, '1day',
            day.strftime('%Y-%m-%d'),
            (day + timedelta(days=1)).strftime('%Y-%m-%d')
        )
        if data:
            return data[0]

        # Fall back to aggregating 1min data into a daily bar
        min_data = self.repo_factory.market_data.get_by_timestamp_range(
            instrument.id, '1min',
            day.strftime('%Y-%m-%d'),
            (day + timedelta(days=1)).strftime('%Y-%m-%d')
        )
        if not min_data:
            return None

        # Aggregate 1min data into a daily OHLCV bar
        opens = [float(md.open) for md in min_data if md.open]
        highs = [float(md.high) for md in min_data if md.high]
        lows = [float(md.low) for md in min_data if md.low]
        closes = [float(md.close) for md in min_data if md.close]
        volumes = [int(md.volume) for md in min_data if md.volume]

        if not closes:
            return None

        # Create a mock MarketData object with aggregated values
        # We use a simple dict-like wrapper since we only access .close, .open, .high, .low, .volume
        class AggregatedMarketData:
            def __init__(self, close, open_, high, low, volume, timestamp, symbol_id):
                self.close = close
                self.open = open_
                self.high = high
                self.low = low
                self.volume = volume
                self.timestamp = timestamp
                self.symbol_id = symbol_id

        return AggregatedMarketData(
            close=closes[-1],
            open_=opens[0] if opens else closes[0],
            high=max(highs) if highs else closes[-1],
            low=min(lows) if lows else closes[-1],
            volume=sum(volumes) if volumes else 0,
            timestamp=day,
            symbol_id=instrument.id,
        )

    def _check_entry_conditions(
        self,
        strategy: Strategy,
        strategy_params: Dict[str, Any],
        symbol: str,
        market_data: MarketData,
        day: datetime,
        computed_indicators: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, List[str]]:
        """Check if entry conditions are met for a symbol"""
        md_dict = self._build_market_data_dict(symbol, market_data, computed_indicators)

        # Check condition-based entry (from Entry tab)
        entry_conditions = strategy_params.get('entryConditions', [])
        if entry_conditions:
            return self.strategy_signal.evaluate_entry_conditions(entry_conditions, md_dict)

        # Fallback: use the signal generation engine
        # Build a simple market_data dict for the signal generator
        simple_market_data = {
            'close': float(market_data.close),
            'volume': int(market_data.volume) if market_data.volume else 0,
        }
        indicators = {
            'rsi': md_dict.get('rsi', 50),
            'price_trend': md_dict.get('price_trend', 'NEUTRAL'),
        }

        # Get instrument
        instrument = self.repo_factory.instruments.get_by_symbol(symbol)
        if not instrument:
            return False, ["Instrument not found"]

        # Use a mock account for signal generation
        signal = self.strategy_signal.generate_trading_signal(
            account=None,
            strategy=strategy,
            instrument=instrument,
            market_data=simple_market_data,
            indicators=indicators,
            strategy_params=strategy_params,
        )

        if signal and signal.get('action') == 'BUY':
            return True, [signal.get('reason', 'Signal-based entry')]

        return False, []

    def _check_exit_conditions(
        self,
        strategy_params: Dict[str, Any],
        symbol: str,
        market_data: MarketData,
        position: Dict[str, Any],
        day: datetime,
        computed_indicators: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, str]:
        """Check if exit conditions are met for a position"""
        current_price = float(market_data.close)
        entry_price = position['avg_price']
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        # Check stop loss
        stop_loss = float(strategy_params.get('stop_loss_percent', 5.0))
        if pnl_pct <= -stop_loss:
            return True, f"Stop loss triggered ({pnl_pct:.2f}% <= -{stop_loss:.2f}%)"

        # Check take profit
        take_profit = float(strategy_params.get('take_profit_percent', 15.0))
        if pnl_pct >= take_profit:
            return True, f"Take profit triggered ({pnl_pct:.2f}% >= {take_profit:.2f}%)"

        # Check exit conditions from Exit tab
        md_dict = self._build_market_data_dict(symbol, market_data, computed_indicators)
        position_data = {
            'symbol': symbol,
            'entry_price': entry_price,
            'current_price': current_price,
            'pnl_pct': pnl_pct,
        }

        should_exit, reason = self.strategy_signal.evaluate_exit_conditions(
            strategy_params, position_data, md_dict
        )
        if should_exit:
            return True, reason

        return False, ""

    def _build_market_data_dict(
        self,
        symbol: str,
        market_data: MarketData,
        computed_indicators: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Build a market data dict from a MarketData record, enriched with indicators"""
        md_dict = {
            'symbol': symbol,
            'close': float(market_data.close) if market_data.close else 0,
            'open': float(market_data.open) if market_data.open else 0,
            'high': float(market_data.high) if market_data.high else 0,
            'low': float(market_data.low) if market_data.low else 0,
            'volume': int(market_data.volume) if market_data.volume else 0,
            'timestamp': market_data.timestamp,
        }

        if computed_indicators:
            md_dict.update(computed_indicators)

        return md_dict

    def _empty_result(self, initial_capital: float) -> Dict[str, Any]:
        """Return an empty result when no trading days are found"""
        return {
            'total_return': 0.0,
            'total_return_pct': 0.0,
            'annualized_return': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'max_drawdown_duration_days': 0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'volatility': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'profit_factor': 0.0,
            'equity_curve': [{'date': '', 'equity': initial_capital, 'cash': initial_capital, 'holdings_value': 0}],
            'trade_log': [],
            'monthly_returns': {},
            'final_equity': initial_capital,
        }



class BacktestService:
    """Service layer for backtesting operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo_factory = RepositoryFactory(db)
        self.engine = BacktestEngine(db, self.repo_factory)

    def run_backtest(
        self,
        strategy_id: int,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        commission_pct: float = 0.0,
        slippage_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """Run a backtest and return results"""
        return self.engine.run_backtest(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
        )

    def get_backtest_results(self, strategy_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get backtest results for a strategy"""
        results = self.repo_factory.backtest_results.get_by_strategy(strategy_id, limit)
        return [self._serialize_result(r) for r in results]

    def get_backtest_by_id(self, backtest_id: int) -> Optional[Dict[str, Any]]:
        """Get a single backtest result by ID"""
        result = self.repo_factory.backtest_results.get_by_id(backtest_id)
        return self._serialize_result(result) if result else None

    def delete_backtest(self, backtest_id: int) -> bool:
        """Delete a backtest result"""
        return self.repo_factory.backtest_results.delete(backtest_id)

    def _serialize_result(self, result: BacktestResult) -> Dict[str, Any]:
        """Serialize a BacktestResult model to dict"""
        return {
            'id': result.id,
            'strategy_id': result.strategy_id,
            'start_date': result.start_date.isoformat() if result.start_date else None,
            'end_date': result.end_date.isoformat() if result.end_date else None,
            'initial_capital': float(result.initial_capital) if result.initial_capital else 0,
            'total_return': float(result.total_return) if result.total_return else 0,
            'total_return_pct': float(result.total_return_pct) if result.total_return_pct else 0,
            'annualized_return': float(result.annualized_return) if result.annualized_return else 0,
            'max_drawdown': float(result.max_drawdown) if result.max_drawdown else 0,
            'max_drawdown_pct': float(result.max_drawdown_pct) if result.max_drawdown_pct else 0,
            'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else 0,
            'volatility': float(result.volatility) if result.volatility else 0,
            'win_rate': float(result.win_rate) if result.win_rate else 0,
            'total_trades': result.total_trades or 0,
            'winning_trades': result.winning_trades or 0,
            'losing_trades': result.losing_trades or 0,
            'profit_factor': float(result.profit_factor) if result.profit_factor else 0,
            'equity_curve': json.loads(result.equity_curve) if result.equity_curve else [],
            'trade_log': json.loads(result.trade_log) if result.trade_log else [],
            'monthly_returns': json.loads(result.monthly_returns) if result.monthly_returns else {},
            'status': result.status or 'unknown',
            'error_message': result.error_message,
            'created_at': result.created_at.isoformat() if result.created_at else None,
        }
