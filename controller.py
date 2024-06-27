# Add Traci to python path, example for macOS:
#   export PYTHONPATH="/usr/local/Cellar/sumo/1.13.0_1/share/sumo/tools"

import traci
from random import choice, randint
from string import ascii_uppercase
import sys
from itertools import chain, combinations
from interlocking.interlockinginterface import Interlocking
from simulationcontroller import SimulationController
from schedulecontroller import ScheduleController
from metadatacontroller import MetadataController

host = "localhost"
port = 4444


class Controller(object):

    def __init__(self, interlocking):
        self.interlocking = interlocking
        self.simulation_controller = SimulationController(self.interlocking)

    def prepare(self):
        self.interlocking.prepare()

    def control(self):
        print("Run Simulation until all vehicles are removed to clean the simulation")
        self.reset()  # to clean the simulation
        print("Simulation Cleaned, ready to go!")
        command = None
        while command != "exit":
            command = input("#: ")
            if command == "print state":
                self.interlocking.print_state()
            elif command == "show route conflicts":
                self.show_route_conflicts()
            elif command == "run each route":
                self.run_each_route()
            elif command.startswith("train"):
                self.create_train_from_command(command)
            elif command.startswith("load schedule"):
                self.load_schedule(command)
            elif command == "print schedule evaluation":
                self.simulation_controller.print_schedule_evaluation()
            elif command == "run":
                self.simulation_controller.run_simulation()
            elif command == "reset":
                self.reset()
            elif command != "exit":
                print("Command unknown")

        print("Close TraCI connection")
        traci.close()

    def reset(self):
        self.interlocking.reset()
        for vehicle_id in traci.vehicle.getIDList():
            traci.vehicle.remove(vehicle_id)

    def run_each_route(self):
        print("Run each route")
        for route in self.interlocking.routes:
            if route.available_in_sumo:
                self.simulation_controller.create_train("train", route)
                self.simulation_controller.run_simulation()
                self.reset()

    def run_all_combinations_of_routes(self):
        print("Run all combinations of routes")

        # see https://stackoverflow.com/a/5898031
        def all_subsets(ss):
            return chain(*map(lambda x: combinations(ss, x), range(1, len(ss) + 1)))

        for subset in all_subsets(self.interlocking.routes):
            print(f"Run combination of {len(subset)} routes")
            for route in subset:
                self.simulation_controller.create_train(f"train_{route.to_string()}", route)
            self.simulation_controller.run_simulation()
            self.reset()

    def create_train_from_command(self, command):
        cmd_splits = command.split(" ")
        if len(cmd_splits) < 8:
            print("Not enough parameters for creating a train")
            return

        train_name = cmd_splits[1]
        self.simulation_controller.add_train(train_name, cmd_splits[2:])

    def load_schedule(self, command):
        self.simulation_controller.load_schedule(command.split(" ")[2])


if __name__ == "__main__":
    plan_pro_file_name = sys.argv[1]
    metadata_file_name = sys.argv[2]

    metadata_controller = MetadataController()
    metadata_controller.load_metadata(metadata_file_name)

    print("Init TraCI connection")
    traci.init(host=host, port=port)

    _interlocking = Interlocking()
    #_interlocking.stations = metadata_controller.stations

    controller = Controller(_interlocking)
    controller.prepare()
    controller.control()
