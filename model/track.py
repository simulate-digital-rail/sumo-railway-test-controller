class Track(object):

    def __init__(self, top_kante_uuid):
        self.top_kante_uuid = top_kante_uuid
        self.base_track_id = top_kante_uuid[-5:]
        self.total_length = 0
        self.state = dict()  # Either free, reserved or occupied
        self.signals = []
        self.lengths = dict()  # Segment id to segment length
        self.left_point = None
        self.right_point = None

    def set_signals(self, signals):
        self.signals = signals
        self.signals.sort(key=lambda sig: sig.abstand, reverse=False)
        sum_of_lengths_so_far = 0
        for i in range(0, len(self.signals) + 1):
            self.state[f"{self.base_track_id}-{i}"] = "free"
            if i < len(self.signals):
                self.lengths[f"{self.base_track_id}-{i}"] = self.signals[i].abstand - sum_of_lengths_so_far
                sum_of_lengths_so_far = sum_of_lengths_so_far + self.lengths[f"{self.base_track_id}-{i}"]

        self.lengths[f"{self.base_track_id}-{len(self.signals)}"] = self.total_length - sum_of_lengths_so_far

    def get_position_of_segment(self, segment_id):
        if segment_id.endswith("-re"):
            segment_id = segment_id[:-3]
        return int(segment_id[segment_id.rfind("-") + 1:])

    def get_position_of_signal(self, signal):
        for i in range(0, len(self.signals)):
            if signal.id == self.signals[i].id:
                return i
        return -1
