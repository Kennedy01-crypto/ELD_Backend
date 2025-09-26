"""
Django management command to run periodic tasks
Replaces Celery beat functionality
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import time
import logging

from eld_app.background_tasks import background_tasks

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run periodic tasks for HOS compliance checking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Interval in seconds between task runs (default: 300)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run tasks once and exit'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
        self.stdout.write(f'Starting periodic tasks with {interval}s interval...')
        
        if run_once:
            self.run_tasks()
            return
        
        try:
            while True:
                self.run_tasks()
                self.stdout.write(f'Waiting {interval} seconds before next run...')
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write('Periodic tasks stopped by user')
        except Exception as e:
            self.stdout.write(f'Error in periodic tasks: {e}')
            logger.error(f'Periodic task error: {e}')

    def run_tasks(self):
        """Run all periodic tasks"""
        self.stdout.write(f'Running periodic tasks at {timezone.now()}')
        
        # Check for HOS violations
        try:
            result = background_tasks.check_violations_async()
            if result:
                self.stdout.write(f'HOS violations check: {result}')
        except Exception as e:
            self.stdout.write(f'Error checking HOS violations: {e}')
            logger.error(f'HOS violations check error: {e}')
        
        # Update HOS status for all drivers
        try:
            from eld_app.models import Driver
            for driver in Driver.objects.all():
                background_tasks.update_hos_status_async(driver.id)
            self.stdout.write('Updated HOS status for all drivers')
        except Exception as e:
            self.stdout.write(f'Error updating HOS status: {e}')
            logger.error(f'HOS status update error: {e}')
        
        self.stdout.write('Periodic tasks completed')
