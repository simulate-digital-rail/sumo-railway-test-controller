class StationDirection(object):

    def __init__(self):
        self.to_station = None
        self.to_platform = 0
        self.routes = []  # Each route is a tuple with start and end signal
