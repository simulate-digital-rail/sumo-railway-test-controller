class PointController(object):

    def __init__(self):
        self.points = None

    def reset(self):
        for point_id in self.points:
            self.points[point_id].orientation = "undefined"
            self.points[point_id].state = "free"

    def set_route(self, route):
        for point_information in self.get_points_of_route(route):
            point = point_information[0]
            first_track = point_information[1]
            second_track = point_information[2]
            orientation = point.get_necessary_orientation(first_track, second_track)
            if orientation == "left" or orientation == "right":
                self.turn_point(point, orientation)
                self.set_point_reserved(point)
            else:
                raise ValueError("Turn should happen but is not possible")

    def can_route_be_set(self, route):
        for point_information in self.get_points_of_route(route):
            point = point_information[0]
            if point.state != "free":
                return False
        return True

    def do_two_routes_collide(self, route_1, route_2):
        points_of_route_1 = {point_information[0] for point_information in self.get_points_of_route(route_1)}
        points_of_route_2 = {point_information[0] for point_information in self.get_points_of_route(route_2)}
        return len(points_of_route_1.intersection(points_of_route_2)) > 0

    def get_points_of_route(self, route):
        result = []
        for i in range(0, len(route.tracks_to_visit) - 1):
            first_track = route.tracks_to_visit[i]
            second_track = route.tracks_to_visit[i + 1]
            for point_id in self.points:
                point = self.points[point_id]
                if point.does_point_connect_tracks(first_track, second_track):
                    result.append((point, first_track, second_track))
        return result

    def turn_point(self, point, orientation):
        if point.orientation == orientation:
            # Everything is fine
            return
        print(f"--- Move point {point.point_id} to {orientation}")
        point.orientation = orientation

    def set_point_reserved(self, point):
        print(f"--- Set point {point.point_id} to reserved")
        point.state = "reserved"

    def set_point_free(self, point):
        print(f"--- Set point {point.point_id} to free")
        point.state = "free"

    def print_state(self):
        print("State of Points:")
        for point_id in self.points:
            point = self.points[point_id]
            print(f"{point.point_id}: {point.state} (Orientation: {point.orientation})")
