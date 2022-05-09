import json
from model import Station, StationDirection


class MetadataController(object):

    def __init__(self):
        self.stations = dict()

    def load_metadata(self, metadata_file_name):
        metadata_json = None
        with open(metadata_file_name, 'r') as f:
            metadata_json = json.load(f)

        # Prepare stations
        stations_json = metadata_json["stations"]
        for station_name in stations_json:
            station = Station(station_name)
            platforms_dict = stations_json[station_name]["platforms"]
            for platform_number in platforms_dict:
                station.platforms[platform_number] = []
                for direction in platforms_dict[platform_number]:
                    station_direction = StationDirection()
                    station_direction.to_station = direction["to"]
                    station_direction.to_platform = direction["to_platform"]
                    for route in direction["routes"]:
                        station_direction.routes.append((route["start_signal"], route["end_signal"]))
                    station.platforms[platform_number].append(station_direction)
            self.stations[station.name] = station
