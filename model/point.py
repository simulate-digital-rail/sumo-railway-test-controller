class Point(object):

    def __init__(self, top_knoten_uuid):
        self.top_knoten_uuid = top_knoten_uuid
        self.point_id = self.top_knoten_uuid[-5:]
        self.orientation = "undefined"  # either left, right or undefined
        self.state = "free"  # either free or reserved
        self.head = None
        self.left = None
        self.right = None
        self.is_point = True

    def set_track_by_anschluss(self, track, anschluss):
        if anschluss == "Spitze":
            self.head = track
        elif anschluss == "Links":
            self.left = track
        elif anschluss == "Rechts":
            self.right = track
        else:  # End
            self.head = track
            self.is_point = False

    def does_point_connect_tracks(self, track_1, track_2):
        return self.does_point_connect_top_kanten(track_1.top_kante_uuid, track_2.top_kante_uuid)

    def does_point_connect_top_kanten(self, top_kante_uuid_1, top_kante_uuid_2):
        if top_kante_uuid_1 is None or top_kante_uuid_2 is None or top_kante_uuid_1 == top_kante_uuid_2:
            return False
        if not self.is_point:
            return False
        all_uuids = []
        if self.head is not None:
            all_uuids.append(self.head.top_kante_uuid)
        if self.left is not None:
            all_uuids.append(self.left.top_kante_uuid)
        if self.right is not None:
            all_uuids.append(self.right.top_kante_uuid)
        return top_kante_uuid_1 in all_uuids and top_kante_uuid_2 in all_uuids

    def get_necessary_orientation(self, track_1, track_2):
        top_kante_uuid_1 = track_1.top_kante_uuid
        top_kante_uuid_2 = track_2.top_kante_uuid
        if top_kante_uuid_1 is None or top_kante_uuid_2 is None or top_kante_uuid_1 == top_kante_uuid_2:
            return "undefined"
        if self.head.top_kante_uuid == top_kante_uuid_1:
            if self.left.top_kante_uuid == top_kante_uuid_2:
                return "left"
            elif self.right.top_kante_uuid == top_kante_uuid_2:
                return "right"
            return "undefined"
        elif self.head.top_kante_uuid == top_kante_uuid_2:
            if self.left.top_kante_uuid == top_kante_uuid_1:
                return "left"
            elif self.right.top_kante_uuid == top_kante_uuid_1:
                return "right"
            return "undefined"
        else:
            return "undefined"  # None of the given edges is the head edge, orientation not possible

    def get_possible_successors(self, track):
        if not self.is_point:
            return []
        if self.head.top_kante_uuid == track.top_kante_uuid:
            return [self.left, self.right]
        if self.left.top_kante_uuid == track.top_kante_uuid or self.right.top_kante_uuid == track.top_kante_uuid:
            return [self.head]
        raise ValueError("Given track is no valid predecessor")
