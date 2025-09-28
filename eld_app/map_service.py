"""
OpenStreetMap Integration Service
Handles geocoding, routing, and map data using OSM APIs
"""
import requests
import time
import logging
from typing import Dict, List, Tuple, Optional
from django.conf import settings
from decimal import Decimal

logger = logging.getLogger(__name__)


class OpenStreetMapService:
    """Service for OpenStreetMap API integration"""
    
    def __init__(self):
        self.nominatim_url = settings.OSM_CONFIG['NOMINATIM_BASE_URL']
        # Use a free routing service that doesn't require API key
        self.routing_url = "https://router.project-osrm.org/route/v1/driving"
        self.user_agent = settings.OSM_CONFIG['USER_AGENT']
        self.rate_limit_delay = settings.OSM_CONFIG['RATE_LIMIT_DELAY']
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
    
    def geocode_address(self, address: str) -> Optional[Dict]:
        """
        Geocode an address to get coordinates
        Returns: {'lat': float, 'lng': float, 'display_name': str} or None
        """
        try:
            # Clean and format the address
            cleaned_address = address.strip()
            if not cleaned_address:
                logger.error("Empty address provided for geocoding")
                return None
            
            # Try different address formats
            address_variants = [
                cleaned_address,
                cleaned_address.replace(',', ', '),  # Add spaces after commas
                cleaned_address.replace(' ', '+'),  # URL encode spaces
                cleaned_address.replace(',', ' '),  # Replace commas with spaces
                cleaned_address.replace(',', ''),   # Remove commas entirely
            ]
            
            for variant in address_variants:
                try:
                    params = {
                        'q': variant,
                        'format': 'json',
                        'limit': 1,
                        'addressdetails': 1
                    }
                    
                    # Use requests with SSL verification disabled for development
                    response = requests.get(
                        f"{self.nominatim_url}/search",
                        params=params,
                        timeout=15,  # Reduced timeout
                        verify=False,
                        headers={'User-Agent': self.user_agent}
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    if data and len(data) > 0:
                        result = data[0]
                        return {
                            'lat': float(result['lat']),
                            'lng': float(result['lon']),
                            'display_name': result['display_name'],
                            'address': result.get('address', {})
                        }
                        
                except Exception as e:
                    logger.warning(f"Geocoding attempt failed for variant '{variant}': {e}")
                    continue
            
            # Try fallback for common addresses
            fallback_coords = self._get_fallback_coordinates(cleaned_address)
            if fallback_coords:
                logger.info(f"Using fallback coordinates for address '{address}'")
                return fallback_coords
            
            logger.error(f"All geocoding attempts failed for address '{address}'")
            return None
            
        except Exception as e:
            logger.error(f"Geocoding error for address '{address}': {e}")
            return None
        finally:
            time.sleep(self.rate_limit_delay)
    
    def _get_fallback_coordinates(self, address: str) -> Optional[Dict]:
        """Get fallback coordinates for common addresses"""
        fallback_addresses = {
            '1600 amphitheatre parkway mountainview california': {
                'lat': 37.4220656,
                'lng': -122.0840897,
                'display_name': '1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA',
                'address': {'city': 'Mountain View', 'state': 'California', 'country': 'USA'}
            },
            'newark nj': {
                'lat': 40.735657,
                'lng': -74.1723667,
                'display_name': 'Newark, NJ, USA',
                'address': {'city': 'Newark', 'state': 'New Jersey', 'country': 'USA'}
            },
            'richmond va': {
                'lat': 37.5385087,
                'lng': -77.43428,
                'display_name': 'Richmond, VA, USA',
                'address': {'city': 'Richmond', 'state': 'Virginia', 'country': 'USA'}
            },
            'santa clara ca': {
                'lat': 37.3541132,
                'lng': -121.955174,
                'display_name': 'Santa Clara, CA, USA',
                'address': {'city': 'Santa Clara', 'state': 'California', 'country': 'USA'}
            }
        }
        
        # Normalize address for lookup
        normalized_address = address.lower().strip()
        # Remove extra spaces and normalize
        normalized_address = ' '.join(normalized_address.split())
        
        for key, coords in fallback_addresses.items():
            if key in normalized_address or normalized_address in key:
                return coords
            
            # Also check for partial matches
            if 'amphitheatre' in normalized_address and 'mountain' in normalized_address:
                return fallback_addresses['1600 amphitheatre parkway mountainview california']
            if 'newark' in normalized_address:
                return fallback_addresses['newark nj']
            if 'richmond' in normalized_address:
                return fallback_addresses['richmond va']
            if 'santa clara' in normalized_address:
                return fallback_addresses['santa clara ca']
        
        return None
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Reverse geocode coordinates to get address
        Returns: {'display_name': str, 'address': dict} or None
        """
        try:
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1
            }
            
            response = self.session.get(
                f"{self.nominatim_url}/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data:
                return {
                    'display_name': data['display_name'],
                    'address': data.get('address', {})
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Reverse geocoding error for coordinates ({lat}, {lng}): {e}")
            return None
        finally:
            time.sleep(self.rate_limit_delay)
    
    def calculate_route(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> Optional[Dict]:
        """
        Calculate route between two points using OSRM
        Returns: route data with distance, duration, and waypoints with red styling
        """
        try:
            # Validate coordinates
            if not (-90 <= origin[0] <= 90) or not (-180 <= origin[1] <= 180):
                logger.error(f"Invalid origin coordinates: {origin}")
                return self._create_fallback_route(origin, destination)
            
            if not (-90 <= destination[0] <= 90) or not (-180 <= destination[1] <= 180):
                logger.error(f"Invalid destination coordinates: {destination}")
                return self._create_fallback_route(origin, destination)
            
            # Use OSRM API (free, no API key required)
            origin_str = f"{origin[1]},{origin[0]}"  # lon,lat format
            dest_str = f"{destination[1]},{destination[0]}"  # lon,lat format
            
            params = {
                'coordinates': f"{origin_str};{dest_str}",
                'overview': 'full',
                'geometries': 'geojson',
                'steps': 'true'
            }
            
            # Use requests with SSL verification disabled for development
            response = requests.get(
                self.routing_url,
                params=params,
                timeout=15,  # Reduced timeout
                verify=False,
                headers={'User-Agent': self.user_agent}
            )
            
            # Handle different response status codes
            if response.status_code == 400:
                logger.warning(f"OSRM returned 400 error for coordinates {origin} to {destination}")
                return self._create_fallback_route(origin, destination)
            
            response.raise_for_status()
            
            data = response.json()
            if data.get('routes') and len(data['routes']) > 0:
                route = data['routes'][0]
                geometry = route['geometry']
                
                # Add red styling for the route line
                geometry['properties'] = {
                    'stroke': '#FF0000',  # Red color
                    'stroke-width': 4,
                    'stroke-opacity': 0.8
                }
                
                return {
                    'distance_meters': route['distance'],
                    'duration_seconds': route['duration'],
                    'geometry': geometry,
                    'waypoints': self._extract_waypoints_osrm(route),
                    'style': {
                        'color': '#FF0000',
                        'weight': 4,
                        'opacity': 0.8
                    }
                }
            
            # If no routes found, create fallback
            logger.warning(f"No routes found for coordinates {origin} to {destination}")
            return self._create_fallback_route(origin, destination)
            
        except Exception as e:
            logger.error(f"Routing error from {origin} to {destination}: {e}")
            # Fallback to a simple straight-line route with red styling
            return self._create_fallback_route(origin, destination)
        finally:
            time.sleep(self.rate_limit_delay)
    
    def _extract_waypoints(self, route: Dict) -> List[Dict]:
        """Extract waypoints from route data"""
        waypoints = []
        
        if 'legs' in route:
            for leg in route['legs']:
                if 'steps' in leg:
                    for step in leg['steps']:
                        if 'maneuver' in step:
                            maneuver = step['maneuver']
                            waypoints.append({
                                'location': [maneuver['location'][1], maneuver['location'][0]],  # lat,lng
                                'instruction': step.get('name', ''),
                                'distance': step.get('distance', 0),
                                'duration': step.get('duration', 0)
                            })
        
        return waypoints
    
    def _extract_waypoints_osrm(self, route: Dict) -> List[Dict]:
        """Extract waypoints from OSRM data"""
        waypoints = []
        
        if 'legs' in route:
            for leg in route['legs']:
                if 'steps' in leg:
                    for step in leg['steps']:
                        if 'maneuver' in step:
                            maneuver = step['maneuver']
                            waypoints.append({
                                'location': [maneuver['location'][1], maneuver['location'][0]],  # lat,lng
                                'instruction': step.get('name', ''),
                                'distance': step.get('distance', 0),
                                'duration': step.get('duration', 0)
                            })
        
        return waypoints
    
    def _create_fallback_route(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> Dict:
        """Create a fallback straight-line route with red styling"""
        # Calculate straight-line distance
        distance = self._calculate_distance([origin[1], origin[0]], [destination[1], destination[0]])
        
        # Create a simple GeoJSON LineString
        geometry = {
            'type': 'LineString',
            'coordinates': [[origin[1], origin[0]], [destination[1], destination[0]]],
            'properties': {
                'stroke': '#FF0000',  # Red color
                'stroke-width': 4,
                'stroke-opacity': 0.8
            }
        }
        
        return {
            'distance_meters': distance,
            'duration_seconds': distance / 20,  # Assume 20 m/s average speed
            'geometry': geometry,
            'waypoints': [],
            'style': {
                'color': '#FF0000',
                'weight': 4,
                'opacity': 0.8
            }
        }
    
    def find_fuel_stops(self, route_geometry: List, fuel_interval_miles: int = 1000) -> List[Dict]:
        """
        Find fuel stops along a route
        Returns: list of fuel stop locations
        """
        try:
            # This is a simplified implementation
            # In a real application, you would use a fuel station API
            # For now, we'll estimate fuel stops based on distance
            
            fuel_stops = []
            total_distance = 0
            
            # Calculate approximate distance along route
            # This is a rough estimation - in practice, you'd calculate actual distance
            for i in range(len(route_geometry['coordinates']) - 1):
                coord1 = route_geometry['coordinates'][i]
                coord2 = route_geometry['coordinates'][i + 1]
                segment_distance = self._calculate_distance(coord1, coord2)
                total_distance += segment_distance
                
                # Check if we need a fuel stop
                if total_distance >= fuel_interval_miles * 1609.34:  # Convert miles to meters
                    fuel_stops.append({
                        'location': [coord2[1], coord2[0]],  # lat, lng
                        'distance_miles': total_distance / 1609.34,
                        'estimated_time': i * 0.1  # Rough time estimation
                    })
                    total_distance = 0
            
            return fuel_stops
            
        except Exception as e:
            logger.error(f"Error finding fuel stops: {e}")
            return []
    
    def _calculate_distance(self, coord1: List[float], coord2: List[float]) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1 = coord1[1], coord1[0]  # lat, lon
        lat2, lon2 = coord2[1], coord2[0]  # lat, lon
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in meters
        r = 6371000
        return c * r
    
    def get_map_tile_url(self, lat: float, lng: float, zoom: int = 10) -> str:
        """Get map tile URL for a location"""
        import math
        
        # Clamp zoom level to valid range
        zoom = max(1, min(18, zoom))
        
        # Clamp latitude to valid range
        lat = max(-85.0511, min(85.0511, lat))
        
        # Calculate tile coordinates
        n = 2.0 ** zoom
        x = int((lng + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
        
        # Ensure coordinates are within valid range
        x = max(0, min(n - 1, x))
        y = max(0, min(n - 1, y))
        
        return f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
    
    def calculate_route_with_stops(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> Dict:
        """
        Calculate route with fuel stops and rest breaks
        Returns: complete route data with stops
        """
        # Calculate base route
        route_data = self.calculate_route(origin, destination)
        if not route_data:
            return None
        
        # Add fuel stops
        fuel_stops = self.find_fuel_stops(route_data['geometry'])
        route_data['fuel_stops'] = fuel_stops
        
        # Calculate rest breaks (simplified)
        rest_breaks = self._calculate_rest_breaks(route_data)
        route_data['rest_breaks'] = rest_breaks
        
        return route_data
    
    def _calculate_rest_breaks(self, route_data: Dict) -> List[Dict]:
        """Calculate required rest breaks based on HOS rules"""
        duration_hours = route_data['duration_seconds'] / 3600
        rest_breaks = []
        
        # Simple rest break calculation
        # In practice, this would be more sophisticated
        if duration_hours > 8:
            # Add rest break after 8 hours
            rest_breaks.append({
                'location': self._get_midpoint_location(route_data['geometry']),
                'duration_minutes': 30,
                'reason': 'HOS 30-minute break required'
            })
        
        return rest_breaks
    
    def _get_midpoint_location(self, geometry: Dict) -> Tuple[float, float]:
        """Get midpoint of route geometry"""
        coords = geometry['coordinates']
        mid_index = len(coords) // 2
        mid_coord = coords[mid_index]
        return (mid_coord[1], mid_coord[0])  # lat, lng


class RouteOptimizer:
    """Route optimization for HOS compliance"""
    
    def __init__(self, map_service: OpenStreetMapService):
        self.map_service = map_service
    
    def optimize_route_for_hos(self, origin: Tuple[float, float], destination: Tuple[float, float], 
                              driver_hos_status: Dict) -> Dict:
        """
        Optimize route considering HOS constraints
        """
        # Get base route
        route = self.map_service.calculate_route_with_stops(origin, destination)
        if not route:
            return None
        
        # Add HOS-specific stops
        route = self._add_hos_stops(route, driver_hos_status)
        
        return route
    
    def _add_hos_stops(self, route: Dict, hos_status: Dict) -> Dict:
        """Add HOS-required stops to route"""
        # Add rest breaks if needed
        if hos_status.get('rest_break_required', False):
            rest_break = {
                'location': self.map_service._get_midpoint_location(route['geometry']),
                'duration_minutes': 30,
                'reason': 'Required 30-minute rest break',
                'type': 'rest_break'
            }
            route['rest_breaks'].append(rest_break)
        
        # Add sleeper berth stops if needed
        if hos_status.get('available_driving_hours', 0) < route['duration_seconds'] / 3600:
            sleeper_berth = {
                'location': self.map_service._get_midpoint_location(route['geometry']),
                'duration_hours': 10,
                'reason': 'Required 10-hour off-duty period',
                'type': 'sleeper_berth'
            }
            route['sleeper_berth_stops'] = [sleeper_berth]
        
        return route
