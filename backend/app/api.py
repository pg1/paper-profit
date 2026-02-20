#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import yaml
import os
from pathlib import Path

from storage.database import get_db
from services.account_service import AccountService
from storage.repositories import InstrumentRepository, OrderRepository, RepositoryFactory
from storage.models import Strategy
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

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
    else:
        raise ValueError(f"Unsupported AI platform: {ai_platform}. Supported platforms: claude, deepseek, openai")


app = FastAPI(title="PaperProfit API", version="1.0.0")

# Enable CORS for all routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for front end release
dist_path = Path(__file__).parent.parent.parent / "frontend" / "release"

# Mount assets directory
app.mount("/assets", StaticFiles(directory=dist_path / "assets"), name="assets")

# Mount images directory if it exists
images_path = dist_path / "images"
if images_path.exists():
    app.mount("/images", StaticFiles(directory=images_path), name="images")


@app.get("/api/accounts", response_model=List[Dict[str, Any]])
async def get_all_accounts(db: Session = Depends(get_db)):
    """Get all accounts"""
    try:
        account_service = AccountService(db)
        accounts = account_service.get_all_accounts()
        
        result = []
        for account in accounts:
            # Calculate portfolio value from positions
            portfolio_value = 0.0
            for position in account.positions:
                if position.current_price and position.quantity:
                    position_value = float(position.quantity) * float(position.current_price)
                    portfolio_value += position_value
            
            total_equity = float(account.cash_balance) + portfolio_value
            
            # Calculate total P&L from positions
            total_unrealized_pnl = 0.0
            total_realized_pnl = 0.0
            
            for position in account.positions:
                if position.unrealized_pnl:
                    total_unrealized_pnl += float(position.unrealized_pnl)
            
            # Calculate realized P&L from trades (simplified - would need to iterate through trades)
            # For now, we'll just use unrealized P&L
            
            total_pnl = total_unrealized_pnl + total_realized_pnl
            
            # Calculate gain/loss percentage as percentage of total equity
            gain_loss_percentage = 0.0
            if total_equity > 0:
                gain_loss_percentage = (total_pnl / total_equity) * 100
            
            result.append({
                "account_id": account.account_id,
                "account_name": account.account_name,
                "account_type": account.account_type,
                "cash_balance": float(account.cash_balance),
                "total_equity": total_equity,
                "gain_loss_percentage": round(gain_loss_percentage, 2),
                "currency": account.currency,
                "status": account.status,
                "is_active": account.is_active,
                "strategy_id": account.strategy_id,
                "strategy_name": account.strategy.name if account.strategy else None,
                "created_at": account.created_at,
                "updated_at": account.updated_at
            })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )


@app.get("/api/accounts/{account_id}", response_model=Dict[str, Any])
async def get_account(account_id: str, db: Session = Depends(get_db)):
    """Get account by ID"""
    try:
        account_service = AccountService(db)
        account = account_service.get_account_by_id(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
        
        return {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "account_type": account.account_type,
            "cash_balance": float(account.cash_balance),
            "currency": account.currency,
            "status": account.status,
            "is_active": account.is_active,
            "strategy_id": account.strategy_id,
            "created_at": account.created_at,
            "updated_at": account.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve account: {str(e)}"
        )


@app.post("/api/accounts", response_model=Dict[str, Any])
async def create_account(account_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new account"""
    try:
        # Handle both old and new payload formats
        if 'initial_balance' in account_data and 'cash_balance' not in account_data:
            # Convert new format to old format for service compatibility
            account_data['cash_balance'] = account_data['initial_balance']
        
        # Set account_name from account_id if not provided (backward compatibility)
        if 'account_name' not in account_data and 'account_id' in account_data:
            account_data['account_name'] = account_data['account_id']
        
        account_service = AccountService(db)
        account = account_service.create_account(account_data)
        return {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "account_type": account.account_type,
            "cash_balance": float(account.cash_balance),
            "currency": account.currency,
            "status": account.status,
            "is_active": account.is_active,
            "created_at": account.created_at,
            "updated_at": account.updated_at
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@app.put("/api/accounts/{account_id}", response_model=Dict[str, Any])
async def update_account(account_id: str, account_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Update an existing account"""
    try:
        account_service = AccountService(db)
        account = account_service.update_account(account_id, account_data)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
        
        return {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "account_type": account.account_type,
            "cash_balance": float(account.cash_balance),
            "currency": account.currency,
            "status": account.status,
            "is_active": account.is_active,
            "strategy_id": account.strategy_id,
            "created_at": account.created_at,
            "updated_at": account.updated_at
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account: {str(e)}"
        )


@app.get("/api/accounts/{account_id}/summary", response_model=Dict[str, Any])
async def get_account_summary(account_id: str, db: Session = Depends(get_db)):
    """Get account summary including positions and performance"""
    try:
        account_service = AccountService(db)
        summary = account_service.get_account_summary(account_id)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve account summary: {str(e)}"
        )


@app.post("/api/accounts/{account_id}/buy", response_model=Dict[str, Any])
async def buy_asset(account_id: str, order_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a buy order for an account. Expected payload: { stock_symbol: str, shares: number, order_type?: 'market'|'limit'|'stop' }"""
    try:
        account_service = AccountService(db)
        order = account_service.create_buy_order(account_id, order_data)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create buy order: {str(e)}"
        )


@app.post("/api/accounts/{account_id}/sell", response_model=Dict[str, Any])
async def sell_asset(account_id: str, order_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a sell order for an account. Expected payload: { stock_symbol: str, shares: number, order_type?: 'market'|'limit'|'stop' }"""
    try:
        account_service = AccountService(db)
        order = account_service.create_sell_order(account_id, order_data)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sell order: {str(e)}"
        )


@app.get("/api/accounts/{account_id}/portfolio", response_model=Dict[str, Any])
async def get_account_portfolio(account_id: str, db: Session = Depends(get_db)):
    """Get account portfolio holdings"""
    try:
        account_service = AccountService(db)
        portfolio = account_service.get_account_portfolio(account_id)
        return portfolio
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve portfolio: {str(e)}"
        )


