import time
import datetime

base_time = "10:00:00"


class TrainOperation(object):

    def __init__(self):
        self.from_station = None
        self.from_platform = 0
        self.to_station = None
        self.to_platform = 0
        self.departure = None
        self.departed = False
        self.planned_departure = -1
        self.actual_departure = -1
        self.arrived = False
        self.arrival = None
        self.actual_arrival = -1
        self.route = None

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
