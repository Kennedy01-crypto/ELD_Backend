# ELD Backend - Electronic Logging Device System

A comprehensive Django REST API backend for Electronic Logging Device (ELD) systems that helps truck drivers comply with Hours of Service (HOS) regulations. This system integrates with OpenStreetMap for route planning and generates FMCSA-compliant daily log sheets.

## Features

- **HOS Compliance Engine**: Implements FMCSA Hours of Service regulations for property-carrying drivers
- **Route Planning**: Integration with OpenStreetMap for geocoding and route calculation
- **Daily Log Generation**: Automated PDF generation of FMCSA-compliant daily log sheets
- **Real-time HOS Tracking**: Monitor driver duty status and available driving hours
- **Violation Detection**: Automatic detection and logging of HOS violations
- **Multi-day Trip Support**: Handle longer trips requiring multiple daily log sheets
- **RESTful API**: Complete API for frontend integration

## HOS Regulations Implemented

- **14-Hour Driving Window**: Maximum 14 consecutive hours to drive up to 11 hours
- **11-Hour Driving Limit**: Maximum 11 total hours of driving within 14-hour window
- **30-Minute Rest Break**: Required after 8 cumulative hours of driving
- **70-Hour/8-Day Rule**: Maximum 70 hours on duty in any 8 consecutive days
- **60-Hour/7-Day Rule**: Alternative rule for carriers not operating daily
- **Sleeper Berth Provision**: Flexible rest break options for team drivers

## Technology Stack

- **Backend**: Django 4.2.7, Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production)
- **Task Queue**: Celery with Redis
- **Maps**: OpenStreetMap (Nominatim, OSRM)
- **PDF Generation**: ReportLab
- **Deployment**: Gunicorn, WhiteNoise

## Installation

### Prerequisites

- Python 3.11+
- Redis server
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ELD_Backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   DATABASE_URL=sqlite:///db.sqlite3
   REDIS_URL=redis://localhost:6379/0
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Create sample data (optional)**
   ```bash
   python manage.py create_sample_data
   ```

8. **Start Redis server**
   ```bash
   redis-server
   ```

9. **Start Celery worker (in separate terminal)**
   ```bash
   celery -A eld_backend worker --loglevel=info
   ```

10. **Start Celery beat (in separate terminal)**
    ```bash
    celery -A eld_backend beat --loglevel=info
    ```

11. **Start Django development server**
    ```bash
    python manage.py runserver
    ```

The API will be available at `http://localhost:8000/api/`

## API Endpoints

### Driver Management

- `GET /api/drivers/` - List all drivers
- `POST /api/drivers/` - Create new driver
- `GET /api/drivers/{id}/` - Get driver details
- `PUT /api/drivers/{id}/` - Update driver
- `DELETE /api/drivers/{id}/` - Delete driver
- `GET /api/drivers/{id}/hos_status/` - Get current HOS status
- `POST /api/drivers/{id}/change_duty_status/` - Change duty status
- `GET /api/drivers/{id}/daily_logs/` - Get driver's daily logs
- `GET /api/drivers/{id}/violations/` - Get HOS violations

### Trip Management

- `GET /api/trips/` - List all trips
- `POST /api/trips/create_trip/` - Create new trip with route calculation
- `GET /api/trips/{id}/` - Get trip details
- `PUT /api/trips/{id}/` - Update trip
- `DELETE /api/trips/{id}/` - Delete trip
- `POST /api/trips/{id}/calculate_route/` - Calculate route for trip
- `GET /api/trips/{id}/route_data/` - Get route data
- `GET /api/trips/{id}/daily_logs/` - Get trip's daily logs
- `POST /api/trips/{id}/start_trip/` - Start trip
- `POST /api/trips/{id}/end_trip/` - End trip

### Daily Log Management

- `GET /api/daily-logs/` - List all daily logs
- `POST /api/daily-logs/` - Create daily log
- `GET /api/daily-logs/{id}/` - Get daily log details
- `PUT /api/daily-logs/{id}/` - Update daily log
- `DELETE /api/daily-logs/{id}/` - Delete daily log
- `POST /api/daily-logs/{id}/generate_pdf/` - Generate PDF
- `POST /api/daily-logs/generate_for_date/` - Generate log for specific date

### Utility Endpoints

- `POST /api/geocode/` - Geocode address to coordinates
- `POST /api/route-calculation/` - Calculate route between points

## API Usage Examples

### 1. Create a Driver

```bash
curl -X POST http://localhost:8000/api/drivers/ \
  -H "Content-Type: application/json" \
  -d '{
    "user": 1,
    "driver_id": "DRV001",
    "home_terminal_address": "123 Main St, Richmond, VA 23219",
    "carrier_name": "John Doe Transportation",
    "carrier_address": "123 Main St, Richmond, VA 23219",
    "current_cycle_hours": 0.00,
    "hos_rule_type": "70_8"
  }'
```