@app.get("/api/accounts/{account_id}/performance", response_model=Dict[str, Any])
async def get_account_performance(account_id: str, db: Session = Depends(get_db)):
    """Get account performance metrics"""
    try:
        account_service = AccountService(db)
        performance = account_service.get_account_performance(account_id)
        return performance
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve account performance: {str(e)}"
        )


@app.get("/api/strategies", response_model=List[Dict[str, Any]])
async def get_all_strategies(db: Session = Depends(get_db)):
    """Get all strategies"""
    try:
        repo_factory = RepositoryFactory(db)
        strategies = repo_factory.strategies.get_all()
        return [{
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "parameters": strategy.parameters,
            "category": strategy.category,
            "strategy_type": strategy.strategy_type,
            "stock_list_mode": strategy.stock_list_mode,
            "stock_list": strategy.stock_list,
            "stock_list_ai_prompt": strategy.stock_list_ai_prompt,
            "parameters": strategy.parameters,
            "is_active": strategy.is_active,
            "created_at": strategy.created_at
        } for strategy in strategies]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategies: {str(e)}"
        )


@app.post("/api/strategies", response_model=Dict[str, Any])
async def create_strategy(strategy_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new strategy"""
    try:
        # Validate required fields
        if not strategy_data.get('name'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strategy name is required"
            )

        # Check if strategy with same name already exists
        repo_factory = RepositoryFactory(db)
        existing_strategy = repo_factory.strategies.get_by_name(strategy_data['name'])
        if existing_strategy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strategy with name '{strategy_data['name']}' already exists"
            )

        # Prepare strategy data for creation
        strategy_payload = {
            "name": strategy_data['name'],
            "description": strategy_data.get('description', ''),
            "parameters": strategy_data.get('parameters', {}),
            "category": strategy_data.get('category', 'Long'),
            "strategy_type": strategy_data.get('strategy_type', 'Buy Hold'),
            "stock_list_mode": strategy_data.get('stock_list_mode', 'Manual'),
            "stock_list": strategy_data.get('stock_list', ''),
            "stock_list_ai_prompt": strategy_data.get('stock_list_ai_prompt', ''),
            "parameters": strategy_data.get('parameters', '{}'),
            "is_active": strategy_data.get('is_active', True)
        }

        # Create the strategy
        strategy = repo_factory.strategies.create(strategy_payload)
        
        return {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "parameters": strategy.parameters,
            "category": strategy.category,
            "strategy_type": strategy.strategy_type,
            "stock_list_mode": strategy.stock_list_mode,
            "stock_list": strategy.stock_list,
            "stock_list_ai_prompt": strategy.stock_list_ai_prompt,
            "parameters": strategy.parameters,
            "is_active": strategy.is_active,
            "created_at": strategy.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy: {str(e)}"
        )


@app.get("/api/strategies/{strategy_id}", response_model=Dict[str, Any])
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Get strategy by ID"""
    try:
        repo_factory = RepositoryFactory(db)
        strategy = repo_factory.strategies.get_by_id(strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy with ID {strategy_id} not found"
            )
        
        return {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "parameters": strategy.parameters,
            "category": strategy.category,
            "strategy_type": strategy.strategy_type,
            "stock_list_mode": strategy.stock_list_mode,
            "stock_list": strategy.stock_list,
            "stock_list_ai_prompt": strategy.stock_list_ai_prompt,
            "parameters": strategy.parameters,
            "is_active": strategy.is_active,
            "created_at": strategy.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategy: {str(e)}"
        )


@app.get("/api/trading-signals", response_model=List[Dict[str, Any]])
async def get_trading_signals(limit: int = 25, strategy_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get recent trading signals, optionally filtered by strategy_id"""
    try:
        repo_factory = RepositoryFactory(db)
        signals = repo_factory.trading_signals.get_recent_signals(strategy_id=strategy_id, limit=limit)
        
        result = []
        for signal in signals:
            # Get instrument symbol
            instrument = repo_factory.instruments.get_by_id(signal.symbol_id)
            # Get strategy name
            strategy = repo_factory.strategies.get_by_id(signal.strategy_id)
            
            # Parse indicators_used JSON if it exists
            indicators_used = {}
            if signal.indicators_used:
                try:
                    import json
                    indicators_used = json.loads(signal.indicators_used)
                except:
                    indicators_used = {}
            
            result.append({
                "id": signal.id,
                "symbol": instrument.symbol if instrument else f"ID:{signal.symbol_id}",
                "symbol_name": instrument.name if instrument else None,
                "strategy": strategy.name if strategy else f"ID:{signal.strategy_id}",
                "timestamp": signal.timestamp,
                "signal_type": signal.signal_type,
                "strength": float(signal.strength) if signal.strength else None,
                "price": float(signal.price) if signal.price else None,
                "confidence": float(signal.confidence) if signal.confidence else None,
                "reason": signal.reason,
                "indicators_used": indicators_used,
                "created_at": signal.created_at
            })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trading signals: {str(e)}"
        )


@app.put("/api/strategies/{strategy_id}", response_model=Dict[str, Any])
async def update_strategy(strategy_id: int, strategy_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Update an existing strategy"""
    try:
        repo_factory = RepositoryFactory(db)
        strategy = repo_factory.strategies.get_by_id(strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy with ID {strategy_id} not found"
            )

        # Validate required fields
        if not strategy_data.get('name'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strategy name is required"
            )

        # Check if strategy with same name already exists (excluding current strategy)
        existing_strategy = repo_factory.strategies.get_by_name(strategy_data['name'])
        if existing_strategy and existing_strategy.id != strategy_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strategy with name '{strategy_data['name']}' already exists"
            )

        # Prepare update data
        update_data = {
            "name": strategy_data['name'],
            "description": strategy_data.get('description', strategy.description),
            "parameters": strategy_data.get('parameters', strategy.parameters),
            "category": strategy_data.get('category', strategy.category),
            "strategy_type": strategy_data.get('strategy_type', strategy.strategy_type),
            "stock_list_mode": strategy_data.get('stock_list_mode', strategy.stock_list_mode),
            "stock_list": strategy_data.get('stock_list', strategy.stock_list),
            "stock_list_ai_prompt": strategy_data.get('stock_list_ai_prompt', strategy.stock_list_ai_prompt),
            "is_active": strategy_data.get('is_active', strategy.is_active)
        }

        # Update the strategy
        updated_strategy = repo_factory.strategies.update(strategy_id, update_data)
        
        return {
            "id": updated_strategy.id,
            "name": updated_strategy.name,
            "description": updated_strategy.description,
            "parameters": updated_strategy.parameters,
            "category": updated_strategy.category,
            "strategy_type": updated_strategy.strategy_type,
            "stock_list_mode": updated_strategy.stock_list_mode,
            "stock_list": updated_strategy.stock_list,
            "stock_list_ai_prompt": updated_strategy.stock_list_ai_prompt,
            "is_active": updated_strategy.is_active,
            "created_at": updated_strategy.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy: {str(e)}"
        )


@app.get("/api/settings", response_model=List[Dict[str, Any]])
async def get_all_settings(category: str = None, db: Session = Depends(get_db)):
    """Get all settings, optionally filtered by category"""
    try:
        repo_factory = RepositoryFactory(db)
        if category:
            settings = repo_factory.settings.get_by_category(category)
        else:
            settings = repo_factory.settings.get_all()
        
        return [{
            "name": setting.name,
            "parameters": setting.parameters,
            "category": setting.category,
            "is_active": setting.is_active,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at
        } for setting in settings]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


@app.get("/api/settings/{name}", response_model=Dict[str, Any])
async def get_setting(name: str, db: Session = Depends(get_db)):
    """Get setting by name"""
    try:
        repo_factory = RepositoryFactory(db)
        setting = repo_factory.settings.get_by_name(name)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting with name '{name}' not found"
            )
        
        return {
            "name": setting.name,
            "parameters": setting.parameters,
            "category": setting.category,
            "is_active": setting.is_active,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve setting: {str(e)}"
        )


