#!/usr/bin/env python3

"""
Parameter Functions Module

This module provides functions for calculating strategy parameters using data
from various third-party services via the octopus data providers.

Each function takes a stock symbol as input and returns the calculated parameter value.
"""

import logging
from typing import Optional, Union, Dict, Any
from sqlalchemy.orm import Session
from octopus.data_providers.alpha_vantage import AlphaVantageService
from octopus.data_providers.financialmodelingprep import FinancialModelingPrepService
from octopus.data_providers.yahoo_finance import YahooFinanceService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FundamentalFunctions:
    """Class containing functions for calculating strategy parameters"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.alpha_vantage = AlphaVantageService(db_session)
        self.fmp = FinancialModelingPrepService(db_session)
        self.yahoo = YahooFinanceService(db_session)
    
    def _get_best_data_provider(self, symbol: str, data_type: str = "fundamental") -> Dict[str, Any]:
        """
        Try multiple data providers to get the best available data for a symbol
        
        Args:
            symbol: Stock symbol
            data_type: Type of data needed ("fundamental", "price", "technical")
            
        Returns:
            Dictionary with the best available data
        """
        data = None
        
        # Try Financial Modeling Prep first for fundamental data
        if data_type == "fundamental":
            try:
                data = self.fmp.fetch_stock_info(symbol)
                if data and data.get('pe_ratio') is not None:
                    logger.info(f"Using Financial Modeling Prep data for {symbol}")
                    return data
            except Exception as e:
                logger.debug(f"Financial Modeling Prep failed for {symbol}: {e}")
        
        # Try Alpha Vantage
        try:
            data = self.alpha_vantage.fetch_stock_info(symbol)
            if data and data.get('pe_ratio') is not None:
                logger.info(f"Using Alpha Vantage data for {symbol}")
                return data
        except Exception as e:
            logger.debug(f"Alpha Vantage failed for {symbol}: {e}")
        
        # Try Yahoo Finance as fallback
        try:
            data = self.yahoo.fetch_stock_info(symbol)
            if data:
                logger.info(f"Using Yahoo Finance data for {symbol}")
                return data
        except Exception as e:
            logger.debug(f"Yahoo Finance failed for {symbol}: {e}")
        
        logger.warning(f"No data available for {symbol} from any provider")
        return {}
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from the best available provider"""
        try:
            # Try Yahoo Finance first for price data
            price_data = self.yahoo.fetch_current_price(symbol)
            if price_data and price_data.get('price'):
                return price_data['price']
            
            # Try Alpha Vantage
            price_data = self.alpha_vantage.fetch_current_price(symbol)
            if price_data and price_data.get('price'):
                return price_data['price']
            
            # Try Financial Modeling Prep
            price_data = self.fmp.fetch_current_price(symbol)
            if price_data and price_data.get('price'):
                return price_data['price']
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
        
        return None
    
    def _get_key_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get key financial metrics from Financial Modeling Prep"""
        try:
            return self.fmp.get_key_metrics(symbol)
        except Exception as e:
            logger.debug(f"Could not get key metrics for {symbol}: {e}")
            return None
    
    def _get_financial_statements(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get financial statements from Financial Modeling Prep"""
        try:
            return self.fmp.get_financial_statements(symbol)
        except Exception as e:
            logger.debug(f"Could not get financial statements for {symbol}: {e}")
            return None
    
    def _get_company_rating(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company rating from Financial Modeling Prep"""
        try:
            return self.fmp.get_company_rating(symbol)
        except Exception as e:
            logger.debug(f"Could not get company rating for {symbol}: {e}")
            return None
    
    # Fundamental Parameters
    
    def get_quality_score(self, symbol: str) -> Optional[int]:
        """
        Calculate fundamental quality score based on multiple factors
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quality score (0-100) or None if data unavailable
        """
        try:
            data = self._get_best_data_provider(symbol, "fundamental")
            if not data:
                return None
            
            score = 0
            
            # P/E ratio scoring (lower is better)
            pe_ratio = data.get('pe_ratio')
            if pe_ratio and pe_ratio > 0:
                if pe_ratio < 15:
                    score += 25
                elif pe_ratio < 25:
                    score += 15
                elif pe_ratio < 40:
                    score += 5
            
            # Market cap scoring (larger is generally more stable)
            market_cap = data.get('market_cap')
            if market_cap:
                if market_cap > 10_000_000_000:  # > $10B
                    score += 25
                elif market_cap > 2_000_000_000:  # > $2B
                    score += 15
                elif market_cap > 300_000_000:    # > $300M
                    score += 10
            
            # Beta scoring (lower volatility is better)
            beta = data.get('beta')
            if beta:
                if beta < 0.8:
                    score += 20
                elif beta < 1.2:
                    score += 15
                elif beta < 1.5:
                    score += 10
            
            # Dividend yield scoring (if applicable)
            dividend_yield = data.get('dividend_yield')
            if dividend_yield and dividend_yield > 0:
                score += 10
            
            # Sector/industry scoring (basic)
            sector = data.get('sector')
            if sector and sector != 'N/A':
                score += 10
            
            return min(score, 100)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Error calculating quality score for {symbol}: {e}")
            return None
    
    def get_pe_ratio(self, symbol: str) -> Optional[float]:
        """
        Get P/E ratio for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            P/E ratio or None if data unavailable
        """
        try:
            data = self._get_best_data_provider(symbol, "fundamental")
            return data.get('pe_ratio')
        except Exception as e:
            logger.error(f"Error getting P/E ratio for {symbol}: {e}")
            return None
    
    def get_pb_ratio(self, symbol: str) -> Optional[float]:
        """
        Get P/B ratio for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            P/B ratio or None if data unavailable
        """
        try:
            metrics = self._get_key_metrics(symbol)
            if metrics:
                return metrics.get('pb_ratio')
            
            # Fallback: Try to calculate from available data
            data = self._get_best_data_provider(symbol, "fundamental")
            current_price = self._get_current_price(symbol)
            market_cap = data.get('market_cap')
            
            if current_price and market_cap and market_cap > 0:
                # Very rough approximation: P/B ≈ Market Cap / (Market Cap / P/E)
                pe_ratio = data.get('pe_ratio')
                if pe_ratio and pe_ratio > 0:
                    return current_price / (market_cap / pe_ratio)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting P/B ratio for {symbol}: {e}")
            return None
    
    def get_dividend_yield(self, symbol: str) -> Optional[float]:
        """
        Get dividend yield for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dividend yield (as decimal) or None if data unavailable
        """
        try:
            data = self._get_best_data_provider(symbol, "fundamental")
            dividend_yield = data.get('dividend_yield')
            if dividend_yield:
                return dividend_yield / 100.0 if dividend_yield > 1 else dividend_yield
            return None
        except Exception as e:
            logger.error(f"Error getting dividend yield for {symbol}: {e}")
            return None
    
    def get_beta(self, symbol: str) -> Optional[float]:
        """
        Get beta coefficient for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Beta coefficient or None if data unavailable
        """
        try:
            data = self._get_best_data_provider(symbol, "fundamental")
            return data.get('beta')
        except Exception as e:
            logger.error(f"Error getting beta for {symbol}: {e}")
            return None
    
    def get_market_cap(self, symbol: str) -> Optional[float]:
        """
        Get market capitalization for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Market cap in dollars or None if data unavailable
        """
        try:
            data = self._get_best_data_provider(symbol, "fundamental")
            return data.get('market_cap')
        except Exception as e:
            logger.error(f"Error getting market cap for {symbol}: {e}")
            return None
    
    def get_sector(self, symbol: str) -> Optional[str]:
        """
        Get sector for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Sector name or None if data unavailable
        """
        try:
            data = self._get_best_data_provider(symbol, "fundamental")
            return data.get('sector')
        except Exception as e:
            logger.error(f"Error getting sector for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None if data unavailable
        """
        return self._get_current_price(symbol)
    
    def get_peg_ratio(self, symbol: str) -> Optional[float]:
        """
        Get PEG ratio for a stock (P/E divided by earnings growth rate)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            PEG ratio or None if data unavailable
        """
        try:
            # This would require earnings growth rate data
            # For now, return a placeholder or use key metrics if available
            metrics = self._get_key_metrics(symbol)
            if metrics:
                return metrics.get('peg_ratio')
            
            # Simple approximation if we have P/E and can estimate growth
            pe_ratio = self.get_pe_ratio(symbol)
            if pe_ratio and pe_ratio > 0:
                # Very rough estimate - in practice this would need actual growth data
                return pe_ratio / 15.0  # Assuming 15% growth as placeholder
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting PEG ratio for {symbol}: {e}")
            return None
    
    def get_roe(self, symbol: str) -> Optional[float]:
        """
        Get Return on Equity for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            ROE (as decimal) or None if data unavailable
        """
        try:
            metrics = self._get_key_metrics(symbol)
            if metrics:
                # ROE might be available in key metrics
                # If not, we'd need to calculate from financial statements
                return metrics.get('roe')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting ROE for {symbol}: {e}")
            return None
    
    def get_revenue_growth(self, symbol: str) -> Optional[float]:
        """
        Get revenue growth rate for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Revenue growth rate (as decimal) or None if data unavailable
        """
        try:
            financials = self._get_financial_statements(symbol)
            if financials and financials.get('income_statement'):
                income_statement = financials['income_statement']
                if len(income_statement) >= 2:
                    # Calculate growth between most recent and previous year
                    current_revenue = income_statement[0].get('revenue')
                    previous_revenue = income_statement[1].get('revenue')
                    
                    if current_revenue and previous_revenue and previous_revenue > 0:
                        growth_rate = (current_revenue - previous_revenue) / previous_revenue
                        return growth_rate
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting revenue growth for {symbol}: {e}")
            return None
    
    def get_eps_growth(self, symbol: str) -> Optional[float]:
        """
        Get EPS growth rate for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            EPS growth rate (as decimal) or None if data unavailable
        """
        try:
            financials = self._get_financial_statements(symbol)
            if financials and financials.get('income_statement'):
                income_statement = financials['income_statement']
                if len(income_statement) >= 2:
                    # Calculate growth between most recent and previous year
                    current_eps = income_statement[0].get('eps')
                    previous_eps = income_statement[1].get('eps')
                    
                    if current_eps and previous_eps and previous_eps > 0:
                        growth_rate = (current_eps - previous_eps) / previous_eps
                        return growth_rate
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting EPS growth for {symbol}: {e}")
            return None
    
    def get_conviction_score(self, symbol: str) -> Optional[int]:
        """
        Calculate conviction score based on multiple factors
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Conviction score (0-100) or None if data unavailable
        """
        try:
            score = 0
            
            # Quality score component
            quality_score = self.get_quality_score(symbol)
            if quality_score:
                score += quality_score * 0.4  # 40% weight
            
            # Growth component
            revenue_growth = self.get_revenue_growth(symbol)
            if revenue_growth:
                if revenue_growth > 0.2:  # > 20%
                    score += 20
                elif revenue_growth > 0.1:  # > 10%
                    score += 15
                elif revenue_growth > 0.05:  # > 5%
                    score += 10
            
            # Valuation component
            pe_ratio = self.get_pe_ratio(symbol)
            if pe_ratio and pe_ratio > 0:
                if pe_ratio < 15:
                    score += 20
                elif pe_ratio < 25:
                    score += 15
                elif pe_ratio < 35:
                    score += 10
            
            # Profitability component
            roe = self.get_roe(symbol)
            if roe:
                if roe > 0.2:  # > 20%
                    score += 20
                elif roe > 0.15:  # > 15%
                    score += 15
                elif roe > 0.1:  # > 10%
                    score += 10
            
            return min(score, 100)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Error calculating conviction score for {symbol}: {e}")
            return None
    
    def get_industry_moat_strength(self, symbol: str) -> Optional[str]:
        """
        Assess industry moat strength based on sector and company characteristics
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Moat strength ("strong", "moderate", "weak") or None if data unavailable
        """
        try:
            data = self._get_best_data_provider(symbol, "fundamental")
            sector = data.get('sector')
            market_cap = data.get('market_cap')
            
            if not sector or sector == 'N/A':
                return "weak"
            
            # Strong moat sectors
            strong_moat_sectors = [
                'Technology', 'Healthcare', 'Consumer Defensive', 
                'Utilities', 'Communication Services'
            ]
            
            # Moderate moat sectors
            moderate_moat_sectors = [
                'Industrials', 'Consumer Cyclical', 'Financial Services'
            ]
            
            # Weak moat sectors
            weak_moat_sectors = [
                'Energy', 'Basic Materials', 'Real Estate'
            ]
            
            if sector in strong_moat_sectors:
                base_strength = "strong"
            elif sector in moderate_moat_sectors:
                base_strength = "moderate"
            else:
                base_strength = "weak"
            
            # Adjust based on market cap (larger companies often have stronger moats)
            if market_cap and market_cap > 50_000_000_000:  # > $50B
                if base_strength == "moderate":
                    return "strong"
                elif base_strength == "weak":
                    return "moderate"
            
            return base_strength
            
        except Exception as e:
            logger.error(f"Error assessing industry moat for {symbol}: {e}")
            return None
    
    # Boolean parameter helpers
    
    def has_fundamental_shift(self, symbol: str, threshold: float = 0.1) -> Optional[bool]:
        """
        Check if fundamentals have deteriorated
        
        Args:
            symbol: Stock symbol
            threshold: Percentage change threshold to consider as deterioration
            
        Returns:
            True if fundamentals have deteriorated, False otherwise, or None if data unavailable
        """
        try:
            # Check revenue growth
            revenue_growth = self.get_revenue_growth(symbol)
            if revenue_growth and revenue_growth < -threshold:
                return True
            
            # Check EPS growth
            eps_growth = self.get_eps_growth(symbol)
            if eps_growth and eps_growth < -threshold:
                return True
            
            # Check quality score (if it drops significantly)
            quality_score = self.get_quality_score(symbol)
            if quality_score and quality_score < 50:  # Arbitrary threshold
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking fundamental shift for {symbol}: {e}")
            return None
    
    def meets_quality_requirement(self, symbol: str, min_quality: int = 70) -> Optional[bool]:
        """
        Check if stock meets minimum quality requirement
        
        Args:
            symbol: Stock symbol
            min_quality: Minimum quality score required
            
        Returns:
            True if quality requirement is met, False otherwise, or None if data unavailable
        """
        try:
            quality_score = self.get_quality_score(symbol)
            if quality_score is not None:
                return quality_score >= min_quality
            return None
        except Exception as e:
            logger.error(f"Error checking quality requirement for {symbol}: {e}")
            return None
    
    def meets_roe_requirement(self, symbol: str, min_roe: float = 0.1) -> Optional[bool]:
        """
        Check if stock meets minimum ROE requirement
        
        Args:
            symbol: Stock symbol
            min_roe: Minimum ROE required (as decimal)
            
        Returns:
            True if ROE requirement is met, False otherwise, or None if data unavailable
        """
        try:
            roe = self.get_roe(symbol)
            if roe is not None:
                return roe >= min_roe
            return None
        except Exception as e:
            logger.error(f"Error checking ROE requirement for {symbol}: {e}")
            return None
    
    def meets_growth_requirement(self, symbol: str, min_growth: float = 0.1) -> Optional[bool]:
        """
        Check if stock meets minimum growth requirement
        
        Args:
            symbol: Stock symbol
            min_growth: Minimum growth rate required (as decimal)
            
        Returns:
            True if growth requirement is met, False otherwise, or None if data unavailable
        """
        try:
            revenue_growth = self.get_revenue_growth(symbol)
            eps_growth = self.get_eps_growth(symbol)
            
            # Use the better of revenue or EPS growth
            if revenue_growth is not None and eps_growth is not None:
                best_growth = max(revenue_growth, eps_growth)
                return best_growth >= min_growth
            elif revenue_growth is not None:
                return revenue_growth >= min_growth
            elif eps_growth is not None:
                return eps_growth >= min_growth
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error checking growth requirement for {symbol}: {e}")
            return None
    
    def meets_valuation_requirement(self, symbol: str, max_pe: float = 20.0, max_pb: float = 2.0) -> Optional[bool]:
        """
        Check if stock meets valuation requirements
        
        Args:
            symbol: Stock symbol
            max_pe: Maximum P/E ratio allowed
            max_pb: Maximum P/B ratio allowed
            
        Returns:
            True if valuation requirements are met, False otherwise, or None if data unavailable
        """
        try:
            pe_ratio = self.get_pe_ratio(symbol)
            pb_ratio = self.get_pb_ratio(symbol)
            
            pe_ok = pe_ratio is None or pe_ratio <= max_pe
            pb_ok = pb_ratio is None or pb_ratio <= max_pb
            
            # If we have at least one ratio, return based on that
            if pe_ratio is not None or pb_ratio is not None:
                return pe_ok and pb_ok
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error checking valuation requirement for {symbol}: {e}")
            return None
    
    def get_all_parameters(self, symbol: str) -> Dict[str, Any]:
        """
        Get all available parameter values for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary containing all calculated parameter values
        """
        parameters = {
            'symbol': symbol,
            'quality_score': self.get_quality_score(symbol),
            'pe_ratio': self.get_pe_ratio(symbol),
            'pb_ratio': self.get_pb_ratio(symbol),
            'dividend_yield': self.get_dividend_yield(symbol),
            'beta': self.get_beta(symbol),
            'market_cap': self.get_market_cap(symbol),
            'sector': self.get_sector(symbol),
            'current_price': self.get_current_price(symbol),
            'peg_ratio': self.get_peg_ratio(symbol),
            'roe': self.get_roe(symbol),
            'revenue_growth': self.get_revenue_growth(symbol),
            'eps_growth': self.get_eps_growth(symbol),
            'conviction_score': self.get_conviction_score(symbol),
            'industry_moat_strength': self.get_industry_moat_strength(symbol),
            'has_fundamental_shift': self.has_fundamental_shift(symbol),
            'meets_quality_requirement': self.meets_quality_requirement(symbol),
            'meets_roe_requirement': self.meets_roe_requirement(symbol),
            'meets_growth_requirement': self.meets_growth_requirement(symbol),
            'meets_valuation_requirement': self.meets_valuation_requirement(symbol)
        }
        
        return parameters


# Convenience functions for direct usage
def create_parameter_functions(db_session: Session) -> FundamentalFunctions:
    """
    Create a FundamentalFunctions instance
    
    Args:
        db_session: Database session
        
    Returns:
        FundamentalFunctions instance
    """
    return FundamentalFunctions(db_session)


def get_parameter_value(db_session: Session, symbol: str, parameter_name: str) -> Any:
    """
    Get a specific parameter value for a stock
    
    Args:
        db_session: Database session
        symbol: Stock symbol
        parameter_name: Name of the parameter to get
        
    Returns:
        Parameter value or None if unavailable
    """
    pf = FundamentalFunctions(db_session)
    
    # Map parameter names to method calls
    parameter_methods = {
        'min_quality_score': pf.get_quality_score,
        'max_pe': pf.get_pe_ratio,
        'max_pb': pf.get_pb_ratio,
        'min_dividend_yield': pf.get_dividend_yield,
        'min_revenue_growth': pf.get_revenue_growth,
        'min_eps_growth': pf.get_eps_growth,
        'max_peg': pf.get_peg_ratio,
        'minimum_roe_percent': pf.get_roe,
        'conviction_score_minimum': pf.get_conviction_score,
        'preferred_industry_moat': pf.get_industry_moat_strength,
        'sell_on_fundamental_shift': pf.has_fundamental_shift,
        'underlying_quality_required': pf.meets_quality_requirement,
        'narrative_match_required': pf.meets_growth_requirement
    }
    
    method = parameter_methods.get(parameter_name)
    if method:
        return method(symbol)
    else:
        logger.warning(f"Unknown parameter: {parameter_name}")
        return None


def get_all_parameters_for_stock(db_session: Session, symbol: str) -> Dict[str, Any]:
    """
    Get all parameter values for a stock
    
    Args:
        db_session: Database session
        symbol: Stock symbol
        
    Returns:
        Dictionary containing all parameter values
    """
    pf = FundamentalFunctions(db_session)
    return pf.get_all_parameters(symbol)
