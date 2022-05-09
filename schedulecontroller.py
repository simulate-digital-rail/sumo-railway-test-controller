import traci
import json
from model import Station, StationDirection, Train, TrainOperation


class ScheduleController(object):

    def __init__(self):
        self.trains = []

    def load_schedule(self, schedule_file_name, stations):
        schedule = None
        with open(schedule_file_name, 'r') as f:
            schedule = json.load(f)

        # Prepare trains
        for train_json in schedule:
            train = Train(train_json["name"])
            train.type = train_json["type"]
            train.min_time_in_station = train_json["min_time_in_station"]
            train.max_speed = int(traci.vehicletype.getMaxSpeed(train.type)) * 3.6
            for operation_json in train_json["operations"]:
                train_operation = TrainOperation()
                train_operation.from_station = stations[operation_json["from"]]
                train_operation.from_platform = operation_json["from_platform"]
                train_operation.to_station = stations[operation_json["to"]]
                train_operation.to_platform = operation_json["to_platform"]
                train_operation.departure = operation_json["departure"]
                train_operation.arrival = operation_json["arrival"]
                train_operation.set_departure(operation_json["departure"])
                train_operation.set_arrival(operation_json["arrival"])
                train.operations.append(train_operation)
            self.trains.append(train)
