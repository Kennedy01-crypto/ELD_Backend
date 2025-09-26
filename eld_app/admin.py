"""
Django Admin Configuration for ELD Backend
"""
from django.contrib import admin
from .models import Driver, Trip, DutyStatus, DailyLog, RouteSegment, FuelStop, HOSViolation


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['driver_id', 'user', 'carrier_name', 'hos_rule_type', 'current_cycle_hours', 'created_at']
    list_filter = ['hos_rule_type', 'created_at']
    search_fields = ['driver_id', 'user__username', 'carrier_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['id', 'driver', 'origin_address', 'destination_address', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['driver__driver_id', 'origin_address', 'destination_address']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DutyStatus)
class DutyStatusAdmin(admin.ModelAdmin):
    list_display = ['driver', 'status', 'start_time', 'end_time', 'location']
    list_filter = ['status', 'start_time']
    search_fields = ['driver__driver_id', 'location']
    readonly_fields = ['created_at']


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ['driver', 'log_date', 'total_miles_driven', 'driving_hours', 'created_at']
    list_filter = ['log_date', 'created_at']
    search_fields = ['driver__driver_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RouteSegment)
class RouteSegmentAdmin(admin.ModelAdmin):
    list_display = ['trip', 'segment_type', 'start_location', 'end_location', 'sequence_order']
    list_filter = ['segment_type', 'trip']
    search_fields = ['trip__id', 'start_location', 'end_location']


@admin.register(FuelStop)
class FuelStopAdmin(admin.ModelAdmin):
    list_display = ['trip', 'location', 'planned_time', 'sequence_order']
    list_filter = ['trip', 'planned_time']
    search_fields = ['trip__id', 'location']


@admin.register(HOSViolation)
class HOSViolationAdmin(admin.ModelAdmin):
    list_display = ['driver', 'violation_type', 'violation_time', 'is_resolved']
    list_filter = ['violation_type', 'is_resolved', 'violation_time']
    search_fields = ['driver__driver_id', 'description']
    readonly_fields = ['created_at']
