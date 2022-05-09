from .overlapcontroller import OverlapController


class TrackController(object):

    def __init__(self, interlocking, point_controller, signal_controller):
        self.tracks = []
        self.interlocking = interlocking
        self.point_controller = point_controller
        self.signal_controller = signal_controller
        self.overlap_controller = OverlapController(interlocking, self, self.point_controller)

    def reset(self):
        for base_track_id in self.tracks:
            self.free_full_track(self.tracks[base_track_id])

    def set_route(self, route, train):
        self.reserve_route(route, train)

    def can_route_be_set(self, route):
        segments = self.get_segments_of_route(route)
        # Overlaps can be used by multiple trains in Germany, so no direct check here
        for track_base_id in segments:
            track = self.tracks[track_base_id]
            for segment_id in segments[track_base_id]:
                if track.state[segment_id] != "free":
                    return False
        return True

    def do_two_routes_collide(self, route_1, route_2):
        segments_of_route_1 = {x for v in self.get_segments_of_route(route_1).values() for x in v}
        segments_of_route_2 = {x for v in self.get_segments_of_route(route_2).values() for x in v}
        if len(segments_of_route_1.intersection(segments_of_route_2)) > 0:
            return True

        overlaps_of_route_1 = self.overlap_controller.get_overlaps_of_route(route_1)
        found_no_free_overlap_route_1 = True
        for overlap in overlaps_of_route_1:
            overlap_segments_of_route_1 = {x for v in overlap.segments.values() for x in v}
            if len(overlap_segments_of_route_1.intersection(segments_of_route_2)) == 0:
                found_no_free_overlap_route_1 = False
                break
        overlaps_of_route_2 = self.overlap_controller.get_overlaps_of_route(route_2)
        found_no_free_overlap_route_2 = True
        for overlap in overlaps_of_route_2:
            overlap_segments_of_route_2 = {x for v in overlap.segments.values() for x in v}
            if len(overlap_segments_of_route_2.intersection(segments_of_route_1)) == 0:
                found_no_free_overlap_route_2 = False
                break
        return found_no_free_overlap_route_1 or found_no_free_overlap_route_2

    def free_route(self, route):
        self.overlap_controller.free_overlap_of_route(route)

    def get_segments_of_route(self, route):
        result = dict()

        if route.start_signal.track.base_track_id == route.end_signal.track.base_track_id:
            pos_start_signal = self.get_position_of_signal(route.start_signal)
            pos_end_signal = self.get_position_of_signal(route.end_signal)
            result[route.start_signal.track.base_track_id] = self.get_segments_of_range(route.start_signal.track,
                                                                                        pos_start_signal + 1,
                                                                                        pos_end_signal + 1)
        else:
            result[route.start_signal.track.base_track_id] = self.get_segments_from_signal(route.start_signal)
            for i in range(1, len(route.tracks_to_visit) - 1):
                result[route.tracks_to_visit[i].base_track_id] = self.get_segments_of_full_track(route.tracks_to_visit[i])
            result[route.end_signal.track.base_track_id] = self.get_segments_to_signal(route.end_signal)
        return result

    def get_segments_of_full_track(self, track):
        return self.get_segments_of_range(track, 0, len(track.signals)+1)

    def get_segments_from_signal(self, signal):
        pos_in_track = self.get_position_of_signal(signal)
        if signal.wirkrichtung == "in":
            return self.get_segments_of_range(signal.track, pos_in_track + 1, len(signal.track.signals) + 1)
        else:
            return self.get_segments_of_range(signal.track, 0, pos_in_track + 1)

    def get_segments_to_signal(self, signal):
        pos_in_track = self.get_position_of_signal(signal)
        if signal.wirkrichtung == "in":
            return self.get_segments_of_range(signal.track, 0, pos_in_track + 1)
        else:
            return self.get_segments_of_range(signal.track, pos_in_track + 1, len(signal.track.signals) + 1)

    def get_segments_of_range(self, track, from_index, to_index):
        result = []
        for i in range(from_index, to_index):
            result.append(f"{track.base_track_id}-{i}")
        return result

    def get_position_of_signal(self, signal):
        for i in range(0, len(signal.track.signals)):
            if signal.id == signal.track.signals[i].id:
                return i
        return -1

    def reserve_route(self, route, train):
        segments = self.get_segments_of_route(route)
        for track_base_id in segments:
            track = self.tracks[track_base_id]
            for segment_id in segments[track_base_id]:
                print(f"--- Set track {segment_id} reserved")
                track.state[segment_id] = "reserved"

        self.overlap_controller.reserve_overlap_of_route(route, train)

    def occupy_full_track(self, track):
        for segment_id in track.state:
            self.occupy_segment_of_track(track, segment_id)

    def occupy_segment_of_track(self, track, segment_id):
        if track.state[segment_id] != "occupied":
            print(f"--- Set track {segment_id} occupied")
            track.state[segment_id] = "occupied"

            # Set signal to halt
            pos_of_segment = track.get_position_of_segment(segment_id)
            if pos_of_segment > 0:
                previous_signal = track.signals[pos_of_segment - 1]
                if previous_signal.wirkrichtung == "in":
                    self.signal_controller.set_signal_halt(previous_signal)
            if pos_of_segment < len(track.signals):
                next_signal = track.signals[pos_of_segment]
                if next_signal.wirkrichtung == "gegen":
                    self.signal_controller.set_signal_halt(next_signal)

    def free_full_track(self, track):
        for segment_id in track.state:
            self.free_segment_of_track(track, segment_id)

    def free_segment_of_track(self, track, segment_id):
        if track.state[segment_id] != "free":
            print(f"--- Set track {segment_id} free")
            track.state[segment_id] = "free"

            # Free point
            pos_of_segment = track.get_position_of_segment(segment_id)
            if pos_of_segment == 0 or pos_of_segment == len(track.signals) + 1:
                route = None
                for active_route in self.interlocking.active_routes:
                    if active_route.contains_segment(segment_id):
                        route = active_route
                        break
                if route is None:
                    raise ValueError("Active route not found")

                driving_direction = route.get_driving_direction_of_track_on_route(track)

                if pos_of_segment == 0 and driving_direction == "in":
                    self.point_controller.set_point_free(track.left_point)
                elif pos_of_segment == len(track.signals) + 1 and driving_direction == "gegen":
                    self.point_controller.set_point_free(track.right_point)

    def print_state(self):
        print("State of Tracks:")
        for base_track_id in self.tracks:
            track = self.tracks[base_track_id]
            for segment in track.state:
                print(f"{segment}: {track.state[segment]}")
