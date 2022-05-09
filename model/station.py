class Station(object):

    def __init__(self, name):
        self.name = name
        self.platforms = dict()

    def get_routes_tuples(self, platform, to_station, to_platform):
        for station_direction in self.platforms[str(platform)]:
            if station_direction.to_station == to_station.name and station_direction.to_platform == to_platform:
                return station_direction.routes
        return None
