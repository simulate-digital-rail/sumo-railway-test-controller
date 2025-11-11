import time
import datetime
from typing import Optional, List
from .station import Station
from .route import Route

base_time = "10:00:00"


class TrainOperation(object):

    def __init__(self):
        self.from_station: Station | None = None
        self.from_platform = 0
        self.to_station: Station | None  = None
        self.to_platform = 0
        self.departure = -1
        self.departed = False
        self.planned_departure = -1
        self.actual_departure = -1
        self.arrived = False
        self.arrival = -1
        self.actual_arrival = -1
        self.routes: List[Route] = []
        self.current_route_counter = 0

    def has_next_route(self) -> bool:
        return self.current_route_counter + 1 < len(self.routes)
    
    def get_next_route(self) -> Route:
        return self.routes[self.current_route_counter + 1]
    
    def get_current_route(self) -> Route:
        return self.routes[self.current_route_counter]

    def set_departure(self, departure):
        self.departure = self.recalc_timestamp(departure)

    def set_arrival(self, arrival):
        self.arrival = self.recalc_timestamp(arrival)

    def recalc_timestamp(self, timestamp):
        ts = time.strptime(timestamp, '%H:%M:%S')
        ts_s = datetime.timedelta(hours=ts.tm_hour, minutes=ts.tm_min, seconds=ts.tm_sec).total_seconds()

        base_ts = time.strptime(base_time, '%H:%M:%S')
        base_s = datetime.timedelta(hours=base_ts.tm_hour, minutes=base_ts.tm_min,
                                    seconds=base_ts.tm_sec).total_seconds()

        return ts_s - base_s

    def timestamp_to_hstring(self, timestamp):
        base_ts = time.strptime(base_time, '%H:%M:%S')
        base_s = datetime.timedelta(hours=base_ts.tm_hour, minutes=base_ts.tm_min,
                                    seconds=base_ts.tm_sec).total_seconds()
        d = datetime.datetime.fromtimestamp(timestamp+base_s-3600)
        return d.strftime("%H:%M:%S")
