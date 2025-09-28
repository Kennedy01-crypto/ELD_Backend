"""
ELD Backend Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class Driver(models.Model):
    """Driver model for HOS tracking"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    driver_id = models.CharField(max_length=50, unique=True)
    license_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    license_state = models.CharField(max_length=2, default='CA')
    home_terminal_address = models.TextField()
    carrier_name = models.CharField(max_length=200)
    carrier_address = models.TextField()
    current_cycle_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(70)]
    )
    hos_rule_type = models.CharField(
        max_length=10,
        choices=[('70_8', '70 hours/8 days'), ('60_7', '60 hours/7 days')],
        default='70_8'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.driver_id})"

    class Meta:
        ordering = ['-created_at']


class Trip(models.Model):
    """Trip model for tracking driver trips"""
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='trips')
    origin_address = models.TextField()
    origin_coordinates = models.CharField(max_length=50)  # "lat,lng"
    destination_address = models.TextField()
    destination_coordinates = models.CharField(max_length=50)  # "lat,lng"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    planned_start_time = models.DateTimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    total_distance_miles = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip {self.id} - {self.origin_address} to {self.destination_address}"

    class Meta:
        ordering = ['-created_at']


class DutyStatus(models.Model):
    """Duty status changes for HOS tracking"""
    STATUS_CHOICES = [
        ('off_duty', 'Off Duty'),
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty_not_driving', 'On Duty (Not Driving)'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='duty_statuses')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='duty_statuses', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200)
    coordinates = models.CharField(max_length=50, null=True, blank=True)  # "lat,lng"
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver.driver_id} - {self.get_status_display()} at {self.start_time}"

    class Meta:
        ordering = ['-start_time']


class RouteSegment(models.Model):
    """Route segments for trip planning"""
    SEGMENT_TYPES = [
        ('driving', 'Driving'),
        ('fuel_stop', 'Fuel Stop'),
        ('rest_break', 'Rest Break'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('sleeper_berth', 'Sleeper Berth'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='route_segments')
    segment_type = models.CharField(max_length=20, choices=SEGMENT_TYPES)
    start_location = models.CharField(max_length=200)
    end_location = models.CharField(max_length=200)
    start_coordinates = models.CharField(max_length=50)  # "lat,lng"
    end_coordinates = models.CharField(max_length=50)  # "lat,lng"
    distance_miles = models.DecimalField(max_digits=8, decimal_places=2)
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2)
    planned_start_time = models.DateTimeField()
    planned_end_time = models.DateTimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    sequence_order = models.PositiveIntegerField()
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.trip.id} - {self.get_segment_type_display()} ({self.sequence_order})"

    class Meta:
        ordering = ['trip', 'sequence_order']


class DailyLog(models.Model):
    """Daily log sheets for HOS compliance"""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='daily_logs')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='daily_logs', null=True, blank=True)
    log_date = models.DateField()
    total_miles_driven = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    vehicle_numbers = models.CharField(max_length=200)
    origin_location = models.CharField(max_length=200, blank=True)
    destination_location = models.CharField(max_length=200, blank=True)
    shipping_documents = models.CharField(max_length=200, blank=True)
    remarks = models.TextField(blank=True)
    
    # HOS totals for the day
    off_duty_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sleeper_berth_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    driving_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    on_duty_not_driving_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # 70-hour/8-day calculations
    total_hours_last_7_days = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    total_hours_last_5_days = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    hours_available_tomorrow = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.driver.driver_id} - {self.log_date}"

    class Meta:
        ordering = ['-log_date']
        unique_together = ['driver', 'log_date']


class FuelStop(models.Model):
    """Fuel stops along the route"""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='fuel_stops')
    location = models.CharField(max_length=200)
    coordinates = models.CharField(max_length=50)  # "lat,lng"
    planned_time = models.DateTimeField()
    actual_time = models.DateTimeField(null=True, blank=True)
    sequence_order = models.PositiveIntegerField()
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Fuel Stop {self.sequence_order} - {self.location}"

    class Meta:
        ordering = ['trip', 'sequence_order']


class HOSViolation(models.Model):
    """HOS violations tracking"""
    VIOLATION_TYPES = [
        ('driving_limit', '11-Hour Driving Limit'),
        ('duty_limit', '14-Hour Duty Limit'),
        ('weekly_limit', '70/60-Hour Weekly Limit'),
        ('rest_break', '30-Minute Rest Break'),
        ('off_duty', '10-Hour Off Duty'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='violations')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='violations', null=True, blank=True)
    violation_type = models.CharField(max_length=20, choices=VIOLATION_TYPES)
    violation_time = models.DateTimeField()
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver.driver_id} - {self.get_violation_type_display()} at {self.violation_time}"

    class Meta:
        ordering = ['-violation_time']
