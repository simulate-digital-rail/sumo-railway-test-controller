class Train(object):

    def __init__(self, name):
        self.name = name
        self.type = "regio"
        self.min_time_in_station = 0
        self.max_speed = 70

        self.operations = []
        self.operation_counter = 0

        self.in_simulation = False
        self.current_position = "undefined"
        self.current_route = None

    def has_more_operations(self):
        return self.operation_counter + 1 < len(self.operations)

    def get_current_operation(self):
        return self.operations[self.operation_counter]

    def get_next_operation(self):
        return self.operations[self.operation_counter + 1]

    def processed_operation(self):
        self.operation_counter = self.operation_counter + 1