### 2. Create a Trip

```bash
curl -X POST http://localhost:8000/api/trips/create_trip/ \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": 1,
    "origin_address": "Richmond, VA",
    "destination_address": "Newark, NJ",
    "planned_start_time": "2024-01-15T06:00:00Z"
  }'
```

### 3. Change Duty Status

```bash
curl -X POST http://localhost:8000/api/drivers/1/change_duty_status/ \
  -H "Content-Type: application/json" \
  -d '{
    "status": "driving",
    "location": "Richmond, VA",
    "coordinates": "37.5407,-77.4360",
    "remarks": "Starting trip"
  }'
```

### 4. Get HOS Status

```bash
curl http://localhost:8000/api/drivers/1/hos_status/
```

### 5. Generate Daily Log PDF

```bash
curl -X POST http://localhost:8000/api/daily-logs/1/generate_pdf/
```

## Data Models

### Driver
- Personal information and HOS rule type
- Current cycle hours tracking
- Carrier information

### Trip
- Origin and destination addresses
- Route planning and optimization
- Status tracking (planned, in_progress, completed)

### DutyStatus
- Real-time duty status changes
- Location and timestamp tracking
- HOS compliance validation

### DailyLog
- 24-hour duty status summary
- HOS calculations and totals
- PDF generation support

### RouteSegment
- Detailed route breakdown
- Segment types (driving, fuel stops, rest breaks)
- Timing and distance information

## HOS Compliance Features

### Real-time Validation
- Validates duty status changes against HOS rules
- Prevents violations before they occur
- Provides detailed compliance status

### Automatic Calculations
- Rolling 7/8-day hour calculations
- 14-hour driving window tracking
- Rest break requirement detection

### Violation Detection
- Automatic violation logging
- Detailed violation descriptions
- Resolution tracking

## Route Planning Features

### OpenStreetMap Integration
- Free geocoding and reverse geocoding
- Route calculation with waypoints
- Distance and duration estimation

### HOS-Aware Planning
- Considers driver's available hours
- Plans required rest breaks
- Optimizes for compliance

### Fuel Stop Planning
- Automatic fuel stop detection
- 1000-mile interval planning
- Location and timing optimization

## PDF Generation

### Daily Log Sheets
- FMCSA-compliant format
- 24-hour grid with duty status lines
- Complete HOS calculations
- Professional formatting

### Multi-day Trip Logs
- Multiple daily logs in single PDF
- Trip summary and overview
- Consistent formatting across days

## Deployment

### Production Setup

1. **Environment Variables**
   ```env
   SECRET_KEY=your-production-secret-key
   DEBUG=False
   DATABASE_URL=postgresql://user:password@host:port/dbname
   REDIS_URL=redis://host:port/0
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

2. **Database Migration**
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

3. **Start Services**
   ```bash
   gunicorn eld_backend.wsgi:application
   celery -A eld_backend worker --loglevel=info
   celery -A eld_backend beat --loglevel=info
   ```

### Heroku Deployment

1. **Install Heroku CLI**
2. **Create Heroku app**
   ```bash
   heroku create your-eld-backend
   ```

3. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set DEBUG=False
   heroku addons:create heroku-postgresql:hobby-dev
   heroku addons:create heroku-redis:hobby-dev
   ```

4. **Deploy**
   ```bash
   git push heroku main
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   ```

## Testing

### Run Tests
```bash
python manage.py test
```

### API Testing with curl
```bash
# Test driver creation
curl -X POST http://localhost:8000/api/drivers/ \
  -H "Content-Type: application/json" \
  -d '{"driver_id": "TEST001", "user": 1, ...}'

# Test trip creation
curl -X POST http://localhost:8000/api/trips/create_trip/ \
  -H "Content-Type: application/json" \
  -d '{"driver_id": 1, "origin_address": "Richmond, VA", ...}'
```

## Monitoring and Logging

### Log Files
- Application logs: `eld_backend.log`
- Celery logs: Console output
- Django logs: Console output

### Health Checks
- API health: `GET /api/`
- Database health: `GET /api/drivers/`
- Celery health: Check worker status

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Roadmap

- [ ] Real-time notifications
- [ ] Mobile app integration
- [ ] Advanced reporting
- [ ] Multi-carrier support
- [ ] Integration with ELD hardware
- [ ] Automated compliance reporting

## Changelog

### v1.0.0
- Initial release
- Core HOS compliance engine
- OpenStreetMap integration
- PDF generation
- REST API
- Celery task processing
