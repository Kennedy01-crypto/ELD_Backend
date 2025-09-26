"""
Hours of Service (HOS) Compliance Engine
Implements FMCSA HOS regulations for property-carrying drivers
"""
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from .models import Driver, DutyStatus, HOSViolation
import logging

logger = logging.getLogger(__name__)


class HOSEngine:
    """Main HOS compliance engine"""
    
    def __init__(self):
        self.config = settings.HOS_CONFIG
    
    def calculate_available_driving_hours(self, driver, current_time=None):
        """
        Calculate available driving hours for a driver at a given time
        Returns: dict with available hours and constraints
        """
        if current_time is None:
            current_time = timezone.now()
        
        # Get current duty status
        current_duty = self.get_current_duty_status(driver, current_time)
        
        # Calculate 14-hour window constraint
        window_hours = self.calculate_14_hour_window_hours(driver, current_time)
        
        # Calculate 11-hour driving limit
        driving_hours = self.calculate_driving_hours_today(driver, current_time)
        available_driving = max(0, self.config['MAX_DRIVING_HOURS'] - driving_hours)
        
        # Calculate weekly limit
        weekly_hours = self.calculate_weekly_hours(driver, current_time)
        max_weekly = self.config['MAX_DAILY_HOURS_70_8_DAY'] if driver.hos_rule_type == '70_8' else self.config['MAX_DAILY_HOURS_60_7_DAY']
        available_weekly = max(0, max_weekly - weekly_hours)
        
        # Calculate required rest break
        rest_break_required = self.is_rest_break_required(driver, current_time)
        
        return {
            'available_driving_hours': min(available_driving, window_hours),
            'window_hours_remaining': window_hours,
            'driving_hours_used': driving_hours,
            'weekly_hours_used': weekly_hours,
            'weekly_hours_available': available_weekly,
            'rest_break_required': rest_break_required,
            'current_duty_status': current_duty,
            'can_drive': available_driving > 0 and window_hours > 0 and not rest_break_required
        }
    
    def get_current_duty_status(self, driver, current_time):
        """Get current duty status for a driver"""
        try:
            current_duty = DutyStatus.objects.filter(
                driver=driver,
                start_time__lte=current_time,
                end_time__isnull=True
            ).order_by('-start_time').first()
            
            if current_duty:
                return current_duty.status
            else:
                return 'off_duty'
        except Exception as e:
            logger.error(f"Error getting current duty status: {e}")
            return 'off_duty'
    
    def calculate_14_hour_window_hours(self, driver, current_time):
        """
        Calculate remaining hours in the 14-hour driving window
        """
        # Find the start of the current 14-hour window
        window_start = self.find_window_start(driver, current_time)
        
        if not window_start:
            return self.config['MAX_DUTY_HOURS_14_WINDOW']
        
        # Calculate elapsed time
        elapsed = current_time - window_start
        elapsed_hours = elapsed.total_seconds() / 3600
        
        remaining = self.config['MAX_DUTY_HOURS_14_WINDOW'] - elapsed_hours
        return max(0, remaining)
    
    def find_window_start(self, driver, current_time):
        """
        Find the start of the current 14-hour window
        """
        # Look for the last 10+ hour off-duty period
        off_duty_periods = DutyStatus.objects.filter(
            driver=driver,
            status='off_duty',
            start_time__lte=current_time
        ).order_by('-start_time')
        
        for period in off_duty_periods:
            if period.end_time:
                # Calculate duration of off-duty period
                duration = period.end_time - period.start_time
                if duration >= timedelta(hours=self.config['MIN_OFF_DUTY_HOURS']):
                    return period.end_time
            else:
                # Current off-duty period
                duration = current_time - period.start_time
                if duration >= timedelta(hours=self.config['MIN_OFF_DUTY_HOURS']):
                    return period.end_time if period.end_time else current_time
        
        return None
    
    def calculate_driving_hours_today(self, driver, current_time):
        """Calculate total driving hours in the current 14-hour window"""
        window_start = self.find_window_start(driver, current_time)
        
        if not window_start:
            return 0
        
        driving_periods = DutyStatus.objects.filter(
            driver=driver,
            status='driving',
            start_time__gte=window_start,
            start_time__lte=current_time
        )
        
        total_hours = 0
        for period in driving_periods:
            end_time = period.end_time if period.end_time else current_time
            duration = end_time - period.start_time
            total_hours += duration.total_seconds() / 3600
        
        return total_hours
    
    def calculate_weekly_hours(self, driver, current_time):
        """Calculate total on-duty hours in the rolling 7/8 day period"""
        if driver.hos_rule_type == '70_8':
            days_back = 8
        else:
            days_back = 7
        
        start_date = current_time - timedelta(days=days_back)
        
        duty_periods = DutyStatus.objects.filter(
            driver=driver,
            start_time__gte=start_date,
            start_time__lte=current_time
        ).exclude(status='off_duty')
        
        total_hours = 0
        for period in duty_periods:
            end_time = period.end_time if period.end_time else current_time
            duration = end_time - period.start_time
            total_hours += duration.total_seconds() / 3600
        
        return total_hours
    
    def is_rest_break_required(self, driver, current_time):
        """Check if 30-minute rest break is required"""
        window_start = self.find_window_start(driver, current_time)
        
        if not window_start:
            return False
        
        # Calculate cumulative driving time since last break
        driving_periods = DutyStatus.objects.filter(
            driver=driver,
            status='driving',
            start_time__gte=window_start,
            start_time__lte=current_time
        ).order_by('start_time')
        
        cumulative_driving = 0
        last_break_time = window_start
        
        for period in driving_periods:
            # Check for breaks between periods
            if period.start_time > last_break_time:
                break_duration = period.start_time - last_break_time
                if break_duration >= timedelta(minutes=self.config['MIN_REST_BREAK_MINUTES']):
                    cumulative_driving = 0
                    last_break_time = period.end_time if period.end_time else current_time
                    continue
            
            # Add driving time
            end_time = period.end_time if period.end_time else current_time
            duration = end_time - period.start_time
            cumulative_driving += duration.total_seconds() / 3600
            
            if cumulative_driving >= self.config['REST_BREAK_AFTER_HOURS']:
                return True
            
            last_break_time = end_time
        
        return False
    
    def validate_duty_status_change(self, driver, new_status, timestamp, location, trip=None):
        """
        Validate if a duty status change is allowed
        Returns: dict with validation result and any violations
        """
        violations = []
        
        # Get current HOS status
        hos_status = self.calculate_available_driving_hours(driver, timestamp)
        
        # Check if driver can start driving
        if new_status == 'driving':
            if not hos_status['can_drive']:
                violations.append({
                    'type': 'driving_not_allowed',
                    'message': 'Driver cannot start driving due to HOS constraints',
                    'details': hos_status
                })
            
            if hos_status['rest_break_required']:
                violations.append({
                    'type': 'rest_break_required',
                    'message': '30-minute rest break required before driving',
                    'details': hos_status
                })
        
        # Check for violations
        if violations:
            for violation in violations:
                self.create_violation(driver, violation, timestamp, trip)
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'hos_status': hos_status
        }
    
    def create_violation(self, driver, violation_data, timestamp, trip=None):
        """Create a HOS violation record"""
        violation_type_map = {
            'driving_not_allowed': 'driving_limit',
            'rest_break_required': 'rest_break',
            'weekly_limit_exceeded': 'weekly_limit'
        }
        
        HOSViolation.objects.create(
            driver=driver,
            trip=trip,
            violation_type=violation_type_map.get(violation_data['type'], 'driving_limit'),
            violation_time=timestamp,
            description=violation_data['message']
        )
    
    def calculate_rolling_8_day_total(self, driver, target_date):
        """Calculate rolling 8-day total for 70-hour rule"""
        start_date = target_date - timedelta(days=8)
        
        duty_periods = DutyStatus.objects.filter(
            driver=driver,
            start_time__gte=start_date,
            start_time__lt=target_date + timedelta(days=1)
        ).exclude(status='off_duty')
        
        total_hours = 0
        for period in duty_periods:
            end_time = period.end_time if period.end_time else target_date
            duration = end_time - period.start_time
            total_hours += duration.total_seconds() / 3600
        
        return total_hours
    
    def calculate_rolling_7_day_total(self, driver, target_date):
        """Calculate rolling 7-day total for 60-hour rule"""
        start_date = target_date - timedelta(days=7)
        
        duty_periods = DutyStatus.objects.filter(
            driver=driver,
            start_time__gte=start_date,
            start_time__lt=target_date + timedelta(days=1)
        ).exclude(status='off_duty')
        
        total_hours = 0
        for period in duty_periods:
            end_time = period.end_time if period.end_time else target_date
            duration = end_time - period.start_time
            total_hours += duration.total_seconds() / 3600
        
        return total_hours
    
    def generate_daily_log_data(self, driver, log_date):
        """Generate data for daily log sheet"""
        start_of_day = timezone.make_aware(datetime.combine(log_date, datetime.min.time()))
        end_of_day = start_of_day + timedelta(days=1)
        
        # Get all duty statuses for the day
        duty_statuses = DutyStatus.objects.filter(
            driver=driver,
            start_time__gte=start_of_day,
            start_time__lt=end_of_day
        ).order_by('start_time')
        
        # Calculate totals
        totals = {
            'off_duty': 0,
            'sleeper_berth': 0,
            'driving': 0,
            'on_duty_not_driving': 0
        }
        
        for status in duty_statuses:
            end_time = status.end_time if status.end_time else end_of_day
            duration = end_time - status.start_time
            hours = duration.total_seconds() / 3600
            
            if status.status in totals:
                totals[status.status] += hours
        
        # Calculate weekly totals
        if driver.hos_rule_type == '70_8':
            weekly_hours = self.calculate_rolling_8_day_total(driver, log_date)
            max_weekly = self.config['MAX_DAILY_HOURS_70_8_DAY']
        else:
            weekly_hours = self.calculate_rolling_7_day_total(driver, log_date)
            max_weekly = self.config['MAX_DAILY_HOURS_60_7_DAY']
        
        return {
            'duty_statuses': duty_statuses,
            'totals': totals,
            'weekly_hours': weekly_hours,
            'max_weekly': max_weekly,
            'hours_available_tomorrow': max(0, max_weekly - weekly_hours)
        }
