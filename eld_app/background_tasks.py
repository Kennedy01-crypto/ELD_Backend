"""
Background Task Service - Django Built-in Alternative to Celery
Uses threading and Django signals for background processing
"""
import threading
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Trip, RouteSegment, FuelStop, DailyLog, Driver, HOSViolation
from .map_service import OpenStreetMapService, RouteOptimizer
from .hos_engine import HOSEngine
from .pdf_generator import DailyLogPDFGenerator, MultiDayLogPDFGenerator

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """Service for running background tasks using Django's built-in threading"""
    
    def __init__(self):
        self.enabled = getattr(settings, 'BACKGROUND_TASKS_ENABLED', True)
    
    def run_async(self, func, *args, **kwargs):
        """Run a function asynchronously in a separate thread"""
        if not self.enabled:
            # Run synchronously if background tasks are disabled
            return func(*args, **kwargs)
        
        def wrapper():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background task error: {e}")
        
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread
    
    def calculate_route_async(self, trip_id):
        """Calculate route for a trip asynchronously"""
        return self.run_async(self._calculate_route_task, trip_id)
    
    def generate_pdf_async(self, daily_log_id):
        """Generate PDF for daily log asynchronously"""
        return self.run_async(self._generate_daily_log_pdf_task, daily_log_id)
    
    def generate_multi_day_pdf_async(self, trip_id):
        """Generate multi-day PDF for trip asynchronously"""
        return self.run_async(self._generate_multi_day_log_pdf_task, trip_id)
    
    def update_hos_status_async(self, driver_id):
        """Update HOS status for driver asynchronously"""
        return self.run_async(self._update_hos_status_task, driver_id)
    
    def check_violations_async(self):
        """Check for HOS violations asynchronously"""
        return self.run_async(self._check_hos_violations_task)
    
    def _calculate_route_task(self, trip_id):
        """Calculate route for a trip"""
        try:
            trip = Trip.objects.get(id=trip_id)
            logger.info(f"Starting route calculation for trip {trip_id}")
            
            # Initialize services
            map_service = OpenStreetMapService()
            hos_engine = HOSEngine()
            
            # Get HOS status for driver
            hos_status = hos_engine.calculate_available_driving_hours(trip.driver)
            
            # Parse coordinates
            origin_lat, origin_lng = trip.origin_coordinates.split(',')
            dest_lat, dest_lng = trip.destination_coordinates.split(',')
            
            origin = (float(origin_lat), float(origin_lng))
            destination = (float(dest_lat), float(dest_lng))
            
            # Calculate route
            route_data = map_service.calculate_route_with_stops(origin, destination)
            
            if not route_data:
                logger.error(f"Could not calculate route for trip {trip_id}")
                return {'status': 'error', 'message': 'Could not calculate route'}
            
            # Update trip with route data
            trip.total_distance_miles = route_data['distance_meters'] / 1609.34  # Convert to miles
            trip.estimated_duration_hours = route_data['duration_seconds'] / 3600  # Convert to hours
            trip.save()
            
            # Create route segments
            self._create_route_segments(trip, route_data, hos_status)
            
            # Create fuel stops
            self._create_fuel_stops(trip, route_data)
            
            logger.info(f"Route calculation completed for trip {trip_id}")
            return {'status': 'success', 'message': 'Route calculated successfully'}
            
        except Trip.DoesNotExist:
            logger.error(f"Trip {trip_id} not found")
            return {'status': 'error', 'message': 'Trip not found'}
        except Exception as e:
            logger.error(f"Error calculating route for trip {trip_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _create_route_segments(self, trip, route_data, hos_status):
        """Create route segments from route data"""
        segments = []
        current_time = trip.planned_start_time
        
        # Add pickup segment
        pickup_segment = RouteSegment.objects.create(
            trip=trip,
            segment_type='pickup',
            start_location=trip.origin_address,
            end_location=trip.origin_address,
            start_coordinates=trip.origin_coordinates,
            end_coordinates=trip.origin_coordinates,
            distance_miles=0,
            duration_hours=1,  # 1 hour for pickup
            planned_start_time=current_time,
            planned_end_time=current_time + timedelta(hours=1),
            sequence_order=1,
            remarks='Pickup time'
        )
        segments.append(pickup_segment)
        current_time += timedelta(hours=1)
        
        # Add driving segments
        if 'waypoints' in route_data and route_data['waypoints']:
            for i, waypoint in enumerate(route_data['waypoints']):
                if i == 0:
                    start_location = trip.origin_address
                    start_coords = trip.origin_coordinates
                else:
                    prev_waypoint = route_data['waypoints'][i-1]
                    start_location = prev_waypoint.get('instruction', 'Waypoint')
                    start_coords = f"{prev_waypoint['location'][0]},{prev_waypoint['location'][1]}"
                
                end_location = waypoint.get('instruction', 'Waypoint')
                end_coords = f"{waypoint['location'][0]},{waypoint['location'][1]}"
                
                distance_miles = waypoint.get('distance', 0) / 1609.34
                duration_hours = waypoint.get('duration', 0) / 3600
                
                driving_segment = RouteSegment.objects.create(
                    trip=trip,
                    segment_type='driving',
                    start_location=start_location,
                    end_location=end_location,
                    start_coordinates=start_coords,
                    end_coordinates=end_coords,
                    distance_miles=distance_miles,
                    duration_hours=duration_hours,
                    planned_start_time=current_time,
                    planned_end_time=current_time + timedelta(hours=duration_hours),
                    sequence_order=len(segments) + 1,
                    remarks='Driving segment'
                )
                segments.append(driving_segment)
                current_time += timedelta(hours=duration_hours)
                
                # Check if rest break is needed
                if hos_status.get('rest_break_required', False) and i > 0:
                    rest_segment = RouteSegment.objects.create(
                        trip=trip,
                        segment_type='rest_break',
                        start_location=end_location,
                        end_location=end_location,
                        start_coordinates=end_coords,
                        end_coordinates=end_coords,
                        distance_miles=0,
                        duration_hours=0.5,  # 30 minutes
                        planned_start_time=current_time,
                        planned_end_time=current_time + timedelta(minutes=30),
                        sequence_order=len(segments) + 1,
                        remarks='Required 30-minute rest break'
                    )
                    segments.append(rest_segment)
                    current_time += timedelta(minutes=30)
        
        # Add dropoff segment
        dropoff_segment = RouteSegment.objects.create(
            trip=trip,
            segment_type='dropoff',
            start_location=trip.destination_address,
            end_location=trip.destination_address,
            start_coordinates=trip.destination_coordinates,
            end_coordinates=trip.destination_coordinates,
            distance_miles=0,
            duration_hours=1,  # 1 hour for dropoff
            planned_start_time=current_time,
            planned_end_time=current_time + timedelta(hours=1),
            sequence_order=len(segments) + 1,
            remarks='Dropoff time'
        )
        segments.append(dropoff_segment)
    
    def _create_fuel_stops(self, trip, route_data):
        """Create fuel stops from route data"""
        if 'fuel_stops' in route_data:
            for i, fuel_stop in enumerate(route_data['fuel_stops']):
                FuelStop.objects.create(
                    trip=trip,
                    location=fuel_stop['location'],
                    coordinates=f"{fuel_stop['location'][0]},{fuel_stop['location'][1]}",
                    planned_time=trip.planned_start_time + timedelta(hours=fuel_stop['estimated_time']),
                    sequence_order=i + 1,
                    remarks=f"Fuel stop {i + 1}"
                )
    
    def _generate_daily_log_pdf_task(self, daily_log_id):
        """Generate PDF for daily log"""
        try:
            daily_log = DailyLog.objects.get(id=daily_log_id)
            logger.info(f"Generating PDF for daily log {daily_log_id}")
            
            # Get duty statuses for the day
            start_of_day = datetime.combine(daily_log.log_date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            
            duty_statuses = DutyStatus.objects.filter(
                driver=daily_log.driver,
                start_time__gte=start_of_day,
                start_time__lt=end_of_day
            ).order_by('start_time')
            
            # Generate PDF
            pdf_generator = DailyLogPDFGenerator()
            pdf_content = pdf_generator.generate_daily_log_pdf(daily_log, duty_statuses)
            
            # Save PDF to file (in production, save to cloud storage)
            filename = f"daily_log_{daily_log.driver.driver_id}_{daily_log.log_date.strftime('%Y%m%d')}.pdf"
            file_path = f"media/daily_logs/{filename}"
            
            import os
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(pdf_content)
            
            logger.info(f"PDF generated successfully for daily log {daily_log_id}")
            return {'status': 'success', 'file_path': file_path}
            
        except DailyLog.DoesNotExist:
            logger.error(f"Daily log {daily_log_id} not found")
            return {'status': 'error', 'message': 'Daily log not found'}
        except Exception as e:
            logger.error(f"Error generating PDF for daily log {daily_log_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _generate_multi_day_log_pdf_task(self, trip_id):
        """Generate multi-day log PDF for trip"""
        try:
            trip = Trip.objects.get(id=trip_id)
            logger.info(f"Generating multi-day PDF for trip {trip_id}")
            
            # Get all daily logs for the trip
            daily_logs = DailyLog.objects.filter(trip=trip).order_by('log_date')
            
            if not daily_logs.exists():
                logger.error(f"No daily logs found for trip {trip_id}")
                return {'status': 'error', 'message': 'No daily logs found'}
            
            # Generate multi-day PDF
            pdf_generator = MultiDayLogPDFGenerator()
            pdf_content = pdf_generator.generate_multi_day_pdf(trip, daily_logs)
            
            # Save PDF to file
            filename = f"trip_log_{trip.id}_{trip.planned_start_time.strftime('%Y%m%d')}.pdf"
            file_path = f"media/trip_logs/{filename}"
            
            import os
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(pdf_content)
            
            logger.info(f"Multi-day PDF generated successfully for trip {trip_id}")
            return {'status': 'success', 'file_path': file_path}
            
        except Trip.DoesNotExist:
            logger.error(f"Trip {trip_id} not found")
            return {'status': 'error', 'message': 'Trip not found'}
        except Exception as e:
            logger.error(f"Error generating multi-day PDF for trip {trip_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _update_hos_status_task(self, driver_id):
        """Update HOS status for driver"""
        try:
            driver = Driver.objects.get(id=driver_id)
            logger.info(f"Updating HOS status for driver {driver_id}")
            
            # Calculate current HOS status
            hos_engine = HOSEngine()
            hos_status = hos_engine.calculate_available_driving_hours(driver)
            
            # Update driver's current cycle hours
            driver.current_cycle_hours = hos_status['weekly_hours_used']
            driver.save()
            
            logger.info(f"HOS status updated for driver {driver_id}")
            return {'status': 'success', 'hos_status': hos_status}
            
        except Driver.DoesNotExist:
            logger.error(f"Driver {driver_id} not found")
            return {'status': 'error', 'message': 'Driver not found'}
        except Exception as e:
            logger.error(f"Error updating HOS status for driver {driver_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _check_hos_violations_task(self):
        """Check for HOS violations across all drivers"""
        try:
            logger.info("Checking for HOS violations")
            
            hos_engine = HOSEngine()
            violations_found = 0
            
            for driver in Driver.objects.all():
                # Check current HOS status
                hos_status = hos_engine.calculate_available_driving_hours(driver)
                
                # Check for violations
                if not hos_status['can_drive'] and hos_status['driving_hours_used'] > 0:
                    # Create violation record
                    HOSViolation.objects.create(
                        driver=driver,
                        violation_type='driving_limit',
                        violation_time=timezone.now(),
                        description='Driver exceeded driving limits'
                    )
                    violations_found += 1
            
            logger.info(f"Found {violations_found} HOS violations")
            return {'status': 'success', 'violations_found': violations_found}
            
        except Exception as e:
            logger.error(f"Error checking HOS violations: {e}")
            return {'status': 'error', 'message': str(e)}


# Global instance
background_tasks = BackgroundTaskService()
