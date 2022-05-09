import traci
from planprohelper import PlanProHelper
from interlockingcontroller import PointController, SignalController, TrackController, TrainDetectionController
from model import Point, Track


class Interlocking(object):

    def __init__(self, plan_pro_file_name):
        self.plan_pro_helper = PlanProHelper(plan_pro_file_name)
        self.point_controller = PointController()
        self.signal_controller = SignalController()
        self.track_controller = TrackController(self, self.point_controller, self.signal_controller)
        self.train_detection_controller = TrainDetectionController(self.track_controller)
        self.stations = None
        self.routes = []
        self.active_routes = []

    def prepare(self):
        signals = self.plan_pro_helper.get_all_signals()
        self.signal_controller.signals = signals

        points = dict()
        for top_knoten in self.plan_pro_helper.get_all_top_knoten():
            uuid = top_knoten.Identitaet.Wert
            point_obj = Point(uuid)
            points[point_obj.point_id] = point_obj
        self.point_controller.points = points

        tracks = dict()
        for top_kante in self.plan_pro_helper.get_all_top_kanten():
            uuid = top_kante.Identitaet.Wert
            track = Track(uuid)
            track.total_length = float(top_kante.TOP_Kante_Allg.TOP_Laenge.Wert)

            id_top_knoten_a = top_kante.ID_TOP_Knoten_A.Wert
            id_top_knoten_b = top_kante.ID_TOP_Knoten_B.Wert

            point_a = points[id_top_knoten_a[-5:]]
            point_b = points[id_top_knoten_b[-5:]]

            track.left_point = point_a
            track.right_point = point_b

            signals_of_track = []
            for signal in signals:
                if signal.top_kante_uuid == uuid:
                    signals_of_track.append(signal)
                    signal.track = track
            track.set_signals(signals_of_track)

            point_a.set_track_by_anschluss(track, top_kante.TOP_Kante_Allg.TOP_Anschluss_A.Wert)
            point_b.set_track_by_anschluss(track, top_kante.TOP_Kante_Allg.TOP_Anschluss_B.Wert)

            tracks[track.base_track_id] = track
        self.track_controller.tracks = tracks

        self.routes = self.plan_pro_helper.get_all_routes(signals)
        route_ids_in_sumo = traci.route.getIDList()
        for route in self.routes:
            for route_id_in_sumo in route_ids_in_sumo:
                if route.id == route_id_in_sumo:
                    route.available_in_sumo = True
            route.sort_tracks_to_visit(points, tracks)

    def reset(self):
        self.point_controller.reset()
        self.track_controller.reset()
        self.signal_controller.reset()
        self.active_routes = []

    def print_state(self):
        self.point_controller.print_state()
        self.track_controller.print_state()
        self.signal_controller.print_state()

        print("Active Routes:")
        for active_route in self.active_routes:
            print(active_route.to_string())

    def set_route(self, route, train):
        if not self.can_route_be_set(route):
            return False
        self.active_routes.append(route)
        self.point_controller.set_route(route)
        self.track_controller.set_route(route, train)
        self.signal_controller.set_route(route)
        return True

    def can_route_be_set(self, route):
        can_be_set = self.track_controller.can_route_be_set(route)
        can_be_set = can_be_set and self.point_controller.can_route_be_set(route)
        return can_be_set

    def do_two_routes_collide(self, route_1, route_2):
        do_collide = self.track_controller.do_two_routes_collide(route_1, route_2)
        do_collide = do_collide or self.point_controller.do_two_routes_collide(route_1, route_2)
        return do_collide

    def free_route(self, route):
        self.track_controller.free_route(route)
        self.active_routes.remove(route)
