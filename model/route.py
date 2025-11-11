from yaramo.model import Route as YaramoRoute

class Route:
    def __init__(self, yaramo_route: YaramoRoute, available_in_sumo: bool):
        self.yaramo_route: YaramoRoute = yaramo_route
        self.identifier = str(yaramo_route)
        self.available_in_sumo: bool = available_in_sumo
        self.last_segment_of_route: str = "undefined"

