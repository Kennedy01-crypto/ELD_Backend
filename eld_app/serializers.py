"""
ELD Backend Serializers
"""
from rest_framework import serializers
from .models import Driver, Trip, DutyStatus, DailyLog, RouteSegment, FuelStop, HOSViolation


class DriverSerializer(serializers.ModelSerializer):
    """Driver serializer"""
    full_name = serializers.SerializerMethodField()
    current_hos_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Driver
        fields = [
            'id', 'driver_id', 'full_name', 'home_terminal_address',
            'carrier_name', 'carrier_address', 'current_cycle_hours',
            'hos_rule_type', 'current_hos_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    
    def get_current_hos_status(self, obj):
        from .hos_engine import HOSEngine
        hos_engine = HOSEngine()
        return hos_engine.calculate_available_driving_hours(obj)


class DriverCreateSerializer(serializers.ModelSerializer):
    """Simplified driver creation serializer for test UI"""
    name = serializers.CharField(write_only=True)
    license_number = serializers.CharField(write_only=True)
    license_state = serializers.CharField(write_only=True)
    
    class Meta:
        model = Driver
        fields = ['name', 'license_number', 'license_state']
    
    def create(self, validated_data):
        from django.contrib.auth.models import User
        
        # Create user first
        user = User.objects.create_user(
            username=validated_data['license_number'],
            first_name=validated_data['name'].split()[0] if ' ' in validated_data['name'] else validated_data['name'],
            last_name=validated_data['name'].split()[-1] if ' ' in validated_data['name'] else '',
            email=f"{validated_data['license_number']}@example.com"
        )
        
        # Create driver with default values
        driver = Driver.objects.create(
            user=user,
            driver_id=validated_data['license_number'],
            home_terminal_address="Default Terminal Address",
            carrier_name="Default Carrier",
            carrier_address="Default Carrier Address"
        )
        
        return driver


class DutyStatusSerializer(serializers.ModelSerializer):
    """Duty status serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DutyStatus
        fields = [
            'id', 'driver', 'trip', 'status', 'status_display',
            'start_time', 'end_time', 'location', 'coordinates',
            'remarks', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RouteSegmentSerializer(serializers.ModelSerializer):
    """Route segment serializer"""
    segment_type_display = serializers.CharField(source='get_segment_type_display', read_only=True)
    
    class Meta:
        model = RouteSegment
        fields = [
            'id', 'trip', 'segment_type', 'segment_type_display',
            'start_location', 'end_location', 'start_coordinates',
            'end_coordinates', 'distance_miles', 'duration_hours',
            'planned_start_time', 'planned_end_time', 'actual_start_time',
            'actual_end_time', 'sequence_order', 'remarks'
        ]
        read_only_fields = ['id']


class FuelStopSerializer(serializers.ModelSerializer):
    """Fuel stop serializer"""
    
    class Meta:
        model = FuelStop
        fields = [
            'id', 'trip', 'location', 'coordinates', 'planned_time',
            'actual_time', 'sequence_order', 'remarks'
        ]
        read_only_fields = ['id']


class TripSerializer(serializers.ModelSerializer):
    """Trip serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    driver_name = serializers.CharField(source='driver.user.get_full_name', read_only=True)
    route_segments = RouteSegmentSerializer(many=True, read_only=True)
    fuel_stops = FuelStopSerializer(many=True, read_only=True)
    hos_compliance = serializers.SerializerMethodField()
    
    class Meta:
        model = Trip
        fields = [
            'id', 'driver', 'driver_name', 'origin_address', 'origin_coordinates',
            'destination_address', 'destination_coordinates', 'status', 'status_display',
            'planned_start_time', 'actual_start_time', 'actual_end_time',
            'total_distance_miles', 'estimated_duration_hours', 'route_segments',
            'fuel_stops', 'hos_compliance', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_hos_compliance(self, obj):
        from .hos_engine import HOSEngine
        hos_engine = HOSEngine()
        return hos_engine.calculate_available_driving_hours(obj.driver)


class DailyLogSerializer(serializers.ModelSerializer):
    """Daily log serializer"""
    driver_name = serializers.CharField(source='driver.user.get_full_name', read_only=True)
    
    class Meta:
        model = DailyLog
        fields = [
            'id', 'driver', 'driver_name', 'trip', 'log_date',
            'total_miles_driven', 'vehicle_numbers', 'origin_location',
            'destination_location', 'shipping_documents', 'remarks',
            'off_duty_hours', 'sleeper_berth_hours', 'driving_hours',
            'on_duty_not_driving_hours', 'total_hours_last_7_days',
            'total_hours_last_5_days', 'hours_available_tomorrow',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HOSViolationSerializer(serializers.ModelSerializer):
    """HOS violation serializer"""
    violation_type_display = serializers.CharField(source='get_violation_type_display', read_only=True)
    driver_name = serializers.CharField(source='driver.user.get_full_name', read_only=True)
    
    class Meta:
        model = HOSViolation
        fields = [
            'id', 'driver', 'driver_name', 'trip', 'violation_type',
            'violation_type_display', 'violation_time', 'description',
            'is_resolved', 'resolved_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TripCreateSerializer(serializers.Serializer):
    """Serializer for creating trips"""
    origin_address = serializers.CharField(max_length=500)
    destination_address = serializers.CharField(max_length=500)
    planned_start_time = serializers.DateTimeField()
    
    def validate(self, data):
        # Add any custom validation here
        return data


class DutyStatusChangeSerializer(serializers.Serializer):
    """Serializer for duty status changes"""
    status = serializers.ChoiceField(choices=DutyStatus.STATUS_CHOICES)
    location = serializers.CharField(max_length=200)
    coordinates = serializers.CharField(max_length=50, required=False)
    remarks = serializers.CharField(max_length=500, required=False)
    
    def validate_coordinates(self, value):
        if value:
            try:
                lat, lng = value.split(',')
                float(lat)
                float(lng)
                return value
            except ValueError:
                raise serializers.ValidationError("Coordinates must be in format 'lat,lng'")
        return value


class RouteCalculationSerializer(serializers.Serializer):
    """Serializer for route calculation requests"""
    origin_coordinates = serializers.CharField(max_length=50)
    destination_coordinates = serializers.CharField(max_length=50)
    include_fuel_stops = serializers.BooleanField(default=True)
    include_rest_breaks = serializers.BooleanField(default=True)
    
    def validate_origin_coordinates(self, value):
        try:
            lat, lng = value.split(',')
            float(lat)
            float(lng)
            return value
        except ValueError:
            raise serializers.ValidationError("Coordinates must be in format 'lat,lng'")
    
    def validate_destination_coordinates(self, value):
        try:
            lat, lng = value.split(',')
            float(lat)
            float(lng)
            return value
        except ValueError:
            raise serializers.ValidationError("Coordinates must be in format 'lat,lng'")


class GeocodeSerializer(serializers.Serializer):
    """Serializer for geocoding requests"""
    address = serializers.CharField(max_length=500, allow_blank=False)
    
    def validate_address(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Address cannot be empty")
        return value.strip()


class SimpleRouteCalculationSerializer(serializers.Serializer):
    """Simplified route calculation serializer for UI"""
    origin = serializers.CharField(max_length=500)
    destination = serializers.CharField(max_length=500)
    
    def validate_origin(self, value):
        if not value.strip():
            raise serializers.ValidationError("Origin cannot be empty")
        return value.strip()
    
    def validate_destination(self, value):
        if not value.strip():
            raise serializers.ValidationError("Destination cannot be empty")
        return value.strip()
