"""
Management command to create a test driver for login testing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from eld_app.models import Driver


class Command(BaseCommand):
    help = 'Create a test driver for login testing'

    def handle(self, *args, **options):
        # Create or get the test user
        user, created = User.objects.get_or_create(
            username='testdriver',
            defaults={
                'first_name': 'Test',
                'last_name': 'Driver',
                'email': 'testdriver@example.com'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS('Created test user'))
        else:
            self.stdout.write(self.style.WARNING('Test user already exists'))
        
        # Create or update the test driver
        driver, created = Driver.objects.get_or_create(
            driver_id='1',
            defaults={
                'user': user,
                'license_number': 'TEST123',
                'license_state': 'CA',
                'home_terminal_address': '123 Main St, Los Angeles, CA 90210',
                'carrier_name': 'Test Carrier Inc.',
                'carrier_address': '456 Business Ave, Los Angeles, CA 90210'
            }
        )
        
        if not created:
            # Update existing driver with license info
            driver.license_number = 'TEST123'
            driver.license_state = 'CA'
            driver.save()
            self.stdout.write(self.style.WARNING('Updated existing driver with license info'))
        else:
            self.stdout.write(self.style.SUCCESS('Created test driver'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Test driver setup complete!\n'
                f'Driver ID: {driver.driver_id}\n'
                f'License Number: {driver.license_number}\n'
                f'Name: {driver.user.get_full_name()}\n'
                f'Login credentials: Driver ID=1, License Number=TEST123'
            )
        )
