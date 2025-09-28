"""
Management command to manually add missing database columns
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Manually add missing database columns'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                # Add license_number column if it doesn't exist
                cursor.execute("""
                    ALTER TABLE eld_app_driver 
                    ADD COLUMN license_number VARCHAR(50) NULL
                """)
                self.stdout.write(self.style.SUCCESS('Added license_number column'))
            except Exception as e:
                if 'duplicate column name' in str(e):
                    self.stdout.write(self.style.WARNING('license_number column already exists'))
                else:
                    self.stdout.write(self.style.ERROR(f'Error adding license_number: {e}'))
            
            try:
                # Add license_state column if it doesn't exist
                cursor.execute("""
                    ALTER TABLE eld_app_driver 
                    ADD COLUMN license_state VARCHAR(2) DEFAULT 'CA'
                """)
                self.stdout.write(self.style.SUCCESS('Added license_state column'))
            except Exception as e:
                if 'duplicate column name' in str(e):
                    self.stdout.write(self.style.WARNING('license_state column already exists'))
                else:
                    self.stdout.write(self.style.ERROR(f'Error adding license_state: {e}'))
        
        self.stdout.write(self.style.SUCCESS('Database fix completed!'))