@app.post("/api/settings", response_model=Dict[str, Any])
async def create_setting(setting_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new setting"""
    try:
        # Validate required fields
        if not setting_data.get('name'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setting name is required"
            )

        # Check if setting with same name already exists
        repo_factory = RepositoryFactory(db)
        existing_setting = repo_factory.settings.get_by_name(setting_data['name'])
        if existing_setting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Setting with name '{setting_data['name']}' already exists"
            )

        # Prepare setting data for creation
        setting_payload = {
            "name": setting_data['name'],
            "parameters": setting_data.get('parameters', ''),
            "category": setting_data.get('category', 'general'),
            "is_active": setting_data.get('is_active', True)
        }

        # Create the setting
        setting = repo_factory.settings.create(setting_payload)
        
        return {
            "name": setting.name,
            "parameters": setting.parameters,
            "category": setting.category,
            "is_active": setting.is_active,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create setting: {str(e)}"
        )


@app.put("/api/settings/{name}", response_model=Dict[str, Any])
async def update_setting(name: str, setting_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Update an existing setting"""
    try:
        repo_factory = RepositoryFactory(db)
        setting = repo_factory.settings.get_by_name(name)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting with name '{name}' not found"
            )

        # Prepare update data (only include fields that are allowed to be updated)
        update_data = {}
        allowed_fields = ['parameters', 'category', 'is_active']
        
        for field in allowed_fields:
            if field in setting_data:
                update_data[field] = setting_data[field]

        # Update the setting
        updated_setting = repo_factory.settings.update(name, update_data)
        
        return {
            "name": updated_setting.name,
            "parameters": updated_setting.parameters,
            "category": updated_setting.category,
            "is_active": updated_setting.is_active,
            "created_at": updated_setting.created_at,
            "updated_at": updated_setting.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}"
        )


