
class Route(object):

    def __init__(self, route_uuid, id):
        self.route_uuid = route_uuid
        self.id = id
        self.start_signal = None
        self.end_signal = None
        self.top_kanten_uuids = []
        self.tracks_to_visit = []
        self.available_in_sumo = False
        self.overlap = None

    def sort_tracks_to_visit(self, points, all_tracks):
        start_track = self.start_signal.track
        self.tracks_to_visit = [start_track]
        used_top_kanten_uuids = [start_track.top_kante_uuid]
        while len(self.tracks_to_visit) < len(self.top_kanten_uuids):
            cur_track = self.tracks_to_visit[-1]
            for pot_top_kante_uuid in self.top_kanten_uuids:
                if pot_top_kante_uuid not in used_top_kanten_uuids:
                    for point_id in points:
                        point = points[point_id]
                        if point.is_point and point.does_point_connect_top_kanten(cur_track.top_kante_uuid, pot_top_kante_uuid):
                            next_track = all_tracks[pot_top_kante_uuid[-5:]]
                            self.tracks_to_visit.append(next_track)
                            used_top_kanten_uuids.append(next_track.top_kante_uuid)

    def contains_segment(self, segment_id):
        for track in self.tracks_to_visit:
            if segment_id in track.state:
                return track
        return None

    def get_driving_direction_of_track_on_route(self, track):
        if len(self.tracks_to_visit) == 0:
            raise ValueError("Route without tracks")
        if self.tracks_to_visit[0].base_track_id == track.base_track_id:
            return self.start_signal.wirkrichtung

        for i in range(1, len(self.tracks_to_visit)):
            cur_track = self.tracks_to_visit[i]

            if cur_track.base_track_id == track.base_track_id:
                prev_track = self.tracks_to_visit[i - 1]
                if cur_track.left_point.point_id == prev_track.left_point.point_id or \
                   cur_track.left_point.point_id == prev_track.right_point.point_id:
                    return "in"
                elif cur_track.right_point.point_id == prev_track.left_point.point_id or \
                     cur_track.right_point.point_id == prev_track.right_point.point_id:
                    return "gegen"
                else:
                    raise ValueError("Tracks in Route not connected by point")
        raise ValueError("Route does not contain track")

    def get_last_segment_of_route(self):
        last_track = self.tracks_to_visit[-1]
        pos_of_signal = last_track.get_position_of_signal(self.end_signal)
        if pos_of_signal == -1:
            raise ValueError("End signal not on last track")
        if self.end_signal.wirkrichtung == "in":
            return f"{last_track.base_track_id}-{pos_of_signal}"
        return f"{last_track.base_track_id}-{pos_of_signal+1}"

    def to_string(self):
        return f"{self.start_signal.id} -> { self.end_signal.id}"
