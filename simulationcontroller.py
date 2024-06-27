import traci
import time
from model import Train, TrainOperation
from schedulecontroller import ScheduleController

warning_counter = 0


class SimulationController(object):

    def __init__(self, interlocking):
        self.interlocking = interlocking
        self.trains = []
        self.finished_trains = []

    def add_train(self, train_name, operations, type="regio", max_speed=70):
        train = Train(train_name)
        train.type = type
        train.max_speed = max_speed

        for i in range(5, len(operations), 6):
            train_operation = TrainOperation()
            train_operation.from_station = self.interlocking.stations[operations[i-5]]
            train_operation.from_platform = int(operations[i-4])
            train_operation.to_station = self.interlocking.stations[operations[i-3]]
            train_operation.to_platform = int(operations[i-2])
            train_operation.set_departure(operations[i-1])
            train_operation.set_arrival(operations[i])
            train.operations.append(train_operation)

        self.trains.append(train)

    def load_schedule(self, schedule_file_name):
        schedule_controller = ScheduleController()
        schedule_controller.load_schedule(schedule_file_name, self.interlocking.stations)
        self.trains.extend(schedule_controller.trains)

    def run_simulation(self):  # run the simulation until all trains are fully
        self.enrich_train_operations_by_routes()
        traci.simulationStep()
        self.after_each_simulation_step()
        while len(self.trains) > 0:
            traci.simulationStep()
            self.after_each_simulation_step()
            time.sleep(traci.simulation.getDeltaT())

    def enrich_train_operations_by_routes(self):
        for train in self.trains:
            for operation in train.operations:
                routes_tuples = operation.from_station.get_routes_tuples(operation.from_platform, operation.to_station,
                                                                         operation.to_platform)
                if routes_tuples is None:
                    print(f"Route from {operation.from_station.name} platform {operation.from_platform} to",
                          f"{operation.to_station.name} platform {operation.to_platform} not found")
                    break  # TODO: Train cannot start
                route_tuple = routes_tuples[0]  # TODO: Support multiple routes between stations
                start_signal = route_tuple[0]
                end_signal = route_tuple[1]
                found = False
                for route in self.interlocking.routes:
                    if route.start_signal.id == start_signal and route.end_signal.id == end_signal:
                        found = True
                        operation.route = route
                        break
                if not found:
                    print(f"No route from {start_signal} to {end_signal} found.")

    def after_each_simulation_step(self):
        global warning_counter
        cur_time = int(traci.simulation.getTime())

        # Update train positions
        to_remove = []
        for train in self.trains:
            if train.in_simulation:
                old_position = train.current_position
                if train.name not in traci.vehicle.getIDList():
                    if old_position != "undefined":
                        self.interlocking.train_detection_controller.count_out(old_position)
                    if len(train.operations) > 0:
                        train.operations[-1].actual_arrival = cur_time
                    to_remove.append(train)
                else:
                    new_position = traci.vehicle.getRoadID(train.name)
                    if new_position.startswith(":"):  # Point internal edges will be ignored
                        continue
                    if new_position.endswith("-re"):
                        new_position = new_position[:-3]
                    if old_position != "undefined" and new_position != old_position:
                        self.interlocking.train_detection_controller.count_out(old_position)
                        self.interlocking.train_detection_controller.count_in(new_position)
                        train.current_position = new_position
                    elif old_position == "undefined":
                        self.interlocking.train_detection_controller.count_in(new_position)
                        train.current_position = new_position

        # Remove trains that disappear
        for remove_train in to_remove:
            print(f"Remove train because disappear {remove_train.name}")
            self.remove_train_from_simulation(remove_train)

        # Update train routes
        for train in self.trains:
            if train.in_simulation and train.has_more_operations():
                if train.current_position == train.current_route.get_last_segment_of_route():
                    current_operation = train.get_current_operation()
                    next_operation = train.get_next_operation()
                    traci.vehicle.setRouteID(train.name, next_operation.route.id)

                    # Arrived
                    if traci.vehicle.getSpeed(train.name) == 0 and not current_operation.arrived:
                        current_operation.arrived = True
                        current_operation.actual_arrival = cur_time
                        next_operation.planned_departure = max(next_operation.departure,
                                                               current_operation.actual_arrival +
                                                               train.min_time_in_station)
                        self.interlocking.free_route(train.current_route)

                    # Start again
                    if current_operation.arrived and cur_time >= next_operation.planned_departure:
                        route_free = self.interlocking.can_route_be_set(next_operation.route)
                        if not route_free:
                            print(f"Route {next_operation.route.to_string()} is currently (partially) blocked."
                                  f" {train.name} has to wait")
                        else:
                            print(f"Train {train.name} continuous on route {next_operation.route.to_string()}")
                            next_operation.actual_departure = cur_time
                            self.interlocking.set_route(next_operation.route, train)
                            train.current_route = next_operation.route
                            train.processed_operation()

        # Create new trains, that come up
        for train in self.trains:
            if not train.in_simulation:
                first_operation = train.get_current_operation()
                if cur_time >= first_operation.departure:  # It's time to depart
                    route_free = self.interlocking.can_route_be_set(first_operation.route)
                    if not route_free:
                        if warning_counter % 30 == 0:
                            print(f"Route {first_operation.route.to_string()} currently (partially) blocked."
                                  f" {train.name} has to wait.")
                        warning_counter = warning_counter + 1
                    else:
                        print(f"Create train {train.name} on route {first_operation.route.to_string()}")
                        self.interlocking.set_route(first_operation.route, train)
                        train.current_route = first_operation.route
                        first_operation.actual_departure = cur_time
                        train.current_position = "undefined"
                        train.in_simulation = True
                        traci.vehicle.add(train.name, train.current_route.id, train.type)

    def remove_train_from_simulation(self, train):
        print(f"Remove train {train.name}")
        self.interlocking.free_route(train.current_route)
        self.finished_trains.append(train)
        self.trains.remove(train)

    def print_schedule_evaluation(self):
        print("Schedule Evaluation")
        for train in self.finished_trains:
            print(f"Train: {train.name}")
            print(f"Operations: {len(train.operations)}")
            for i in range(0, len(train.operations)):
                op = train.operations[i]
                print(f"Operation: {i + 1}")
                print(f"From {op.from_station.name} {op.from_platform} to {op.to_station.name} {op.to_platform}")
                print(f"Departure from schedule: {op.timestamp_to_hstring(op.departure)}, "
                      f"actual departure: {op.timestamp_to_hstring(op.actual_departure)}")
                departure_delay = op.actual_departure - op.departure
                if departure_delay > 0:
                    print(f"Departed {departure_delay} seconds late")
                elif departure_delay == 0:
                    print(f"Departed perfect on time")
                elif departure_delay < 0:
                    print(f"Departed {int(abs(departure_delay))} seconds early")

                print(f"Arrival from schedule: {op.timestamp_to_hstring(op.arrival)}, "
                      f"actual arrival: {op.timestamp_to_hstring(op.actual_arrival)}")
                arrival_delay = op.actual_arrival - op.arrival
                if arrival_delay > 0:
                    print(f"Arrived {arrival_delay} seconds late")
                elif arrival_delay == 0:
                    print(f"Arrived perfect on time")
                elif arrival_delay < 0:
                    print(f"Arrived {int(abs(arrival_delay))} seconds early")
            print("-----")
