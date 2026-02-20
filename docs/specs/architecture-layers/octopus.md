# Octopus Module

## Overview

The **Octopus** module is the external integration layer of the PaperProfit trading platform, designed to connect with various third-party services and APIs. Named for its ability to reach out in multiple directions like an octopus's tentacles, this module provides unified interfaces to AI platforms, data providers, and brokerage services.

## Architecture

Octopus follows a modular plugin architecture with three main submodules:

### 1. AI Platforms (`ai_platforms/`)
- **DeepSeekService** - Integration with DeepSeek AI for financial analysis
- **ClaudeService** - Integration with Anthropic's Claude AI
- **OpenAIService** - Integration with OpenAI's GPT models

### 2. Data Providers (`data_providers/`)
- **YahooFinanceService** - Real-time and historical market data from Yahoo Finance
- **AlphaVantageService** - Advanced financial data and technical indicators
- **FinancialModelingPrepService** - Fundamental data and financial statements

### 3. Brokers (`brokers/`)
- **AlpacaService** (planned) - Integration with Alpaca trading API
- **InteractiveBrokers** (planned) - Integration with Interactive Brokers API

## Key Features

### AI Integration
- **Stock Analysis**: Comprehensive AI-powered analysis of individual stocks
- **Trading Strategy Generation**: AI-generated trading strategies with entry/exit points
- **Market Insights**: Sector-specific and general market intelligence
- **Stock Comparison**: Comparative analysis of multiple stocks
- **Demo Mode**: Fallback mock responses when API keys are not configured

### Data Provider Integration
- **Real-time Quotes**: Current prices and market data
- **Historical Data**: OHLCV data with customizable timeframes
- **Fundamental Data**: Financial statements, ratios, and company information
- **Technical Indicators**: Pre-calculated technical analysis metrics
- **Market Screeners**: Top gainers/losers and stock screening

### Unified Interface
- **Consistent API**: Standardized methods across different providers
- **Error Handling**: Robust error handling and fallback mechanisms
- **Configuration Management**: API keys and settings stored in database
- **Logging**: Comprehensive logging for debugging and monitoring

## API Integration

The module is integrated with the main API through AI analysis endpoints:
- `/api/ai/analyze-stock` - Analyze stocks using selected AI platform
- `/api/ai/generate-strategy` - Generate trading strategies with AI
- `/api/ai/market-insights` - Get market insights from AI
- `/api/ai/compare-stocks` - Compare multiple stocks using AI

And data provider endpoints:
- `/api/instruments/search` - Search for instruments
- `/api/instruments/get/{symbol}` - Get instrument data
- `/api/instruments/{symbol}/market-data` - Get historical market data
- `/api/instruments/list/winners` - Get top gainers
- `/api/instruments/list/losers` - Get top losers

## Service Factory Pattern

Octopus uses a factory pattern to instantiate the appropriate service based on configuration:
```python
def get_ai_service(ai_platform: str, db_session: Session):
    """Factory function to get the appropriate AI service instance"""
    ai_platform = ai_platform.lower() if ai_platform else "deepseek"
    
    if ai_platform == "claude":
        from octopus.ai_platforms.claude import ClaudeService
        return ClaudeService(db_session)
    elif ai_platform == "openai":
        from octopus.ai_platforms.openai import OpenAIService
        return OpenAIService(db_session)
    elif ai_platform == "deepseek":
        from octopus.ai_platforms.deepseek import DeepSeekService
        return DeepSeekService(db_session)
```

## Purpose

Octopus serves as the external connectivity layer of PaperProfit, enabling the platform to leverage powerful AI analysis and comprehensive market data without being tied to any single provider. Its modular design allows for easy addition of new services and providers as the platform evolves.