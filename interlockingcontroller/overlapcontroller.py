from model import Overlap


class OverlapController(object):

    def __init__(self, interlocking, track_controller, point_controller):
        self.interlocking = interlocking
        self.track_controller = track_controller
        self.point_controller = point_controller

    def get_overlaps_of_route(self, route, train=None):
        max_speed = 70
        if train is not None:
            max_speed = train.max_speed
        missing_length_of_overlap = 0
        if max_speed <= 30:
            missing_length_of_overlap = 0
        elif max_speed <= 40:
            missing_length_of_overlap = 50
        elif max_speed <= 60:
            missing_length_of_overlap = 100
        else:
            missing_length_of_overlap = 200

        overlap_obj = Overlap(missing_length_of_overlap, route)
        if missing_length_of_overlap == 0:
            return [overlap_obj]

        last_track = route.end_signal.track
        segments_from_end_signal = self.track_controller.get_segments_from_signal(route.end_signal)

        for segment_id in segments_from_end_signal:
            overlap_obj.add_segment(last_track, segment_id)
            if overlap_obj.is_full():
                return [overlap_obj]

        # Current track is not enough
        found_overlaps = self.get_overlaps_of_route_recursive(last_track, route.end_signal.wirkrichtung, overlap_obj)
        full_overlaps = []
        longest_overlap = found_overlaps[0]
        for overlap in found_overlaps:
            if overlap.is_full():
                full_overlaps.append(overlap)
            if overlap.missing_length < longest_overlap.missing_length:
                longest_overlap = overlap
        if len(full_overlaps) > 0:
            return full_overlaps
        print("--- Warning: No full overlap found, take the longest one")
        return [longest_overlap]

    def get_overlaps_of_route_recursive(self, cur_track, cur_driving_direction, cur_overlap):
        next_point = None
        if cur_driving_direction == "in":
            next_point = cur_track.right_point
        else:
            next_point = cur_track.left_point
        cur_overlap.points.append(next_point)
        successors = next_point.get_possible_successors(cur_track)
        results = []
        for successor_track in successors:
            new_overlap = cur_overlap.duplicate()
            driving_direction = "in"
            if successor_track.right_point.point_id == next_point.point_id:
                driving_direction = "gegen"
            if driving_direction == "in":
                for segment_id in successor_track.lengths:
                    new_overlap.add_segment(successor_track, segment_id)
                    if new_overlap.is_full():
                        break
            else:
                for segment_id in reversed(successor_track.lengths):
                    new_overlap.add_segment(successor_track, segment_id)
                    if new_overlap.is_full():
                        break
            results.append(new_overlap)
            if not new_overlap.is_full():
                # Track was not long enough
                results.extend(self.get_overlaps_of_route_recursive(successor_track, driving_direction, new_overlap))
        return results

    def reserve_overlap_of_route(self, route, train):
        overlap = self.get_first_reservable_overlap(route, train)
        if overlap is None:
            raise ValueError("No reservable overlap found")
        for track_base_id in overlap.segments:
            track = self.track_controller.tracks[track_base_id]
            for segment_id in overlap.segments[track_base_id]:
                print(f"--- Set track {segment_id} reserved (overlap)")
                track.state[segment_id] = "reserved-overlap"
        for point in overlap.points:
            print(f"--- Set point {point.point_id} to reserved (overlap)")
            point.state = "reserved-overlap"

            # Get necessary orientation
            points_tracks = [point.head, point.left, point.right]
            found_tracks = []
            for track in points_tracks:
                if track.base_track_id in overlap.segments:
                    found_tracks.append(track)

            if len(found_tracks) != 2:
                raise ValueError("Overlap contains points without 2 of their tracks")
            necessery_orientation = point.get_necessary_orientation(found_tracks[0], found_tracks[1])
            if necessery_orientation == "undefined":
                raise ValueError("Not able to turn overlap point")
            self.point_controller.turn_point(point, necessery_orientation)
        route.overlap = overlap

    def free_overlap_of_route(self, route):
        overlap = route.overlap
        if overlap is None:
            raise ValueError("Overlap is None")
        for track_base_id in overlap.segments:
            track = self.track_controller.tracks[track_base_id]
            for segment_id in overlap.segments[track_base_id]:
                if not self.is_segment_used_in_any_other_overlap(segment_id, route):
                    print(f"--- Set track {segment_id} free")
                    track.state[segment_id] = "free"
        for point in overlap.points:
            if not self.is_point_used_in_any_other_overlap(point, route):
                self.point_controller.set_point_free(point)

    def get_first_reservable_overlap(self, route, train):
        all_overlaps = self.get_overlaps_of_route(route, train)
        for overlap in all_overlaps:
            if self.can_overlap_be_reserved(overlap):
                return overlap
        return None

    def can_overlap_be_reserved(self, overlap):
        for base_track_id in overlap.segments:
            track = self.track_controller.tracks[base_track_id]
            for segment_id in overlap.segments[base_track_id]:
                if track.state[segment_id] != "free" and track.state[segment_id] != "reserved-overlap":
                    return False
        for point in overlap.points:
            if point.state != "free" and point.state != "reserved-overlap":
                return False
        return True

    def is_segment_used_in_any_other_overlap(self, segment_id, route):
        for active_route in self.interlocking.active_routes:
            if active_route.id != route.id:
                overlap_of_active_route = active_route.overlap
                if overlap_of_active_route is None:
                    raise ValueError("An active route has no overlap object")
                for base_track_id in overlap_of_active_route.segments:
                    if segment_id in overlap_of_active_route.segments[base_track_id]:
                        return True
        return False

    def is_point_used_in_any_other_overlap(self, point, route):
        for active_route in self.interlocking.active_routes:
            if active_route.id != route.id:
                overlap_of_active_route = active_route.overlap
                if overlap_of_active_route is None:
                    raise ValueError("An active route has no overlap object")
                for point_of_active_route in overlap_of_active_route.points:
                    if point.point_id == point_of_active_route.point_id:
                        return True
        return False
