# Add Traci to python path, example for macOS:
#   export PYTHONPATH="/usr/local/Cellar/sumo/1.10.0/share/sumo/tools/"

import argparse
from ast import In
import asyncio
import os
from pathlib import Path
import threading
import traci
from random import choice, randint
from string import ascii_uppercase
import sys
from itertools import chain, combinations
from simulationcontroller import SimulationController
from schedulecontroller import ScheduleController
from metadatacontroller import MetadataController
from interlocking.interlockinginterface import Interlocking
from interlocking.model.helper import Settings, InterlockingOperation, InterlockingOperationType
from interlocking.infrastructureprovider import LoggingInfrastructureProvider, SUMOInfrastructureProvider, RandomWaitInfrastructureProvider
from planpro_importer import PlanProVersion, import_planpro
from yaramo.model import Topology
from typing import Dict, List
from model import Station, Route
from sumoexporter import SUMOExporter
from railwayroutegenerator.routegenerator import RouteGenerator


import logging

# Module-level logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Controller(object):

    def __init__(self, topology: Topology, stations: Dict[str, Station], routes: List[Route] = []):
        self.topology: Topology = topology
        self.stations: Dict[str, Station] = stations
        self.routes: List[Route] = routes
        
        sumo_infrastructure_provider = SUMOInfrastructureProvider(traci_instance=traci)
        infrastructure_provider = [LoggingInfrastructureProvider(),
                                sumo_infrastructure_provider]
        self.operations_queue = asyncio.Queue()
        self.interlocking = Interlocking(infrastructure_provider, Settings(max_number_of_points_at_same_time=3))
        self.interlocking.prepare(self.topology)
        self.interlocking.print_state()
        logger.info(f"infrastructure providers: {self.interlocking.infrastructure_providers}")
        
        self.simulation_controller = SimulationController(self.stations, self.routes, self.interlocking, self.operations_queue, sumo_infrastructure_provider)

    def prepare(self):
        self.print_setup()

    def print_setup(self):
        logger.info("Found Signals:")
        for signal in self.topology.signals.values():
            logger.info("%s\t(Kind: %s; Wirkrichtung: %s; UUID: %s)", signal.name, signal.kind, signal.direction, signal.uuid)
        logger.info("Found Routes:")
        for route in self.routes:
            logger.info("%s\t(ID: %s; Available in SUMO: %s)", str(route.yaramo_route), route.yaramo_route.uuid, route.available_in_sumo)

    def show_route_conflicts(self):
        logger.info("Route conflicts:")
        interlocking = Interlocking([LoggingInfrastructureProvider()])
        interlocking.prepare(self.topology)
        for route in self.topology.routes.values():
            for route2 in self.topology.routes.values():
                if route.uuid != route2.uuid and interlocking.do_two_routes_collide(route, route2):
                    logger.warning("%s =/= %s", route, route2)

    async def start_controller(self):
        logger.info("Start Interlocking")
        async with asyncio.TaskGroup() as tg:
            logger.info("Starting Interlocking with operations queue")
            tg.create_task(self.interlocking.run_with_operations_queue(self.operations_queue))
            logger.info("Interlocking started, start control loop")
            tg.create_task(self.control())
    
    async def enqueue_operation(self, operation):
        self.operations_queue.put_nowait(operation)
        await self.operations_queue.join()

    async def control(self):
        logger.info("Run Simulation until all vehicles are removed to clean the simulation")
        await self.reset()  # to clean the simulation
        logger.info("Simulation Cleaned, ready to go!")
        command = None
        while command != "exit":
            command = input("#: ")
            if command == "print setup":
                self.print_setup()
            elif command == "print state":
                await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.PRINT_STATE))
            elif command == "show route conflicts":
                self.show_route_conflicts()
            elif command == "run each route":
                await self.run_each_route()
            elif command == "run all combinations of routes":
                self.run_all_combinations_of_routes()
            elif command.startswith("train"):
                self.create_train_from_command(command)
            elif command.startswith("load schedule"):
                self.load_schedule(command)
            elif command.startswith("ls"):
                self.load_schedule(command)
            elif command == "print schedule evaluation":
                self.simulation_controller.print_schedule_evaluation()
            elif command == "run":
                await self.simulation_controller.run_simulation()
            elif command == "reset":
                await self.reset()
            elif command != "exit":
                logger.warning("Command unknown: %s", command)
        
        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.EXIT))

        logger.info("Close TraCI connection")
        traci.close()

    async def reset(self):
        await self.enqueue_operation(InterlockingOperation(InterlockingOperationType.RESET))
        for vehicle_id in traci.vehicle.getIDList():
            traci.vehicle.remove(vehicle_id)

    async def run_each_route(self):
        # TODO: Not working atm
        logger.info("Run each route")
        for route in self.routes:
            if route.available_in_sumo:
                self.simulation_controller.create_train("train", route)
                await self.simulation_controller.run_simulation()
                await self.reset()

    def run_all_combinations_of_routes(self):
        # TODO: Not working atm
        logger.info("Run all combinations of routes")

        # see https://stackoverflow.com/a/5898031
        def all_subsets(ss):
            return chain(*map(lambda x: combinations(ss, x), range(1, len(ss) + 1)))

        for subset in all_subsets(self.routes):
            logger.info("Run combination of %d routes", len(subset))
            for route in subset:
                self.simulation_controller.create_train(f"train_{route.to_string()}", route)
            self.simulation_controller.run_simulation()
            self.reset()

    def create_train_from_command(self, command):
        cmd_splits = command.split(" ")
        if len(cmd_splits) < 8:
            logger.error("Not enough parameters for creating a train")
            return

        train_name = cmd_splits[1]
        self.simulation_controller.add_train(train_name, cmd_splits[2:])

    def load_schedule(self, command):
        if command == "ls":
            self.simulation_controller.load_schedule("test/complex-example-adv.schedule.json")
        else:
            self.simulation_controller.load_schedule(command.split(" ")[2])


