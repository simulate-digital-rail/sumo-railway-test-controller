class Signal(object):

    def __init__(self, top_kante_uuid, signal_uuid, signal_id):
        self.top_kante_uuid = top_kante_uuid
        self.signal_uuid = signal_uuid
        self.id = signal_id
        self.state = "halt"  # Either halt or go
        self.wirkrichtung = None  # Either in or gegen
        self.kind = None
        self.track = None
        self.abstand = 0.0
