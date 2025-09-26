from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login
from django.middleware.csrf import get_token
from django.contrib.auth.models import User
import json


def test_ui(request):
    """Serve the test UI for backend functionality testing"""
    return render(request, 'test_ui.html')


def admin_login(request):
    """Serve the admin login UI"""
    return render(request, 'admin_login.html')


@csrf_exempt
@require_http_methods(["GET"])
def api_status(request):
    """API status endpoint for testing connectivity"""
    return HttpResponse(
        '{"status": "online", "message": "ELD Backend API is running"}',
        content_type='application/json'
    )


@require_http_methods(["GET"])
def csrf_token(request):
    """Get CSRF token for API requests"""
    csrf_token = get_token(request)
    return JsonResponse({'csrf_token': csrf_token})


@csrf_exempt
@require_http_methods(["POST"])
def admin_login_api(request):
    """Admin login API endpoint"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({'error': 'Username and password are required'}, status=400)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser or user.is_staff:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'is_superuser': user.is_superuser,
                        'is_staff': user.is_staff
                    }
                })
            else:
                return JsonResponse({'error': 'User does not have admin privileges'}, status=403)
        else:
            return JsonResponse({'error': 'Invalid username or password'}, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
