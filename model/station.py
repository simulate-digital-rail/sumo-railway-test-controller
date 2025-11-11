from typing import Dict, List
from .route import Route

class StationDirection(object):

    def __init__(self):
        self.to_station = None
        self.to_platform = 0
        self.routes: List[Route] = []  # Each route is a tuple with start and end signal


class Station(object):

    def __init__(self, name):
        self.name = name
        self.platforms: Dict[str, List[StationDirection]] = dict()

    def get_routes(self, platform, to_station, to_platform):
        for station_direction in self.platforms[str(platform)]:
            if station_direction.to_station == to_station.name and station_direction.to_platform == to_platform:
                return station_direction.routes
        return None