@app.delete("/api/settings/{name}")
async def delete_setting(name: str, db: Session = Depends(get_db)):
    """Delete a setting"""
    try:
        repo_factory = RepositoryFactory(db)
        setting = repo_factory.settings.get_by_name(name)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting with name '{name}' not found"
            )

        # Delete the setting (soft delete by setting is_active=False)
        success = repo_factory.settings.delete(name)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete setting '{name}'"
            )

        return {"message": f"Setting '{name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete setting: {str(e)}"
        )


@app.get("/api/instruments/search", response_model=List[Dict[str, Any]])
async def search_instruments(query: str, limit: int = 20):
    """Search for instruments by query string"""
    try:
        import yfinance as yf
        
        # Perform search using yfinance
        search = yf.Search(query)
        
        # Get quotes and limit to requested number
        quotes = search.quotes[:limit] if search.quotes else []
        
        # Format the response
        results = []
        for quote in quotes:
            result = {
                "symbol": quote.get("symbol"),
                "name": quote.get("longname") or quote.get("shortname"),
                "exchange": quote.get("exchange"),
                "exchange_display": quote.get("exchDisp"),
                "type": quote.get("quoteType"),
                "type_display": quote.get("typeDisp"),
                "sector": quote.get("sector"),
                "sector_display": quote.get("sectorDisp"),
                "industry": quote.get("industry"),
                "industry_display": quote.get("industryDisp"),
                "score": quote.get("score")
            }
            results.append(result)
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search instruments: {str(e)}"
        )


