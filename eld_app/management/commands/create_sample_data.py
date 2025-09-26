"""
Django management command to create sample data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from eld_app.models import Driver, Trip, DutyStatus, DailyLog
from datetime import datetime, timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create sample user and driver
        user, created = User.objects.get_or_create(
            username='testdriver',
            defaults={
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
        
        driver, created = Driver.objects.get_or_create(
            user=user,
            defaults={
                'driver_id': 'DRV001',
                'home_terminal_address': '123 Main St, Richmond, VA 23219',
                'carrier_name': 'John Doe Transportation',
                'carrier_address': '123 Main St, Richmond, VA 23219',
                'current_cycle_hours': 0.00,
                'hos_rule_type': '70_8'
            }
        )
        
        if created:
            self.stdout.write(f'Created driver: {driver.driver_id}')
        
        # Create sample trip
        trip, created = Trip.objects.get_or_create(
            driver=driver,
            origin_address='Richmond, VA',
            destination_address='Newark, NJ',
            defaults={
                'origin_coordinates': '37.5407,-77.4360',
                'destination_coordinates': '40.7357,-74.1724',
                'planned_start_time': timezone.now() + timedelta(hours=1),
                'status': 'planned'
            }
        )
        
        if created:
            self.stdout.write(f'Created trip: {trip.id}')
        
        # Create sample duty statuses
        now = timezone.now()
        
        # Off duty from midnight to 6 AM
        DutyStatus.objects.get_or_create(
            driver=driver,
            status='off_duty',
            start_time=now.replace(hour=0, minute=0, second=0, microsecond=0),
            defaults={
                'end_time': now.replace(hour=6, minute=0, second=0, microsecond=0),
                'location': 'Home Terminal',
                'remarks': 'Off duty rest period'
            }
        )
        
        # On duty (not driving) from 6 AM to 7:30 AM
        DutyStatus.objects.get_or_create(
            driver=driver,
            status='on_duty_not_driving',
            start_time=now.replace(hour=6, minute=0, second=0, microsecond=0),
            defaults={
                'end_time': now.replace(hour=7, minute=30, second=0, microsecond=0),
                'location': 'Richmond, VA',
                'remarks': 'Pre-trip inspection and loading'
            }
        )
        
        # Driving from 7:30 AM to 9:00 AM
        DutyStatus.objects.get_or_create(
            driver=driver,
            status='driving',
            start_time=now.replace(hour=7, minute=30, second=0, microsecond=0),
            defaults={
                'end_time': now.replace(hour=9, minute=0, second=0, microsecond=0),
                'location': 'Richmond, VA to Fredericksburg, VA',
                'remarks': 'Driving segment 1'
            }
        )
        
        # Create sample daily log
        today = now.date()
        daily_log, created = DailyLog.objects.get_or_create(
            driver=driver,
            log_date=today,
            defaults={
                'total_miles_driven': 350.0,
                'vehicle_numbers': '123, 20544',
                'origin_location': 'Richmond, VA',
                'destination_location': 'Newark, NJ',
                'shipping_documents': '101601',
                'off_duty_hours': 10.0,
                'sleeper_berth_hours': 1.75,
                'driving_hours': 7.75,
                'on_duty_not_driving_hours': 4.5,
                'total_hours_last_7_days': 45.0,
                'total_hours_last_5_days': 35.0,
                'hours_available_tomorrow': 25.0
            }
        )
        
        if created:
            self.stdout.write(f'Created daily log for {today}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )
