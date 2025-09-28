@echo off
echo Starting ELD Backend Server...
echo.
echo Server will be available at:
echo   - Main API: http://127.0.0.1:8000/
echo   - Admin Test UI: http://127.0.0.1:8000/api/test-ui/
echo   - Driver UI: http://127.0.0.1:8000/api/driver-ui/
echo   - Admin Login: http://127.0.0.1:8000/api/admin-login/
echo   - Django Admin: http://127.0.0.1:8000/admin/
echo.
echo Test Credentials:
echo   Username: admin
echo   Password: admin123
echo.
C:\Users\UndefinedDataPointX\AppData\Local\Programs\Python\Python313\python.exe manage.py runserver 127.0.0.1:8000