@app.get("/api/instruments/get/{symbol}", response_model=Dict[str, Any])
async def get_instrument(symbol: str, db: Session = Depends(get_db)):
    """Get instrument data by symbol using Yahoo Finance"""
    try:
        from octopus.data_providers.yahoo_finance import YahooFinanceService
        
        # Create Yahoo Finance service instance
        yahoo_service = YahooFinanceService(db)
        
        # Fetch current price and basic info
        current_price_data = yahoo_service.fetch_current_price(symbol)
        if not current_price_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument with symbol '{symbol}' not found or no data available"
            )
        
        # Fetch additional stock information
        stock_info = yahoo_service.fetch_stock_info(symbol)
        
        # Combine the data
        instrument_data = {
            "symbol": current_price_data["symbol"],
            "name": current_price_data["company_name"],
            "current_price": current_price_data["price"],
            "currency": current_price_data["currency"],
            "exchange": current_price_data["exchange"],
            "sector": current_price_data["sector"]
        }
        
        # Add additional info if available
        if stock_info:
            instrument_data.update({
                "market_cap": stock_info.get("market_cap"),
                "pe_ratio": stock_info.get("pe_ratio"),
                "dividend_yield": stock_info.get("dividend_yield"),
                "beta": stock_info.get("beta"),
                "fifty_two_week_high": stock_info.get("fifty_two_week_high"),
                "fifty_two_week_low": stock_info.get("fifty_two_week_low"),
                "industry": stock_info.get("industry")
            })
        
        return instrument_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve instrument data: {str(e)}"
        )


@app.get("/api/instruments/{symbol}/market-data", response_model=List[Dict[str, Any]])
async def get_instrument_market_data(symbol: str, period: str = "1mo", db: Session = Depends(get_db)):
    """Get market data for an instrument with time period controls"""
    try:
        from octopus.data_providers.yahoo_finance import YahooFinanceService
        
        # Create Yahoo Finance service instance
        yahoo_service = YahooFinanceService(db)
        
        # Map period to yfinance compatible periods
        period_mapping = {
            "1d": "1d",
            "1w": "1wk",
            "1m": "1mo",
            "3m": "3mo",
            "6m": "6mo",
            "ytd": "ytd",
            "1y": "1y"
        }
        
        # Default to 1 month if period not recognized
        yfinance_period = period_mapping.get(period, "1mo")
        
        # Fetch historical data
        historical_data = yahoo_service.fetch_historical_data(symbol, yfinance_period)
        
        if not historical_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No market data available for symbol '{symbol}' with period '{period}'"
            )
        
        return historical_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve market data: {str(e)}"
        )


@app.get("/api/instruments/list/winners", response_model=List[Dict[str, Any]])
async def get_top_gainers(limit: int = 20):
    """Get top gainers (winners) using Yahoo Finance screener"""
    try:
        from yfinance import screener
        
        # Get day gainers using yfinance screener
        result = screener.screen('day_gainers', count=limit)
        
        if not result or 'quotes' not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No gainers data available"
            )
        
        quotes = result['quotes']
        
        # Format the response to match frontend expectations
        formatted_results = []
        for quote in quotes:
            symbol = quote.get('symbol')
            name = quote.get('longName') or quote.get('shortName') or symbol
            price = quote.get('regularMarketPrice')
            change = quote.get('regularMarketChange')
            change_percent = quote.get('regularMarketChangePercent')
            volume = quote.get('regularMarketVolume')
             
            formatted_results.append({
                "symbol": symbol,
                "name": name,
                "price": price,
                "volume": format_volume(volume) if volume else "N/A",
                "change_percent": change_percent,
                "change_amount": change,
                "market_cap": quote.get('marketCap'),
                "exchange": quote.get('fullExchangeName') or quote.get('exchange'),
                "sector": quote.get('sector') or quote.get('sectorDisp', 'N/A')
            })
        
        return formatted_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve top gainers: {str(e)}"
        )


@app.get("/api/instruments/list/losers", response_model=List[Dict[str, Any]])
async def get_top_losers(limit: int = 20):
    """Get top losers using Yahoo Finance screener"""
    try:
        from yfinance import screener
        
        # Get day losers using yfinance screener
        result = screener.screen('day_losers', count=limit)
        
        if not result or 'quotes' not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No losers data available"
            )
        
        quotes = result['quotes']
        
        # Format the response to match frontend expectations
        formatted_results = []
        for quote in quotes:
            symbol = quote.get('symbol')
            name = quote.get('longName') or quote.get('shortName') or symbol
            price = quote.get('regularMarketPrice')
            change = quote.get('regularMarketChange')
            change_percent = quote.get('regularMarketChangePercent')
            volume = quote.get('regularMarketVolume')
            
            
            formatted_results.append({
                "symbol": symbol,
                "name": name,
                "price": price,
                "volume": format_volume(volume) if volume else "N/A",
                "change_percent": change_percent,
                "change_amount": change,
                "market_cap": quote.get('marketCap'),
                "exchange": quote.get('fullExchangeName') or quote.get('exchange'),
                "sector": quote.get('sector') or quote.get('sectorDisp', 'N/A')
            })
        
        return formatted_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve top losers: {str(e)}"
        )


