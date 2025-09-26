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
        self.routing_url = settings.OSM_CONFIG['ROUTING_BASE_URL']
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
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            
            response = self.session.get(
                f"{self.nominatim_url}/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data:
                result = data[0]
                return {
                    'lat': float(result['lat']),
                    'lng': float(result['lon']),
                    'display_name': result['display_name'],
                    'address': result.get('address', {})
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Geocoding error for address '{address}': {e}")
            return None
        finally:
            time.sleep(self.rate_limit_delay)
    
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
        Calculate route between two points
        Returns: route data with distance, duration, and waypoints
        """
        try:
            origin_str = f"{origin[1]},{origin[0]}"  # lon,lat format
            dest_str = f"{destination[1]},{destination[0]}"  # lon,lat format
            
            params = {
                'coordinates': f"{origin_str};{dest_str}",
                'overview': 'full',
                'geometries': 'geojson',
                'steps': 'true'
            }
            
            response = self.session.get(
                self.routing_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('routes'):
                route = data['routes'][0]
                return {
                    'distance_meters': route['distance'],
                    'duration_seconds': route['duration'],
                    'geometry': route['geometry'],
                    'legs': route['legs'] if 'legs' in route else [],
                    'waypoints': self._extract_waypoints(route)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Routing error from {origin} to {destination}: {e}")
            return None
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
        # Using OpenStreetMap tile server
        return f"https://tile.openstreetmap.org/{zoom}/{int((lng + 180) / 360 * 2**zoom)}/{int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 2**zoom)}.png"
    
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
