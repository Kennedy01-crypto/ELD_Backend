"""
ELD Backend API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
import logging

from .models import Driver, Trip, DutyStatus, DailyLog, RouteSegment, FuelStop, HOSViolation
from .serializers import (
    DriverSerializer, DriverCreateSerializer, TripSerializer, DutyStatusSerializer, DailyLogSerializer,
    HOSViolationSerializer, TripCreateSerializer, DutyStatusChangeSerializer,
    RouteCalculationSerializer, SimpleRouteCalculationSerializer, GeocodeSerializer
)
from .hos_engine import HOSEngine
from .map_service import OpenStreetMapService, RouteOptimizer
from .background_tasks import background_tasks

logger = logging.getLogger(__name__)


class DriverViewSet(viewsets.ModelViewSet):
    """Driver management"""
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DriverCreateSerializer
        return DriverSerializer
    
    @action(detail=True, methods=['get'])
    def hos_status(self, request, pk=None):
        """Get current HOS status for driver"""
        driver = self.get_object()
        hos_engine = HOSEngine()
        hos_status = hos_engine.calculate_available_driving_hours(driver)
        return Response(hos_status)
    
    @action(detail=True, methods=['post'])
    def change_duty_status(self, request, pk=None):
        """Change driver duty status"""
        driver = self.get_object()
        serializer = DutyStatusChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            # Validate duty status change
            hos_engine = HOSEngine()
            validation = hos_engine.validate_duty_status_change(
                driver=driver,
                new_status=serializer.validated_data['status'],
                timestamp=timezone.now(),
                location=serializer.validated_data['location']
            )
            
            if validation['valid']:
                # Create duty status record
                duty_status = DutyStatus.objects.create(
                    driver=driver,
                    status=serializer.validated_data['status'],
                    start_time=timezone.now(),
                    location=serializer.validated_data['location'],
                    coordinates=serializer.validated_data.get('coordinates'),
                    remarks=serializer.validated_data.get('remarks', '')
                )
                
                # End previous duty status if exists
                previous_duty = DutyStatus.objects.filter(
                    driver=driver,
                    end_time__isnull=True
                ).exclude(id=duty_status.id).first()
                
                if previous_duty:
                    previous_duty.end_time = timezone.now()
                    previous_duty.save()
                
                return Response({
                    'status': 'success',
                    'duty_status': DutyStatusSerializer(duty_status).data,
                    'hos_status': validation['hos_status']
                })
            else:
                return Response({
                    'status': 'error',
                    'violations': validation['violations'],
                    'hos_status': validation['hos_status']
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_duty_status(self, request, pk=None):
        """Update driver's duty status (alias for change_duty_status)"""
        return self.change_duty_status(request, pk)
    
    @action(detail=True, methods=['get'])
    def daily_logs(self, request, pk=None):
        """Get daily logs for driver"""
        driver = self.get_object()
        logs = DailyLog.objects.filter(driver=driver).order_by('-log_date')
        serializer = DailyLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def violations(self, request, pk=None):
        """Get HOS violations for driver"""
        driver = self.get_object()
        violations = HOSViolation.objects.filter(driver=driver).order_by('-violation_time')
        serializer = HOSViolationSerializer(violations, many=True)
        return Response(serializer.data)


