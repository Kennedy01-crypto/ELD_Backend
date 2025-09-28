"""
URL configuration for eld_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.conf.urls.static import static

def api_root(request):
    """API root endpoint with available endpoints"""
    return JsonResponse({
        'message': 'ELD Backend API',
        'version': '1.0.0',
        'endpoints': {
            'drivers': '/api/drivers/',
            'trips': '/api/trips/',
            'daily_logs': '/api/daily-logs/',
            'violations': '/api/violations/',
            'geocode': '/api/geocode/',
            'route_calculation': '/api/route-calculation/',
            'admin': '/admin/'
        },
        'documentation': 'See README.md for API usage examples'
    })

urlpatterns = [
    path('', api_root, name='api_root'),
    path('admin/', admin.site.urls),
    path('api/', include('eld_app.urls')),
    path('test-ui/', include('eld_app.urls')),  # Add test-ui route
    path('favicon.ico', lambda request: HttpResponse(status=204), name='favicon'),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
