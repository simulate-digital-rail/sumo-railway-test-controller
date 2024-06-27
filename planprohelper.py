import planpromodel
from model import Signal, Route
from railwayroutegenerator import generator
import uuid

x_shift = 4533770.0
y_shift = 5625780.0


class PlanProHelper(object):

    def __init__(self, plan_pro_file_name):
        self.plan_pro_file_name = plan_pro_file_name
        self.root_object = planpromodel.parse(plan_pro_file_name + ".ppxml", silence=True)

    def get_number_of_fachdaten(self):
        return len(self.root_object.LST_Planung.Fachdaten.Ausgabe_Fachdaten)

    def get_container_by_fachdaten_id(self, fachdaten_id):
        return self.root_object.LST_Planung.Fachdaten.Ausgabe_Fachdaten[fachdaten_id].LST_Zustand_Ziel.Container

    def get_all_signals(self):
        all_signals = []
        for i in range(0, self.get_number_of_fachdaten()):
            container = self.get_container_by_fachdaten_id(i)
            signals = container.Signal
            for signal in signals:
                if signal.Signal_Real is None or signal.Signal_Real.Signal_Real_Aktiv is None or \
                   (signal.Signal_Real.Signal_Real_Aktiv.Signal_Funktion.Wert != "Einfahr_Signal" and
                    signal.Signal_Real.Signal_Real_Aktiv.Signal_Funktion.Wert != "Ausfahr_Signal" and
                    signal.Signal_Real.Signal_Real_Aktiv.Signal_Funktion.Wert != "Block_Signal"):
                    continue  # take only Einfahr and Ausfahr signals
                sig_id = signal.Bezeichnung.Bezeichnung_Tabelle.Wert
                punkt_obj = signal.Punkt_Objekt_TOP_Kante[0]
                top_kante_uuid = punkt_obj.ID_TOP_Kante.Wert
                signal_obj = Signal(top_kante_uuid, signal.Identitaet.Wert, sig_id)
                signal_obj.kind = signal.Signal_Real.Signal_Real_Aktiv.Signal_Funktion.Wert
                signal_obj.wirkrichtung = punkt_obj.Wirkrichtung.Wert
                signal_obj.abstand = float(punkt_obj.Abstand.Wert)
                all_signals.append(signal_obj)
        return all_signals

    def get_all_routes(self, signals=None, generate_routes=True):
        if signals is None:
            signals = self.get_all_signals()

        def find_signal_by_uuid(_signal_uuid):
            for _signal in signals:
                if _signal.signal_uuid == _signal_uuid:
                    return _signal
            return None

        all_routes = []

        if generate_routes:
            print("Start generation")
            routes = generator.generate_from_planpro(self.plan_pro_file_name, output_format="python-objects")
            print("End generation")
            for route in routes:
                start_signal = find_signal_by_uuid(route.start_signal.uuid)
                end_signal = find_signal_by_uuid(route.end_signal.uuid)
                if start_signal is None or end_signal is None:
                    continue
                if start_signal.id == "99R" and end_signal.id == "99Q":
                    continue

                top_kanten_uuids = []
                for edge in route.edges:
                    top_kanten_uuids.append(edge.uuid)

                route_uuid = f"generated-route_{str(uuid.uuid4())}"
                route_id = f"route_{start_signal.id.upper()}-{end_signal.id.upper()}"
                route_obj = Route(route_uuid, route_id)
                route_obj.start_signal = start_signal
                route_obj.end_signal = end_signal
                route_obj.top_kanten_uuids = top_kanten_uuids
                all_routes.append(route_obj)
        else:
            for i in range(0, self.get_number_of_fachdaten()):
                container = self.get_container_by_fachdaten_id(i)
                routes = container.Fstr_Fahrweg
                for route in routes:
                    start_signal_uuid = route.ID_Start.Wert
                    end_signal_uuid = route.ID_Ziel.Wert
                    start_signal = find_signal_by_uuid(start_signal_uuid)
                    end_signal = find_signal_by_uuid(end_signal_uuid)
                    if start_signal is None or end_signal is None:
                        continue

                    top_kanten_uuids = []
                    for teilbereich in route.Bereich_Objekt_Teilbereich:
                        top_kanten_uuids.append(teilbereich.ID_TOP_Kante.Wert)

                    route_uuid = route.Identitaet.Wert
                    route_id = f"route_{start_signal.id.upper()}-{end_signal.id.upper()}"
                    route_obj = Route(route_uuid, route_id)
                    route_obj.start_signal = start_signal
                    route_obj.end_signal = end_signal
                    route_obj.top_kanten_uuids = top_kanten_uuids
                    all_routes.append(route_obj)
        return all_routes

    def get_all_top_knoten(self):
        all_top_knoten = []
        for i in range(0, self.get_number_of_fachdaten()):
            container = self.get_container_by_fachdaten_id(i)
            for top_knoten in container.TOP_Knoten:
                all_top_knoten.append(top_knoten)
        return all_top_knoten

    def get_all_top_kanten(self):
        all_top_kanten = []
        for i in range(0, self.get_number_of_fachdaten()):
            container = self.get_container_by_fachdaten_id(i)
            for top_kante in container.TOP_Kante:
                all_top_kanten.append(top_kante)
        return all_top_kanten
