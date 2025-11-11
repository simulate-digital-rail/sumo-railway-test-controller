import asyncio
from re import I
from typing import Dict, List
from xxlimited import new
import traci
import time
from model import Train, TrainOperation, Station, Route
from schedulecontroller import ScheduleController
from interlocking.interlockinginterface import Interlocking
from interlocking.model import OccupancyState
from interlocking.model.helper import Settings, InterlockingOperation, InterlockingOperationType
from interlocking.infrastructureprovider import LoggingInfrastructureProvider, SUMOInfrastructureProvider, RandomWaitInfrastructureProvider

import logging

# Module-level logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SimulationController(object):

    def __init__(self, stations: Dict[str, Station], routes: List[Route], interlocking: Interlocking, operations_queue: asyncio.Queue, sumo_infrastructure_provider: SUMOInfrastructureProvider):
        self.operations_queue = operations_queue
        self.interlocking = interlocking
        self.routes = routes
        self.stations: Dict[str, Station] = stations
        self.trains: List[Train] = []
        self.sumo_infrastructure_provider = sumo_infrastructure_provider
        self.finished_trains: List[Train] = []

    def add_train(self, train_name, operations, train_type="regio", max_speed=70):
        train = Train(train_name)
        train.train_type = train_type
        train.max_speed = max_speed

        for i in range(5, len(operations), 6):
            train_operation = TrainOperation()
            train_operation.from_station = self.stations[operations[i-5]]
            train_operation.from_platform = int(operations[i-4])
            train_operation.to_station = self.stations[operations[i-3]]
            train_operation.to_platform = int(operations[i-2])
            train_operation.set_departure(operations[i-1])
            train_operation.set_arrival(operations[i])
            train.operations.append(train_operation)

        self.trains.append(train)

    def load_schedule(self, schedule_file_name):
        schedule_controller = ScheduleController()
        logger.info(f"Loading schedule from {schedule_file_name}")
        schedule_controller.load_schedule(schedule_file_name, self.stations)
        logger.info(f"Add {len(schedule_controller.trains)} trains from schedule to simulation")
        for train in schedule_controller.trains:
            logger.info(f"Train {train.name} with {len(train.operations)} operations")
        self.trains.extend(schedule_controller.trains)

    async def enqueue_operation(self, operation):
        self.operations_queue.put_nowait(operation)
        await self.operations_queue.join()

    async def run_simulation(self):  # run the simulation until all trains are fully processed
        self.enrich_routes_by_last_segment()
        self.enrich_train_operations_by_routes()
        traci.simulationStep()
        await self.after_each_simulation_step()
        while len(self.trains) > 0:
            #logger.debug(f"Current simulation time: {traci.simulation.getTime()}")
            traci.simulationStep()
            await self.after_each_simulation_step()
            await asyncio.sleep(traci.simulation.getDeltaT())

    def enrich_routes_by_last_segment(self):
        for route in self.routes:
            interlocking_route = self.interlocking.get_route_from_yaramo_route(route.yaramo_route)
            route.last_segment_of_route = interlocking_route.get_last_segment_of_route().segment_id

    def enrich_train_operations_by_routes(self):
        for train in self.trains:
            for operation in train.operations:
                routes = operation.from_station.get_routes(operation.from_platform, operation.to_station,
                                                                         operation.to_platform)
                if routes is None:
                    logger.error(f"Route from {operation.from_station.name} platform {operation.from_platform} to {operation.to_station.name} platform {operation.to_platform} not found")
                    break  # TODO: Train cannot start
                logger.debug(f"Found {len(routes)} routes from {operation.from_station.name} platform {operation.from_platform} to {operation.to_station.name} platform {operation.to_platform}")
                operation.routes = routes

    def get_sumo_route_id(self, route: Route) -> str:
        return f"route_{route.identifier.replace('->', '-')}"

    async def after_each_simulation_step(self):
        cur_time = int(traci.simulation.getTime())

        # Update train positions
        to_remove = []
        for train in self.trains:
            if train.in_simulation:
                old_position = train.current_position
                if train.name not in traci.vehicle.getIDList():
                    if old_position != "undefined":
                        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.TDS_COUNT_OUT,
                                                                                train.name,
                                                                                segment_id=old_position,
                                                                                infrastructure_provider=self.sumo_infrastructure_provider))
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
                        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.TDS_COUNT_OUT,
                                                                                train.name,
                                                                                segment_id=old_position,
                                                                                infrastructure_provider=self.sumo_infrastructure_provider))
                        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.TDS_COUNT_IN,
                                                                                train.name,
                                                                                segment_id=new_position,
                                                                                infrastructure_provider=self.sumo_infrastructure_provider))
                        train.current_position = new_position
                    elif old_position == "undefined":
                        # Reserve segment before first signal
                        segment = self.interlocking.train_detection_controller.get_segment_by_segment_id(new_position)
                        segment.used_by.add(train.name)
                        segment.state = OccupancyState.RESERVED

                        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.TDS_COUNT_IN,
                                                                                train.name,
                                                                                segment_id=new_position,
                                                                                infrastructure_provider=self.sumo_infrastructure_provider))
                        train.current_position = new_position

        # Remove trains that disappear
        for remove_train in to_remove:
            await self.remove_train_from_simulation(remove_train)

        # Update train routes
        for train in self.trains:
            logger.debug(f"Train {train.name} in simulation: {train.in_simulation}, has more operations: {train.has_more_operations()}")
            if train.in_simulation:
                logger.debug(f"Train {train.name} current position: {train.current_position}, last segment of route: {train.current_route.last_segment_of_route}")
                logger.debug(f"Train {train.name} stops {traci.vehicle.getStops(train.name)}")
                if train.current_position == train.current_route.last_segment_of_route:
                    current_operation = train.get_current_operation()
                    if current_operation.has_next_route():
                        # Not at the end of the operation, just continue with the next route
                        next_route = current_operation.get_next_route()
                        route_free = self.interlocking.can_route_be_set(next_route.yaramo_route, train.name)
                        if not route_free:
                            logger.info(f"Route {next_route.identifier} is currently (partially) blocked."
                                f" {train.name} has to wait")
                        else:
                            await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.SET_ROUTE,
                                                                                            train.name,
                                                                                            yaramo_route=next_route.yaramo_route))
                            traci.vehicle.setRouteID(train.name, self.get_sumo_route_id(next_route))
                            await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.FREE_ROUTE,
                                                                                            train.name,
                                                                                            yaramo_route=train.current_route.yaramo_route))
                            train.current_route = next_route
                            current_operation.current_route_counter += 1
                            continue
                    else:
                        # When the train reached the end of the last operation, SUMO will remove it automatically (handled above)
                        if train.has_more_operations():
                            next_operation = train.get_next_operation()
                            traci.vehicle.setRouteID(train.name, self.get_sumo_route_id(next_operation.get_current_route()))
                            # Arrived
                            if traci.vehicle.getSpeed(train.name) == 0 and not current_operation.arrived:
                                current_operation.arrived = True
                                current_operation.actual_arrival = cur_time
                                next_operation.planned_departure = max(int(next_operation.departure),
                                                                    current_operation.actual_arrival +
                                                                    train.min_time_in_station)
                                logger.debug(f"Train {train.name} start again at {next_operation.planned_departure}")
                            # Start again
                            if current_operation.arrived and cur_time >= next_operation.planned_departure:
                                route_free = self.interlocking.can_route_be_set(next_operation.get_current_route().yaramo_route, train.name)
                                if not route_free:
                                    logger.info(f"Route {next_operation.get_current_route().identifier} is currently (partially) blocked."
                                        f" {train.name} has to wait")
                                else:
                                    logger.info(f"Train {train.name} continuous on route {next_operation.get_current_route().identifier}")
                                    next_operation.actual_departure = cur_time
                                    await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.SET_ROUTE,
                                                                                            train.name,
                                                                                            yaramo_route=next_operation.get_current_route().yaramo_route))
                                    await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.FREE_ROUTE,
                                                                                        train.name,
                                                                                        yaramo_route=train.current_route.yaramo_route))
                                    train.current_route = next_operation.get_current_route()
                                    train.processed_operation()
                            else:
                                logger.info(f"Train {train.name} waiting in station at {train.current_position}")

        # Create new trains, that come up
        for train in self.trains:
            if not train.in_simulation:
                first_operation = train.get_current_operation()
                if cur_time >= first_operation.departure:  # It's time to depart
                    route_free = self.interlocking.can_route_be_set(first_operation.get_current_route().yaramo_route, train.name)
                    if not route_free:
                        logger.info(f"Route {first_operation.get_current_route().identifier} currently (partially) blocked."
                              f" {train.name} has to wait.")
                    else:
                        logger.info(f"Create train {train.name} on route {first_operation.get_current_route().identifier}")
                        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.SET_ROUTE,
                                                                                train.name,
                                                                                yaramo_route=first_operation.get_current_route().yaramo_route))
                        train.current_route = first_operation.get_current_route()
                        first_operation.actual_departure = cur_time
                        train.current_position = "undefined"
                        train.in_simulation = True
                        traci.vehicle.add(train.name, self.get_sumo_route_id(train.current_route), train.train_type)
                else:
                    logger.debug(f"Train {train.name} scheduled to depart at "
                          f"{first_operation.timestamp_to_hstring(first_operation.departure)}, current time is "
                          f"{first_operation.timestamp_to_hstring(cur_time)}")

    async def remove_train_from_simulation(self, train):
        logger.info(f"Remove train {train.name}")
        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.FREE_ROUTE,
                                                                train.name,
                                                                yaramo_route=train.current_route.yaramo_route))
        self.finished_trains.append(train)
        self.trains.remove(train)

    def print_schedule_evaluation(self):
        logger.info("Schedule Evaluation")
        for train in self.finished_trains:
            logger.info(f"Train: {train.name}")
            logger.info(f"Operations: {len(train.operations)}")
            for i in range(0, len(train.operations)):
                op = train.operations[i]
                logger.info(f"Operation: {i + 1}")
                logger.info(f"From {op.from_station.name} {op.from_platform} to {op.to_station.name} {op.to_platform}")
                logger.info(f"Departure from schedule: {op.timestamp_to_hstring(op.departure)}, "
                      f"actual departure: {op.timestamp_to_hstring(op.actual_departure)}")
                departure_delay = op.actual_departure - op.departure
                if departure_delay > 0:
                    logger.info(f"Departed {departure_delay} seconds late")
                elif departure_delay == 0:
                    logger.info(f"Departed perfect on time")
                elif departure_delay < 0:
                    logger.info(f"Departed {int(abs(departure_delay))} seconds early")
                    
                logger.info(f"Arrival from schedule: {op.timestamp_to_hstring(op.arrival)}, "
                      f"actual arrival: {op.timestamp_to_hstring(op.actual_arrival)}")
                arrival_delay = op.actual_arrival - op.arrival
                if arrival_delay > 0:
                    logger.info(f"Arrived {arrival_delay} seconds late")
                elif arrival_delay == 0:
                    logger.info(f"Arrived perfect on time")
                elif arrival_delay < 0:
                    logger.info(f"Arrived {int(abs(arrival_delay))} seconds early")
            logger.info("-----")
