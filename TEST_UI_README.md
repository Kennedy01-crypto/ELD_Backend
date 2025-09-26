# 🚛 ELD Backend Test UI

A comprehensive web interface for testing all backend functionalities of the ELD (Electronic Logging Device) system.

## 🌐 Access the Test UI

**URL:** `http://127.0.0.1:8000/api/test-ui/`

## 🎯 Features

### 1. **Driver Management** 👥
- **Get All Drivers** - Retrieve list of all registered drivers
- **Create New Driver** - Add new drivers to the system
  - Name, License Number, License State

### 2. **Trip Management** 🚛
- **Get All Trips** - View all trips in the system
- **Create New Trip** - Create trips with route calculation
  - Driver ID, Origin, Destination, Planned Start Time

### 3. **Hours of Service (HOS) Status** ⏰
- **Get HOS Status** - Check driver's current HOS compliance
- **Update Duty Status** - Change driver's duty status
  - Off Duty, Sleeper Berth, Driving, On Duty (Not Driving)

### 4. **Geocoding Services** 📍
- **Geocode Address** - Convert addresses to coordinates
- **Reverse Geocode** - Convert coordinates to addresses

### 5. **Route Calculation** 🗺️
- **Calculate Route** - Get route between two locations
- **Get Map Tile** - Retrieve map tiles for specific coordinates

### 6. **Daily Logs** 📋
- **Get Daily Logs** - View all daily logs
- **Generate PDF** - Create PDF daily log sheets

## 🚀 How to Use

1. **Start the Django server:**
   ```bash
   python manage.py runserver
   ```

2. **Open your browser and navigate to:**
   ```
   http://127.0.0.1:8000/api/test-ui/
   ```

3. **Test different functionalities:**
   - Click on different tabs to access various features
   - Fill in the forms with test data
   - Click buttons to make API calls
   - View responses in the formatted output areas

## 📊 Sample Test Data

### Create a Driver:
- **Name:** John Doe
- **License Number:** D123456789
- **License State:** VA

### Create a Trip:
- **Driver ID:** 1
- **Origin:** Richmond, VA
- **Destination:** Newark, NJ
- **Planned Start Time:** Current date/time

### Test Geocoding:
- **Address:** 1600 Amphitheatre Parkway, Mountain View, CA
- **Coordinates:** 37.4221, -122.0841

## 🔧 API Endpoints Tested

- `GET /api/drivers/` - List drivers
- `POST /api/drivers/` - Create driver
- `GET /api/drivers/{id}/hos_status/` - Get HOS status
- `POST /api/drivers/{id}/update_duty_status/` - Update duty status
- `GET /api/trips/` - List trips
- `POST /api/trips/create_trip/` - Create trip
- `POST /api/geocode/` - Geocode address
- `POST /api/geocode/reverse/` - Reverse geocode
- `POST /api/route-calculation/` - Calculate route
- `GET /api/map-tile/` - Get map tile
- `GET /api/daily-logs/` - List daily logs
- `POST /api/daily-logs/generate_pdf/` - Generate PDF

## 🎨 UI Features

- **Responsive Design** - Works on all screen sizes
- **Tabbed Interface** - Organized by functionality
- **Real-time Feedback** - Loading indicators and response display
- **Error Handling** - Clear error messages
- **Form Validation** - Input validation and formatting
- **Modern UI** - Clean, professional design

## 🛠️ Technical Details

- **Frontend:** Pure HTML, CSS, JavaScript
- **Backend:** Django REST Framework
- **API Communication:** Fetch API with JSON
- **Styling:** Modern CSS with gradients and animations
- **Responsive:** CSS Grid and Flexbox

## 📝 Notes

- All API calls are made to `http://127.0.0.1:8000/api/`
- Responses are displayed in formatted JSON
- Error responses are highlighted in red
- Success responses are highlighted in green
- Loading states are shown during API calls

This test UI provides a complete interface for testing all backend functionalities without needing a separate frontend application.