def create_sumo_scenario(topology: Topology):
    sumo_exporter = SUMOExporter(topology)
    sumo_exporter.convert()
    sumo_exporter.write_output()
    logging.info("Start sumo with:")
    logging.info("")
    logging.info(f"sumo-gui -c sumo-config/{topology.name}.scenario.sumocfg --remote-port 4444 --step-length=0.1 -S")
    logging.info("or")
    logging.info(f"sumo -c sumo-config/{topology.name}.scenario.sumocfg --remote-port 4444 --step-length=0.1")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process PlanPro files")
    parser.add_argument("plan_pro_file", help="Path to the PlanPro file")
    parser.add_argument("plan_pro_version", help="Version of the PlanPro file")
    parser.add_argument("metadata_file", help="Path to the metadata file")
    parser.add_argument("--generate-routes", "-g", action="store_true", help="Generate routes from the PlanPro file")
    parser.add_argument("--traci-port", "-p", type=int, default=4444, help="Port for the TraCI connection")
    parser.add_argument("--traci-host", "-H", type=str, default="localhost", help="Host for the TraCI connection")
    args = parser.parse_args()

    plan_pro_file_name = args.plan_pro_file
    plan_pro_version_name = args.plan_pro_version
    metadata_file_name = args.metadata_file

    plan_pro_version = None
    if plan_pro_version_name == "1.10":
        plan_pro_version = PlanProVersion.PlanPro110
    elif plan_pro_version_name == "1.9":
        plan_pro_version = PlanProVersion.PlanPro19
    else:
        logger.error("PlanPro version %s not supported, use 1.9 or 1.10", plan_pro_version_name)
        sys.exit(1)

    topology: Topology | None = import_planpro(plan_pro_file_name, plan_pro_version)
    if topology is None:
        logger.error("Error importing PlanPro file")
        sys.exit(1)
    logger.info("Imported topology from PlanPro file")

    if args.generate_routes:
        RouteGenerator(topology).generate_routes()    
    for route in topology.routes.values():
        route.update_maximum_speed()

    if not Path(f"./sumo-config/{topology.name}.scenario.sumocfg").is_file():
        create_sumo_scenario(topology)

    threading.Thread(target=lambda: os.system(f"sumo-gui -c sumo-config/{topology.name}.scenario.sumocfg --remote-port 4444 --time-to-teleport 3000 --step-length=0.1 -S")).start() # type: ignore

    logger.info("Init TraCI connection")
    traci.init(host=args.traci_host, port=args.traci_port)

    routes: list[Route] = []
    sumo_routes = traci.route.getIDList()
    for yaramo_route in topology.routes.values():
        available_in_sumo = f"route_{yaramo_route.start_signal.name}-{yaramo_route.end_signal.name}" in sumo_routes # type: ignore
        route = Route(yaramo_route, available_in_sumo)
        routes.append(route)

    metadata_controller = MetadataController()
    metadata_controller.load_metadata(metadata_file_name, routes)

    controller = Controller(topology, metadata_controller.stations, routes)
    controller.prepare()
    asyncio.run(controller.start_controller())
