#!/usr/bin/env python3

import pytz
from datetime import datetime, time, timedelta
import logging

logger = logging.getLogger(__name__)

class MarketHours:
    """Utility class to check if stock market is open"""
    
    def __init__(self):
        # US Eastern Time (NYSE/NASDAQ market hours)
        self.market_tz = pytz.timezone('US/Eastern')
        
        # Regular market hours: 9:30 AM - 4:00 PM ET
        self.market_open = time(9, 30)
        self.market_close = time(16, 0)
        
        # Extended hours (optional - for future use)
        self.pre_market_open = time(4, 0)
        self.after_market_close = time(20, 0)
    
    def is_market_open(self, check_time=None):
        """
        Check if the stock market is currently open
        Returns True if market is open, False otherwise
        """
        if check_time is None:
            check_time = datetime.now(self.market_tz)
        
        # Convert to market timezone if needed
        if check_time.tzinfo is None:
            check_time = self.market_tz.localize(check_time)
        else:
            check_time = check_time.astimezone(self.market_tz)
        
        current_time = check_time.time()
        current_date = check_time.date()
        current_weekday = check_time.weekday()
        
        # Market is closed on weekends
        if current_weekday >= 5:  # Saturday (5) or Sunday (6)
            logger.debug(f"Market closed: Weekend ({check_time.strftime('%A')})")
            return False
        
        # Check if it's a US market holiday
        if self._is_market_holiday(current_date):
            logger.debug(f"Market closed: Holiday ({current_date})")
            return False
        
        # Check if within regular market hours
        if self.market_open <= current_time <= self.market_close:
            logger.debug(f"Market open: {current_time} ET")
            return True
        
        logger.debug(f"Market closed: Outside trading hours ({current_time} ET)")
        return False
    
    def _is_market_holiday(self, date):
        """
        Check if the given date is a US stock market holiday
        This is a simplified version - in production you'd want a more comprehensive list
        """
        year = date.year
        
        # Major US market holidays (simplified list)
        holidays = [
            # New Year's Day (or observed)
            datetime(year, 1, 1).date(),
            # Martin Luther King Jr. Day (3rd Monday in January)
            self._get_nth_weekday(year, 1, 0, 3),  # 0 = Monday
            # Presidents' Day (3rd Monday in February)
            self._get_nth_weekday(year, 2, 0, 3),
            # Good Friday (varies by year - simplified)
            # Memorial Day (last Monday in May)
            self._get_last_weekday(year, 5, 0),
            # Juneteenth (June 19th)
            datetime(year, 6, 19).date(),
            # Independence Day (July 4th)
            datetime(year, 7, 4).date(),
            # Labor Day (1st Monday in September)
            self._get_nth_weekday(year, 9, 0, 1),
            # Thanksgiving Day (4th Thursday in November)
            self._get_nth_weekday(year, 11, 3, 4),  # 3 = Thursday
            # Christmas Day (December 25th)
            datetime(year, 12, 25).date(),
        ]
        
        # Handle observed holidays (if holiday falls on weekend)
        for holiday in holidays[:]:  # Create a copy for iteration
            if holiday.weekday() == 5:  # Saturday
                holidays.append(holiday - timedelta(days=1))  # Observed on Friday
            elif holiday.weekday() == 6:  # Sunday
                holidays.append(holiday + timedelta(days=1))  # Observed on Monday
        
        return date in holidays
    
    def _get_nth_weekday(self, year, month, weekday, n):
        """Get the nth weekday of a given month"""
        # weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        first_day = datetime(year, month, 1)
        first_weekday = (weekday - first_day.weekday()) % 7
        target_day = first_day + timedelta(days=first_weekday + 7*(n-1))
        return target_day.date()
    
    def _get_last_weekday(self, year, month, weekday):
        """Get the last weekday of a given month"""
        # Get first day of next month, then go backwards
        if month == 12:
            next_month = datetime(year+1, 1, 1)
        else:
            next_month = datetime(year, month+1, 1)
        
        last_day = next_month - timedelta(days=1)
        days_to_subtract = (last_day.weekday() - weekday) % 7
        if days_to_subtract == 0:
            days_to_subtract = 7
        target_day = last_day - timedelta(days=days_to_subtract)
        return target_day.date()
    
    def get_next_market_open(self):
        """Get the datetime when market will next open"""
        now = datetime.now(self.market_tz)
        
        # If market is currently open, return current time
        if self.is_market_open(now):
            return now
        
        # Find next market open time
        current_date = now.date()
        current_time = now.time()

        check_time = datetime.now(self.market_tz)
        current_weekday = check_time.weekday()
        
        # Check today first
        if current_weekday < 5 and not self._is_market_holiday(current_date):
            if current_time < self.market_open:
                # Market opens later today
                next_open = datetime.combine(current_date, self.market_open)
                return self.market_tz.localize(next_open)
        
        # Find next trading day
        days_ahead = 1
        while True:
            next_date = current_date + timedelta(days=days_ahead)
            next_weekday = next_date.weekday()
            
            if next_weekday < 5 and not self._is_market_holiday(next_date):
                next_open = datetime.combine(next_date, self.market_open)
                return self.market_tz.localize(next_open)
            
            days_ahead += 1
    
    def get_market_status(self):
        """Get current market status as a string"""
        if self.is_market_open():
            return "OPEN"
        else:
            next_open = self.get_next_market_open()
            return f"CLOSED - Next open: {next_open.strftime('%Y-%m-%d %H:%M ET')}"


# Global instance for easy access
market_hours = MarketHours()