def format_volume(volume):
    """Format volume to human readable format (K, M, B)"""
    if volume >= 1_000_000_000:
        return f"{volume/1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        return f"{volume/1_000_000:.2f}M"
    elif volume >= 1_000:
        return f"{volume/1_000:.2f}K"
    else:
        return str(volume)


@app.get("/api/watchlist", response_model=List[Dict[str, Any]])
async def get_watchlist(db: Session = Depends(get_db)):
    """Get all instruments in the watchlist"""
    try:
        repo_factory = RepositoryFactory(db)
        watchlist_instruments = repo_factory.instruments.get_watchlist()
        
        result = []
        for instrument in watchlist_instruments:
            # Try to get current price from Yahoo Finance
            current_price = None
            try:
                from octopus.data_providers.yahoo_finance import YahooFinanceService
                yahoo_service = YahooFinanceService(db)
                price_data = yahoo_service.fetch_current_price(instrument.symbol)
                if price_data:
                    current_price = price_data.get("price")
            except:
                current_price = None
            
            result.append({
                "id": instrument.id,
                "symbol": instrument.symbol,
                "name": instrument.name,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "watch_list": instrument.watch_list,
                "current_price": current_price,
                "overall_score": instrument.overall_score,
                "risk_score": instrument.risk_score,
                "sector": instrument.sector,
                "is_active": instrument.is_active,
                "created_at": instrument.created_at,
                "updated_at": instrument.updated_at
            })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve watchlist: {str(e)}"
        )


@app.post("/api/watchlist/{symbol}", response_model=Dict[str, Any])
async def add_to_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Add an instrument to the watchlist"""
    try:
        repo_factory = RepositoryFactory(db)
        instrument = repo_factory.instruments.add_to_watchlist(symbol)
        
        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add {symbol} to watchlist"
            )
        
        return {
            "id": instrument.id,
            "symbol": instrument.symbol,
            "name": instrument.name,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "watch_list": instrument.watch_list,
            "overall_score": instrument.overall_score,
            "risk_score": instrument.risk_score,
            "sector": instrument.sector,
            "is_active": instrument.is_active,
            "created_at": instrument.created_at,
            "updated_at": instrument.updated_at,
            "message": f"Successfully added {symbol} to watchlist"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add {symbol} to watchlist: {str(e)}"
        )


@app.delete("/api/watchlist/{symbol}", response_model=Dict[str, Any])
async def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Remove an instrument from the watchlist"""
    try:
        repo_factory = RepositoryFactory(db)
        instrument = repo_factory.instruments.remove_from_watchlist(symbol)
        
        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument {symbol} not found"
            )
        
        return {
            "id": instrument.id,
            "symbol": instrument.symbol,
            "name": instrument.name,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "watch_list": instrument.watch_list,
            "is_active": instrument.is_active,
            "created_at": instrument.created_at,
            "updated_at": instrument.updated_at,
            "message": f"Successfully removed {symbol} from watchlist"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove {symbol} from watchlist: {str(e)}"
        )


@app.get("/api/watchlist/{symbol}/status", response_model=Dict[str, Any])
async def check_watchlist_status(symbol: str, db: Session = Depends(get_db)):
    """Check if an instrument is in the watchlist"""
    try:
        repo_factory = RepositoryFactory(db)
        is_in_watchlist = repo_factory.instruments.is_in_watchlist(symbol)
        
        # Get instrument details if it exists
        instrument = repo_factory.instruments.get_by_symbol(symbol)
        
        response = {
            "symbol": symbol,
            "in_watchlist": is_in_watchlist
        }
        
        if instrument:
            response.update({
                "id": instrument.id,
                "name": instrument.name,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "watch_list": instrument.watch_list,
                "is_active": instrument.is_active
            })
        
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check watchlist status for {symbol}: {str(e)}"
        )