class TripViewSet(viewsets.ModelViewSet):
    """Trip management"""
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    @action(detail=False, methods=['get', 'post'])
    def create_trip(self, request):
        """Create a new trip with route calculation"""
        if request.method == 'GET':
            return Response({
                'message': 'Create Trip Endpoint',
                'method': 'POST',
                'required_fields': {
                    'driver_id': 'integer - ID of the driver',
                    'origin_address': 'string - Starting location',
                    'destination_address': 'string - Destination location',
                    'planned_start_time': 'string - ISO datetime format'
                },
                'example': {
                    'driver_id': 1,
                    'origin_address': 'Richmond, VA',
                    'destination_address': 'Newark, NJ',
                    'planned_start_time': '2024-01-15T06:00:00Z'
                }
            })
        
        # POST method implementation
        serializer = TripCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Get driver (assuming from request or user)
            driver_id = request.data.get('driver_id')
            if not driver_id:
                return Response(
                    {'error': 'driver_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                driver = Driver.objects.get(id=driver_id)
            except Driver.DoesNotExist:
                return Response(
                    {'error': 'Driver not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Geocode addresses
            map_service = OpenStreetMapService()
            origin_geocoded = map_service.geocode_address(serializer.validated_data['origin_address'])
            dest_geocoded = map_service.geocode_address(serializer.validated_data['destination_address'])
            
            if not origin_geocoded or not dest_geocoded:
                return Response(
                    {'error': 'Could not geocode addresses'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create trip
            trip = Trip.objects.create(
                driver=driver,
                origin_address=serializer.validated_data['origin_address'],
                origin_coordinates=f"{origin_geocoded['lat']},{origin_geocoded['lng']}",
                destination_address=serializer.validated_data['destination_address'],
                destination_coordinates=f"{dest_geocoded['lat']},{dest_geocoded['lng']}",
                planned_start_time=serializer.validated_data['planned_start_time']
            )
            
            # Start route calculation task
            background_tasks.calculate_route_async(trip.id)
            
            return Response(TripSerializer(trip).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def calculate_route(self, request, pk=None):
        """Calculate route for trip"""
        trip = self.get_object()
        
        # Start route calculation task
        background_tasks.calculate_route_async(trip.id)
        
        return Response({'status': 'Route calculation started'})
    
    @action(detail=True, methods=['get'])
    def route_data(self, request, pk=None):
        """Get route data for trip"""
        trip = self.get_object()
        
        # Get route segments
        segments = RouteSegment.objects.filter(trip=trip).order_by('sequence_order')
        fuel_stops = FuelStop.objects.filter(trip=trip).order_by('sequence_order')
        
        route_data = {
            'trip_id': str(trip.id),
            'origin': {
                'address': trip.origin_address,
                'coordinates': trip.origin_coordinates
            },
            'destination': {
                'address': trip.destination_address,
                'coordinates': trip.destination_coordinates
            },
            'total_distance_miles': float(trip.total_distance_miles) if trip.total_distance_miles else None,
            'estimated_duration_hours': float(trip.estimated_duration_hours) if trip.estimated_duration_hours else None,
            'segments': [{
                'type': segment.segment_type,
                'start_location': segment.start_location,
                'end_location': segment.end_location,
                'start_coordinates': segment.start_coordinates,
                'end_coordinates': segment.end_coordinates,
                'distance_miles': float(segment.distance_miles),
                'duration_hours': float(segment.duration_hours),
                'planned_start_time': segment.planned_start_time,
                'planned_end_time': segment.planned_end_time,
                'remarks': segment.remarks
            } for segment in segments],
            'fuel_stops': [{
                'location': stop.location,
                'coordinates': stop.coordinates,
                'planned_time': stop.planned_time,
                'sequence_order': stop.sequence_order,
                'remarks': stop.remarks
            } for stop in fuel_stops]
        }
        
        return Response(route_data)
    
    @action(detail=True, methods=['get'])
    def daily_logs(self, request, pk=None):
        """Get daily logs for trip"""
        trip = self.get_object()
        logs = DailyLog.objects.filter(trip=trip).order_by('log_date')
        serializer = DailyLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_trip(self, request, pk=None):
        """Start a trip"""
        trip = self.get_object()
        
        if trip.status != 'planned':
            return Response(
                {'error': 'Trip is not in planned status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check HOS compliance
        hos_engine = HOSEngine()
        hos_status = hos_engine.calculate_available_driving_hours(trip.driver)
        
        if not hos_status['can_drive']:
            return Response(
                {'error': 'Driver cannot start trip due to HOS constraints', 'hos_status': hos_status}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update trip status
        trip.status = 'in_progress'
        trip.actual_start_time = timezone.now()
        trip.save()
        
        # Create driving duty status
        DutyStatus.objects.create(
            driver=trip.driver,
            trip=trip,
            status='driving',
            start_time=timezone.now(),
            location=trip.origin_address,
            coordinates=trip.origin_coordinates
        )
        
        return Response({'status': 'Trip started successfully'})
    
    @action(detail=True, methods=['post'])
    def end_trip(self, request, pk=None):
        """End a trip"""
        trip = self.get_object()
        
        if trip.status != 'in_progress':
            return Response(
                {'error': 'Trip is not in progress'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update trip status
        trip.status = 'completed'
        trip.actual_end_time = timezone.now()
        trip.save()
        
        # End current duty status
        current_duty = DutyStatus.objects.filter(
            driver=trip.driver,
            trip=trip,
            end_time__isnull=True
        ).first()
        
        if current_duty:
            current_duty.end_time = timezone.now()
            current_duty.save()
        
        return Response({'status': 'Trip ended successfully'})


class GeocodeView(APIView):
    """Geocoding API"""
    
    def post(self, request):
        """Geocode an address"""
        serializer = GeocodeSerializer(data=request.data)
        
        if serializer.is_valid():
            map_service = OpenStreetMapService()
            result = map_service.geocode_address(serializer.validated_data['address'])
            
            if result:
                return Response(result)
            else:
                return Response(
                    {'error': 'Could not geocode address'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RouteCalculationView(APIView):
    """Route calculation API"""
    
    def post(self, request):
        """Calculate route between two points"""
        serializer = SimpleRouteCalculationSerializer(data=request.data)
        
        if serializer.is_valid():
            map_service = OpenStreetMapService()
            
            # First geocode the addresses to get coordinates
            origin_coords = map_service.geocode_address(serializer.validated_data['origin'])
            destination_coords = map_service.geocode_address(serializer.validated_data['destination'])
            
            if not origin_coords or not destination_coords:
                return Response(
                    {'error': 'Could not geocode one or both addresses'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate route using coordinates
            origin = (float(origin_coords['lat']), float(origin_coords['lng']))
            destination = (float(destination_coords['lat']), float(destination_coords['lng']))
            
            route = map_service.calculate_route_with_stops(origin, destination)
            
            if route:
                # Add the original addresses to the result
                route['origin_address'] = serializer.validated_data['origin']
                route['destination_address'] = serializer.validated_data['destination']
                return Response(route)
            else:
                return Response(
                    {'error': 'Could not calculate route'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReverseGeocodeView(APIView):
    """Reverse geocoding API"""
    
    def post(self, request):
        """Reverse geocode coordinates to address"""
        try:
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            
            if not latitude or not longitude:
                return Response(
                    {'error': 'Latitude and longitude are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            map_service = OpenStreetMapService()
            result = map_service.reverse_geocode(float(latitude), float(longitude))
            
            if result:
                return Response(result)
            else:
                return Response(
                    {'error': 'Could not reverse geocode coordinates'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError) as e:
            return Response(
                {'error': 'Invalid coordinates'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class MapTileView(APIView):
    """Map tile API"""
    
    def get(self, request):
        """Get map tile URL for given coordinates and zoom level"""
        try:
            lat = request.GET.get('lat')
            lng = request.GET.get('lng')
            zoom = request.GET.get('zoom', 10)
            
            if not lat or not lng:
                return Response(
                    {'error': 'Latitude and longitude are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            map_service = OpenStreetMapService()
            tile_url = map_service.get_map_tile_url(float(lat), float(lng), int(zoom))
            
            return Response({
                'tile_url': tile_url,
                'coordinates': {
                    'latitude': float(lat),
                    'longitude': float(lng),
                    'zoom': int(zoom)
                }
            })
        except (ValueError, TypeError) as e:
            return Response(
                {'error': 'Invalid parameters'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class DailyLogViewSet(viewsets.ModelViewSet):
    """Daily log management"""
    queryset = DailyLog.objects.all()
    serializer_class = DailyLogSerializer
    
    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, pk=None):
        """Generate PDF for daily log"""
        daily_log = self.get_object()
        
        # Start PDF generation task
        background_tasks.generate_pdf_async(daily_log.id)
        
        return Response({'status': 'PDF generation started'})
    
    @action(detail=False, methods=['post'])
    def generate_pdf(self, request):
        """Generate PDF for daily log by driver and date"""
        driver_id = request.data.get('driver_id')
        date = request.data.get('date')
        
        if not driver_id or not date:
            return Response(
                {'error': 'driver_id and date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            driver = Driver.objects.get(id=driver_id)
            daily_log, created = DailyLog.objects.get_or_create(
                driver=driver,
                log_date=date,
                defaults={
                    'total_miles_driven': 0,
                    'off_duty_hours': 0,
                    'sleeper_berth_hours': 0,
                    'driving_hours': 0,
                    'on_duty_not_driving_hours': 0
                }
            )
            
            # Start PDF generation task
            background_tasks.generate_pdf_async(daily_log.id)
            
            return Response({
                'status': 'PDF generation started',
                'daily_log_id': daily_log.id,
                'created': created
            })
        except Driver.DoesNotExist:
            return Response(
                {'error': 'Driver not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def generate_for_date(self, request):
        """Generate daily log for specific date"""
        driver_id = request.data.get('driver_id')
        log_date = request.data.get('log_date')
        
        if not driver_id or not log_date:
            return Response(
                {'error': 'driver_id and log_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            driver = Driver.objects.get(id=driver_id)
            log_date = datetime.strptime(log_date, '%Y-%m-%d').date()
        except (Driver.DoesNotExist, ValueError):
            return Response(
                {'error': 'Invalid driver_id or log_date'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate daily log data
        hos_engine = HOSEngine()
        log_data = hos_engine.generate_daily_log_data(driver, log_date)
        
        # Create or update daily log
        daily_log, created = DailyLog.objects.get_or_create(
            driver=driver,
            log_date=log_date,
            defaults={
                'off_duty_hours': log_data['totals']['off_duty'],
                'sleeper_berth_hours': log_data['totals']['sleeper_berth'],
                'driving_hours': log_data['totals']['driving'],
                'on_duty_not_driving_hours': log_data['totals']['on_duty_not_driving'],
                'total_hours_last_7_days': log_data['weekly_hours'],
                'hours_available_tomorrow': log_data['hours_available_tomorrow']
            }
        )
        
        if not created:
            # Update existing log
            daily_log.off_duty_hours = log_data['totals']['off_duty']
            daily_log.sleeper_berth_hours = log_data['totals']['sleeper_berth']
            daily_log.driving_hours = log_data['totals']['driving']
            daily_log.on_duty_not_driving_hours = log_data['totals']['on_duty_not_driving']
            daily_log.total_hours_last_7_days = log_data['weekly_hours']
            daily_log.hours_available_tomorrow = log_data['hours_available_tomorrow']
            daily_log.save()
        
        return Response(DailyLogSerializer(daily_log).data)


class HOSViolationViewSet(viewsets.ModelViewSet):
    """HOS violation management"""
    queryset = HOSViolation.objects.all()
    serializer_class = HOSViolationSerializer
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a violation"""
        violation = self.get_object()
        violation.is_resolved = True
        violation.resolved_at = timezone.now()
        violation.save()
        
        return Response({'status': 'Violation resolved'})
