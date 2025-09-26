"""
ELD App URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'drivers', views.DriverViewSet)
router.register(r'trips', views.TripViewSet)
router.register(r'daily-logs', views.DailyLogViewSet)
router.register(r'violations', views.HOSViolationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('geocode/', views.GeocodeView.as_view(), name='geocode'),
    path('route-calculation/', views.RouteCalculationView.as_view(), name='route-calculation'),
]
