"""
ELD App URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import test_views

router = DefaultRouter()
router.register(r'drivers', views.DriverViewSet)
router.register(r'trips', views.TripViewSet)
router.register(r'daily-logs', views.DailyLogViewSet)
router.register(r'violations', views.HOSViolationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('geocode/', views.GeocodeView.as_view(), name='geocode'),
    path('geocode/reverse/', views.ReverseGeocodeView.as_view(), name='reverse_geocode'),
    path('route-calculation/', views.RouteCalculationView.as_view(), name='route-calculation'),
    path('map-tile/', views.MapTileView.as_view(), name='map_tile'),
    path('test-ui/', test_views.test_ui, name='test_ui'),
    path('status/', test_views.api_status, name='api_status'),
]