@app.get("/api/service-list", response_model=List[Dict[str, Any]])
async def get_service_list():
    """Get service list from YAML configuration"""
    try:
        # Path to the service list settings YAML file
        yaml_path = os.path.join(os.path.dirname(__file__), 'config', 'service-list-settings.yaml')
        
        # Check if file exists
        if not os.path.exists(yaml_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service list configuration file not found"
            )
        
        # Read and parse YAML file
        with open(yaml_path, 'r') as file:
            service_data = yaml.safe_load(file)
        
        # Return the categories with services
        return service_data.get('categories', [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve service list: {str(e)}"
        )


@app.get("/api/strategy-list", response_model=List[Dict[str, Any]])
async def get_strategy_list():
    """Get strategy list from YAML configuration"""
    try:
        # Path to the strategy list YAML file
        yaml_path = os.path.join(os.path.dirname(__file__), 'config', 'strategy-list.yaml')
        
        # Check if file exists
        if not os.path.exists(yaml_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy list configuration file not found"
            )
        
        # Read and parse YAML file
        with open(yaml_path, 'r') as file:
            strategy_data = yaml.safe_load(file)
        
        # Return the strategies
        return strategy_data.get('strategies', [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve strategy list: {str(e)}"
        )


def decode_gzip_base64_content(encoded_data):
    """Decode gzip+base64 encoded content"""
    try:
        import base64
        import gzip
        
        # Decode base64
        decoded_bytes = base64.b64decode(encoded_data)
        
        # Decompress gzip
        decompressed_bytes = gzip.decompress(decoded_bytes)
        
        # Convert to string
        return decompressed_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decode gzip+base64 content: {str(e)}")


def process_guide_content(guide_data):
    """Process guide data to decode gzip+base64 content"""
    if not isinstance(guide_data, list):
        return guide_data
    
    processed_chapters = []
    for chapter in guide_data:
        processed_chapter = chapter.copy()
        
        # Process sections if they exist
        if 'sections' in chapter and isinstance(chapter['sections'], list):
            processed_sections = []
            for section in chapter['sections']:
                processed_section = section.copy()
                
                # Decode content if it's gzip+base64 encoded
                if ('content' in section and 
                    isinstance(section['content'], dict) and
                    section['content'].get('encoding') == 'gzip+base64' and
                    'data' in section['content']):
                    
                    try:
                        decoded_content = decode_gzip_base64_content(section['content']['data'])
                        processed_section['content'] = decoded_content
                    except Exception as e:
                        processed_section['content'] = f"Error decoding content: {str(e)}"
                
                processed_sections.append(processed_section)
            
            processed_chapter['sections'] = processed_sections
        
        processed_chapters.append(processed_chapter)
    
    return processed_chapters


@app.get("/api/guide", response_model=Dict[str, Any])
async def get_guide():
    """Get investment guide from YAML configuration"""
    try:
        # Path to the guide YAML file
        yaml_path = os.path.join(os.path.dirname(__file__), 'config', 'guide.yaml')
        
        # Check if file exists
        if not os.path.exists(yaml_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guide configuration file not found"
            )
        
        # Read and parse YAML file
        with open(yaml_path, 'r') as file:
            guide_data = yaml.safe_load(file)
        
        # Process the guide data to decode gzip+base64 content
        processed_chapters = process_guide_content(guide_data)
        
        # Return the guide data in the expected format for the frontend
        return {
            "title": "Investment Guide",
            "chapters": processed_chapters
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve guide: {str(e)}"
        )


@app.post("/api/ai/analyze-stock", response_model=Dict[str, Any])
async def analyze_stock_with_ai(analysis_request: Dict[str, Any], db: Session = Depends(get_db)):
    """Analyze a stock using AI (claude, deepseek, or openai)"""
    try:
        symbol = analysis_request.get('symbol')
        analysis_type = analysis_request.get('analysis_type', 'comprehensive')
        ai_platform = analysis_request.get('ai', 'deepseek')
        
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock symbol is required"
            )
        
        # Get the appropriate AI service
        ai_service = get_ai_service(ai_platform, db)
        
        # Perform analysis
        analysis_result = ai_service.analyze_stock(symbol, analysis_type)
        
        if not analysis_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate analysis for {symbol} using {ai_platform}"
            )
        
        return analysis_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze stock with AI: {str(e)}"
        )


@app.post("/api/ai/generate-strategy", response_model=Dict[str, Any])
async def generate_trading_strategy(strategy_request: Dict[str, Any], db: Session = Depends(get_db)):
    """Generate trading strategy using AI (claude, deepseek, or openai)"""
    try:
        symbol = strategy_request.get('symbol')
        timeframe = strategy_request.get('timeframe', 'short_term')
        ai_platform = strategy_request.get('ai', 'deepseek')
        
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock symbol is required"
            )
        
        # Get the appropriate AI service
        ai_service = get_ai_service(ai_platform, db)
        
        # Generate strategy
        strategy_result = ai_service.generate_trading_strategy(symbol, timeframe)
        
        if not strategy_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate trading strategy for {symbol} using {ai_platform}"
            )
        
        return strategy_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate trading strategy: {str(e)}"
        )


