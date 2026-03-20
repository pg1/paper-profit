import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from storage.repositories import RepositoryFactory
from storage.models import Strategy, Setting

logger = logging.getLogger(__name__)


class InstrumentDiscovery:
    """Module for discovering and managing instruments"""
    
    def __init__(self, db: Session, repo_factory: RepositoryFactory):
        self.db = db
        self.repo_factory = repo_factory
    
    def get_stock_list(self, strategy: Strategy) -> List[str]:
        """ Get stock list from strategy """
               
        # Parse existing stock list (could be comma-separated, newline-separated, or JSON array)
        stock_list = []
        
        # Try JSON first
        try:
            stocks_json = json.loads(strategy.stock_list)
            if isinstance(stocks_json, list):
                stock_list = [str(s).strip().upper() for s in stocks_json if s]
        except json.JSONDecodeError:
            # Try comma-separated
            if ',' in strategy.stock_list:
                stock_list = [s.strip().upper() for s in strategy.stock_list.split(',') if s.strip()]
            else:
                # Try newline-separated
                stock_list = [s.strip().upper() for s in strategy.stock_list.split('\n') if s.strip()]
        
        return stock_list
    
    
    def _save_generated_stock_list(self, strategy: Strategy, stock_list: List[str]):
        """Save generated stock list back to the database"""
        try:
            # Convert list to comma-separated string
            stock_list_str = ','.join(stock_list)
            
            # Update the strategy with the new stock list
            update_data = {
                'stock_list': stock_list_str
            }
            
            # Only update if the list has changed
            if strategy.stock_list != stock_list_str:
                self.repo_factory.strategies.update(strategy.id, update_data)
                logger.info(f"Updated stock list for strategy '{strategy.name}' with {len(stock_list)} stocks")
            else:
                logger.info(f"Stock list unchanged for strategy '{strategy.name}'")
                
        except Exception as e:
            logger.error(f"Error saving generated stock list: {str(e)}")
    
    def _get_fallback_stock_list(self, ai_prompt: str) -> List[str]:
        """Get fallback stock list based on prompt keywords (mock implementation)"""
        # This is the original mock implementation
        ai_prompt_lower = ai_prompt.lower()
        
        if 'tech' in ai_prompt_lower or 'technology' in ai_prompt_lower:
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META']
        elif 'finance' in ai_prompt_lower or 'bank' in ai_prompt_lower:
            return ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS']
        elif 'health' in ai_prompt_lower or 'pharma' in ai_prompt_lower:
            return ['JNJ', 'PFE', 'MRK', 'ABT', 'UNH', 'LLY']
        elif 'energy' in ai_prompt_lower or 'oil' in ai_prompt_lower:
            return ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC']
        elif 'consumer' in ai_prompt_lower or 'retail' in ai_prompt_lower:
            return ['WMT', 'TGT', 'COST', 'HD', 'LOW', 'AMZN']
        elif 'industrial' in ai_prompt_lower:
            return ['CAT', 'BA', 'HON', 'GE', 'MMM', 'UTX']
        else:
            # Default to some popular stocks
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'JNJ']
    
    def get_stocks_by_universe(self, strategy: Strategy, limit: int = 20) -> List[str]:
        """
        Get stocks based on the stock_universe parameter in strategy.
        
        Args:
            strategy: The Strategy object containing parameters
            limit: Maximum number of stocks to return (default 20)
            
        Returns:
            List of stock symbols
            
        Supported stock_universe values:
            - strategy_list: Use the strategy's stock_list field
            - sector_filters: Filter instruments by sector (sector_include/sector_exclude)
            - watchlist: Get all stocks from the watchlist
            - screener: Generic screener combining multiple filters
            - winners: Top day gainers from Yahoo Finance screener
            - losers: Top day losers from Yahoo Finance screener
        """
        # Get stock_universe from strategy parameters
        parameters = strategy.parameters or {}
        stock_universe = parameters.get('stock_universe', 'strategy_list')
        
        logger.info(f"Getting stocks for universe: {stock_universe}")
        
        # Dispatch to appropriate method based on universe type
        if stock_universe == 'strategy_list':
            return self.get_stock_list(strategy)
        
        elif stock_universe == 'watchlist':
            return self._get_watchlist_stocks()
        
        elif stock_universe == 'winners':
            return self._get_screener_stocks('day_gainers', limit)
        
        elif stock_universe == 'losers':
            return self._get_screener_stocks('day_losers', limit)
        
        elif stock_universe == 'sector_filters':
            return self._get_sector_filtered_stocks(strategy, limit)
        
        elif stock_universe == 'screener':
            return self._get_screener_filtered_stocks(strategy, limit)
        
        else:
            # Fallback to strategy list
            return self.get_stock_list(strategy)
    
    def _get_watchlist_stocks(self) -> List[str]:
        """Get all stocks from the watchlist"""
        try:
            watchlist_instruments = self.repo_factory.instruments.get_watchlist()
            stocks = [inst.symbol.upper() for inst in watchlist_instruments if inst.symbol]
            logger.info(f"Retrieved {len(stocks)} stocks from watchlist")
            return stocks
        except Exception as e:
            logger.error(f"Error getting watchlist stocks: {str(e)}")
            return []
    
    def _get_screener_stocks(self, screener_type: str, limit: int = 20) -> List[str]:
        """
        Get stocks from Yahoo Finance screener.
        
        Args:
            screener_type: Type of screener ('day_gainers', 'day_losers', etc.)
            limit: Maximum number of stocks to return
            
        Returns:
            List of stock symbols
        """
        try:
            from yfinance import screener
            
            result = screener.screen(screener_type, count=limit)
            
            if result and 'quotes' in result:
                stocks = [quote.get('symbol', '').upper() for quote in result['quotes'] if quote.get('symbol')]
                logger.info(f"Retrieved {len(stocks)} stocks from {screener_type} screener")
                return stocks[:limit]
            else:
                logger.warning(f"No data returned from {screener_type} screener")
                return []
                
        except ImportError:
            logger.error("yfinance package not installed or screener module not available")
            return []
        except Exception as e:
            logger.error(f"Error getting {screener_type} stocks: {str(e)}")
            return []
    
    def _get_sector_filtered_stocks(self, strategy: Strategy, limit: int = 20) -> List[str]:
        """
        Get stocks filtered by sector based on strategy parameters.
        
        Uses sector_include and sector_exclude from strategy parameters.
        """
        try:
            parameters = strategy.parameters or {}
            sector_include = parameters.get('sector_include', [])
            sector_exclude = parameters.get('sector_exclude', [])
            
            # Ensure they are lists
            if isinstance(sector_include, str):
                sector_include = [s.strip() for s in sector_include.split(',') if s.strip()]
            if isinstance(sector_exclude, str):
                sector_exclude = [s.strip() for s in sector_exclude.split(',') if s.strip()]
            
            # Get all active instruments
            all_instruments = self.repo_factory.instruments.get_all(active_only=True)
            
            filtered_stocks = []
            for instrument in all_instruments:
                sector = instrument.sector or 'Unknown'
                
                # Apply inclusion filter (if specified)
                if sector_include and sector not in sector_include:
                    continue
                
                # Apply exclusion filter
                if sector in sector_exclude:
                    continue
                
                filtered_stocks.append(instrument.symbol.upper())
            
            logger.info(f"Retrieved {len(filtered_stocks)} stocks after sector filtering (include: {sector_include}, exclude: {sector_exclude})")
            return filtered_stocks[:limit]
            
        except Exception as e:
            logger.error(f"Error getting sector filtered stocks: {str(e)}")
            return []
    
    def _get_screener_filtered_stocks(self, strategy: Strategy, limit: int = 20) -> List[str]:
        """
        Get stocks using a combination of screener filters from strategy parameters.
        
        Combines multiple filters: score_threshold, risk_score_max, sector filters, min_volume, etc.
        """
        try:
            parameters = strategy.parameters or {}
            
            # Get filter parameters
            score_threshold = parameters.get('score_threshold', 0)
            risk_score_max = parameters.get('risk_score_max', 100)
            sector_include = parameters.get('sector_include', [])
            sector_exclude = parameters.get('sector_exclude', [])
            
            # Ensure sector filters are lists
            if isinstance(sector_include, str):
                sector_include = [s.strip() for s in sector_include.split(',') if s.strip()]
            if isinstance(sector_exclude, str):
                sector_exclude = [s.strip() for s in sector_exclude.split(',') if s.strip()]
            
            # Get all active instruments
            all_instruments = self.repo_factory.instruments.get_all(active_only=True)
            
            filtered_stocks = []
            for instrument in all_instruments:
                # Apply score threshold filter
                if instrument.overall_score is not None and instrument.overall_score < score_threshold:
                    continue
                
                # Apply risk score filter (lower risk score = safer)
                if instrument.risk_score is not None and instrument.risk_score > risk_score_max:
                    continue
                
                # Apply sector filters
                sector = instrument.sector or 'Unknown'
                if sector_include and sector not in sector_include:
                    continue
                if sector in sector_exclude:
                    continue
                
                filtered_stocks.append(instrument.symbol.upper())
            
            # Sort by overall_score (highest first) if available
            instruments_with_scores = [
                (inst.symbol.upper(), inst.overall_score or 0) 
                for inst in all_instruments 
                if inst.symbol.upper() in filtered_stocks
            ]
            instruments_with_scores.sort(key=lambda x: x[1], reverse=True)
            
            sorted_stocks = [symbol for symbol, score in instruments_with_scores]
            
            logger.info(f"Retrieved {len(sorted_stocks)} stocks after screener filtering")
            return sorted_stocks[:limit]
            
        except Exception as e:
            logger.error(f"Error getting screener filtered stocks: {str(e)}")
            return []
