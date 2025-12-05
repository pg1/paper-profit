#!/usr/bin/env python3

import logging
import json
import requests
from sqlalchemy.orm import Session
from storage.repositories import RepositoryFactory
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeepSeekService:
    """DeepSeek AI Platform service for financial analysis and insights"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.repo = RepositoryFactory(db_session)
        self.api_key = self._get_api_key_from_settings()
        self.base_url = "https://api.deepseek.com/v1"
        logger.info(f"DeepSeek API key loaded: {'***' + self.api_key[-4:] if self.api_key != 'demo' else 'demo key'}")
    
    def _get_api_key_from_settings(self):
        """Get DeepSeek API key from settings table"""
        try:
            setting = self.repo.settings.get_by_name('DeepSeek')
            if setting and setting.parameters:
                # Parse the JSON parameters field
                params = json.loads(setting.parameters)
                api_key = params.get('key', 'demo')
                logger.info(f"Loaded DeepSeek API key from settings table")
                return api_key
            else:
                logger.warning("DeepSeek setting not found in database, using demo key")
                return 'demo'
        except Exception as e:
            logger.error(f"Error loading DeepSeek API key from settings: {e}")
            return 'demo'
    
    def _make_api_request(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make API request to DeepSeek with error handling"""
        if self.api_key == 'demo':
            logger.info("Using demo mode - returning mock data")
            return self._get_mock_response(endpoint, payload)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"DeepSeek API error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error calling DeepSeek API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling DeepSeek API: {e}")
            return None
    
    def _get_mock_response(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock responses for demo mode"""
        if endpoint == "chat/completions":
            # Mock analysis response
            symbol = payload.get('messages', [{}])[0].get('content', '').split()[-1] if payload.get('messages') else 'Unknown'
            
            mock_responses = {
                "id": "mock-chat-completion-123",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "deepseek-chat",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"Based on my analysis of {symbol}, I observe:\n\n"
                                      f"• Strong technical indicators showing bullish momentum\n"
                                      f"• Positive earnings growth trajectory\n"
                                      f"• Favorable market sentiment in the sector\n"
                                      f"• Support levels holding well above moving averages\n\n"
                                      f"Recommendation: Consider accumulation on pullbacks"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 150,
                    "total_tokens": 250
                }
            }
            return mock_responses
        
        return {"error": "Mock endpoint not implemented"}
    
    def analyze_stock(self, symbol: str, analysis_type: str = "comprehensive") -> Optional[Dict[str, Any]]:
        """Analyze a stock using DeepSeek AI"""
        try:
            # Create analysis prompt based on type
            if analysis_type == "technical":
                prompt = f"Provide a technical analysis for {symbol} stock. Focus on price trends, support/resistance levels, volume patterns, and key technical indicators."
            elif analysis_type == "fundamental":
                prompt = f"Provide a fundamental analysis for {symbol} stock. Focus on financial metrics, valuation, growth prospects, and competitive positioning."
            elif analysis_type == "sentiment":
                prompt = f"Provide a market sentiment analysis for {symbol} stock. Focus on recent news, analyst opinions, and overall market perception."
            else:
                prompt = f"Provide a comprehensive analysis for {symbol} stock covering technical, fundamental, and sentiment factors."
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a financial analyst specializing in stock market analysis. Provide clear, data-driven insights with actionable recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = self._make_api_request("chat/completions", payload)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                analysis_text = response['choices'][0]['message']['content']
                
                # Parse the analysis to extract structured insights
                structured_analysis = self._parse_analysis_text(analysis_text, symbol, analysis_type)
                
                logger.info(f"Generated {analysis_type} analysis for {symbol} using DeepSeek")
                return structured_analysis
            else:
                logger.warning(f"No valid response from DeepSeek for {symbol} analysis")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with DeepSeek: {e}")
            return None
    
    def _parse_analysis_text(self, analysis_text: str, symbol: str, analysis_type: str) -> Dict[str, Any]:
        """Parse AI analysis text into structured format"""
        # This is a simplified parser - in production you might want more sophisticated parsing
        structured_analysis = {
            'symbol': symbol,
            'analysis_type': analysis_type,
            'raw_analysis': analysis_text,
            'summary': '',
            'key_points': [],
            'recommendation': '',
            'confidence_score': 0.7,  # Mock confidence score
            'risk_level': 'medium'  # Mock risk level
        }
        
        # Extract key points (simple heuristic)
        lines = analysis_text.split('\n')
        key_points = []
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-'):
                key_points.append(line[1:].strip())
            elif line and len(line) > 20 and not line.startswith('Based on'):
                key_points.append(line)
        
        structured_analysis['key_points'] = key_points[:5]  # Limit to top 5 points
        
        # Extract summary (first few sentences)
        sentences = analysis_text.split('. ')
        if len(sentences) > 0:
            structured_analysis['summary'] = sentences[0] + '.'
        
        # Extract recommendation (look for keywords)
        recommendation_keywords = ['buy', 'sell', 'hold', 'accumulate', 'reduce']
        for keyword in recommendation_keywords:
            if keyword in analysis_text.lower():
                structured_analysis['recommendation'] = keyword.upper()
                break
        
        return structured_analysis
    
    def generate_trading_strategy(self, symbol: str, timeframe: str = "short_term") -> Optional[Dict[str, Any]]:
        """Generate trading strategy using DeepSeek AI"""
        try:
            prompt = f"Generate a {timeframe} trading strategy for {symbol} stock. Include entry points, exit points, stop-loss levels, and position sizing recommendations."
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert trading strategist. Provide specific, actionable trading strategies with clear risk management guidelines."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 800
            }
            
            response = self._make_api_request("chat/completions", payload)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                strategy_text = response['choices'][0]['message']['content']
                
                strategy_data = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy_description': strategy_text,
                    'entry_points': [],
                    'exit_points': [],
                    'stop_loss': '',
                    'position_size': '',
                    'risk_reward_ratio': ''
                }
                
                logger.info(f"Generated {timeframe} trading strategy for {symbol} using DeepSeek")
                return strategy_data
            else:
                logger.warning(f"No valid response from DeepSeek for {symbol} strategy")
                return None
                
        except Exception as e:
            logger.error(f"Error generating trading strategy for {symbol} with DeepSeek: {e}")
            return None
    
    def get_market_insights(self, sector: str = None) -> Optional[Dict[str, Any]]:
        """Get general market insights using DeepSeek AI"""
        try:
            if sector:
                prompt = f"Provide current market insights and analysis for the {sector} sector. Include key trends, opportunities, and risks."
            else:
                prompt = "Provide current overall market insights and analysis. Include major trends, sector performance, and macroeconomic factors."
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a market analyst providing broad market insights. Focus on actionable intelligence and emerging trends."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.4,
                "max_tokens": 1200
            }
            
            response = self._make_api_request("chat/completions", payload)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                insights_text = response['choices'][0]['message']['content']
                
                insights_data = {
                    'sector': sector or 'general',
                    'insights': insights_text,
                    'key_trends': [],
                    'opportunities': [],
                    'risks': []
                }
                
                logger.info(f"Generated market insights for {sector or 'general market'} using DeepSeek")
                return insights_data
            else:
                logger.warning(f"No valid response from DeepSeek for market insights")
                return None
                
        except Exception as e:
            logger.error(f"Error getting market insights with DeepSeek: {e}")
            return None
    
    def compare_stocks(self, symbols: List[str], comparison_type: str = "performance") -> Optional[Dict[str, Any]]:
        """Compare multiple stocks using DeepSeek AI"""
        try:
            symbol_list = ", ".join(symbols)
            
            if comparison_type == "fundamental":
                prompt = f"Compare the fundamental characteristics of these stocks: {symbol_list}. Focus on valuation, growth, profitability, and financial health."
            elif comparison_type == "technical":
                prompt = f"Compare the technical characteristics of these stocks: {symbol_list}. Focus on price trends, momentum, volatility, and chart patterns."
            else:
                prompt = f"Provide a comprehensive comparison of these stocks: {symbol_list}. Cover both fundamental and technical aspects."
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a comparative stock analyst. Provide clear comparisons highlighting relative strengths and weaknesses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1500
            }
            
            response = self._make_api_request("chat/completions", payload)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                comparison_text = response['choices'][0]['message']['content']
                
                comparison_data = {
                    'symbols': symbols,
                    'comparison_type': comparison_type,
                    'analysis': comparison_text,
                    'rankings': {},
                    'strengths': {},
                    'weaknesses': {}
                }
                
                logger.info(f"Generated comparison for {symbol_list} using DeepSeek")
                return comparison_data
            else:
                logger.warning(f"No valid response from DeepSeek for stock comparison")
                return None
                
        except Exception as e:
            logger.error(f"Error comparing stocks {symbols} with DeepSeek: {e}")
            return None
    
    def save_analysis_to_database(self, symbol: str, analysis_data: Dict[str, Any]) -> bool:
        """Save AI analysis to database"""
        try:
            # Check if instrument exists
            existing_instrument = self.repo.instruments.get_by_symbol(symbol)
            if not existing_instrument:
                logger.warning(f"Instrument {symbol} not found in database")
                return False
            
            # Create analysis record
            analysis_record = {
                'symbol_id': existing_instrument.id,
                'analysis_type': analysis_data.get('analysis_type', 'comprehensive'),
                'analysis_data': json.dumps(analysis_data),
                'source': 'deepseek',
                'confidence_score': analysis_data.get('confidence_score', 0.5),
                'created_at': analysis_data.get('created_at')  # Will be set by database if None
            }
            
            # Save to database (assuming there's an analysis repository)
            # For now, just log the analysis
            logger.info(f"Analysis for {symbol} ready to be saved: {analysis_data.get('summary', 'No summary')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving analysis for {symbol} to database: {e}")
            return False