@app.get("/api/ai/market-insights", response_model=Dict[str, Any])
async def get_market_insights(sector: str = None, ai: str = "deepseek", db: Session = Depends(get_db)):
    """Get market insights using AI (claude, deepseek, or openai)"""
    try:
        # Get the appropriate AI service
        ai_service = get_ai_service(ai, db)
        
        # Get market insights
        insights_result = ai_service.get_market_insights(sector)
        
        if not insights_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate market insights using {ai}"
            )
        
        return insights_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market insights: {str(e)}"
        )


@app.post("/api/ai/compare-stocks", response_model=Dict[str, Any])
async def compare_stocks_with_ai(comparison_request: Dict[str, Any], db: Session = Depends(get_db)):
    """Compare multiple stocks using AI (claude, deepseek, or openai)"""
    try:
        symbols = comparison_request.get('symbols', [])
        comparison_type = comparison_request.get('comparison_type', 'performance')
        ai_platform = comparison_request.get('ai', 'deepseek')
        
        if not symbols or len(symbols) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least two stock symbols are required for comparison"
            )
        
        # Get the appropriate AI service
        ai_service = get_ai_service(ai_platform, db)
        
        # Compare stocks
        comparison_result = ai_service.compare_stocks(symbols, comparison_type)
        
        if not comparison_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to compare stocks using {ai_platform}: {', '.join(symbols)}"
            )
        
        return comparison_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare stocks with AI: {str(e)}"
        )


@app.get("/api/learning-days/{day}/study")
async def get_learning_day_study(day: int):
    """Get study content for a learning day"""
    try:
        # Path to the study.txt file
        study_path = Path(__file__).parent / "neumann" / str(day) / "study.txt"
        
        # Check if file exists
        if not study_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Study content for day {day} not found"
            )
        
        # Read and return the study content
        with open(study_path, 'r') as file:
            study_content = file.read()
        
        return {
            "day": day,
            "content": study_content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve study content: {str(e)}"
        )


@app.get("/api/learning-days/{day}/quiz")
async def get_learning_day_quiz(day: int):
    """Get quiz data for a learning day"""
    try:
        # Path to the quiz.json file
        quiz_path = Path(__file__).parent / "neumann" / str(day) / "quiz.json"
        
        # Check if file exists
        if not quiz_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quiz for day {day} not found"
            )
        
        # Read and parse the quiz JSON
        with open(quiz_path, 'r') as file:
            import json
            quiz_data = json.load(file)
        
        return {
            "day": day,
            **quiz_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quiz data: {str(e)}"
        )


@app.get("/api/learning-days/{day}/exercise")
async def get_learning_day_exercise(day: int):
    """Get exercise HTML content for a learning day"""
    try:
        # Path to the exercise.html file
        exercise_path = Path(__file__).parent / "neumann" / str(day) / "exercise.html"
        
        # Check if file exists
        if not exercise_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exercise for day {day} not found"
            )
        
        # Read and return the exercise HTML content
        with open(exercise_path, 'r') as file:
            exercise_content = file.read()
        
        return {
            "day": day,
            "content": exercise_content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve exercise content: {str(e)}"
        )


@app.get("/api/learning-days/{day}/image")
async def get_learning_day_image(day: int):
    """Get image for a learning day"""
    try:
        # Path to the 1.png file
        image_path = Path(__file__).parent / "neumann" / str(day) / "1.png"
        
        # Check if file exists
        if not image_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image for day {day} not found"
            )
        
        # Return the image file
        return FileResponse(image_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve image: {str(e)}"
        )


@app.get("/api/learning-days", response_model=Dict[str, Any])
async def get_learning_day_list():
    """Get learning day list from YAML configuration"""
    try:
        # Path to the learning day list YAML file
        yaml_path = os.path.join(os.path.dirname(__file__), 'neumann', 'learning-day-list.yaml')
        
        # Check if file exists
        if not os.path.exists(yaml_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning day list configuration file not found"
            )
        
        # Read and parse YAML file
        with open(yaml_path, 'r') as file:
            learning_day_data = yaml.safe_load(file)
        
        # Return the learning day data
        return learning_day_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve learning day list: {str(e)}"
        )


# Serve index.html for all other routes (SPA support)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if the path is a file that exists
    file_path = dist_path / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # Otherwise, serve index.html for Vue Router
    return FileResponse(dist_path / "index.html")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
