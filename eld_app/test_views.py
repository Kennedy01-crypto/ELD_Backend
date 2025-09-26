from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def test_ui(request):
    """Serve the test UI for backend functionality testing"""
    return render(request, 'test_ui.html')


@csrf_exempt
@require_http_methods(["GET"])
def api_status(request):
    """API status endpoint for testing connectivity"""
    return HttpResponse(
        '{"status": "online", "message": "ELD Backend API is running"}',
        content_type='application/json'
    )
