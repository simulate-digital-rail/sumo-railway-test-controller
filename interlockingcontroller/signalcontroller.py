import traci


class SignalController(object):

    def __init__(self):
        self.signals = None

    def reset(self):
        for signal in self.signals:
            self.set_signal_halt(signal)

    def set_route(self, route):
        self.set_signal_go(route.start_signal)

    def set_signal_halt(self, signal):
        print(f"--- Set signal {signal.id} to halt")
        signal.state = "halt"
        if signal.wirkrichtung == "in":
            traci.trafficlight.setRedYellowGreenState(signal.id, "rG")
        else:
            traci.trafficlight.setRedYellowGreenState(signal.id, "Gr")

    def set_signal_go(self, signal):
        print(f"--- Set signal {signal.id} to go")
        signal.state = "go"
        traci.trafficlight.setRedYellowGreenState(signal.id, "GG")

    def print_state(self):
        print("State of Signals:")
        for signal in self.signals:
            print(f"{signal.id}: {signal.state}")
