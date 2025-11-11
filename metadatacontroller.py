import json
import logging

from py import log
from model import Station, StationDirection, Route
from typing import Dict, List


class MetadataController(object):

    def __init__(self):
        self.stations: Dict[str, Station] = {}

    def load_metadata(self, metadata_file_name, routes: List[Route]):
        def _get_route_by_signals(start_signal, end_signal) -> Route | None:
            for route in routes:
                if route.yaramo_route.start_signal.name == start_signal and \
                   route.yaramo_route.end_signal.name == end_signal: # type: ignore
                    return route
            logging.error(f"Route from {start_signal} to {end_signal} not found in topology")
            return None

        with open(metadata_file_name, 'r') as f:
            metadata_json = json.load(f)

        stations_json = metadata_json.get("stations", {})
        for station_name, station_data in stations_json.items():
            station = Station(station_name)
            for platform_number, directions in station_data["platforms"].items():
                station.platforms[platform_number] = []
                for direction in directions:
                    station_direction = StationDirection()
                    station_direction.to_station = direction["to"]
                    station_direction.to_platform = direction["to_platform"]
                    for route in direction["routes"]:
                        found_route = _get_route_by_signals(route["start_signal"], route["end_signal"])
                        if found_route is not None:
                            station_direction.routes.append(found_route)
                    station.platforms[platform_number].append(station_direction)
            self.stations[station.name] = station

