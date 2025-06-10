import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import uuid
import datetime
import copy
import requests
import time  # Only needed if website push/pull is kept and threaded
from typing import Dict, Any, Optional, List
import threading  # Keep for data_lock, even if website push/pull is simplified
import queue
import socket

HOST = '0.0.0.0'  # Lauscht auf allen verfügbaren Interfaces
PORT = 65432


def handle_client(conn: socket.socket, addr: Any, app_instance: 'MainApp'):
    print(f"Verbunden mit {addr}")

    client_send_queue: queue.Queue[Optional[str]] = queue.Queue()  # Queue for messages to this client
    app_instance.add_client_queue(addr, client_send_queue)

    send_thread = threading.Thread(target=send_to_client_from_queue, args=(conn, client_send_queue, addr), daemon=True)
    send_thread.start()

    try:
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    print(f"Verbindung mit {addr} geschlossen (Client hat geschlossen).")
                    break
                decoded_data = data.decode('utf-8')
                # print(f"Client ({addr}) sagt: {decoded_data}") # Optional: Debug
                message_receive(decoded_data)  # This processes client -> server messages
    except ConnectionResetError:
        print(f"Verbindung mit {addr} unerwartet geschlossen.")
    except socket.timeout:
        print(f"Timeout bei Verbindung mit {addr}.")
    except Exception as e:
        print(f"Fehler bei der Kommunikation mit {addr}: {e}")
    finally:
        print(f"Handler für {addr} beendet.")
        app_instance.remove_client_queue(addr)
        try:
            client_send_queue.put(None)  # Sentinel to stop send_thread
        except Exception as e:
            print(f"Error putting sentinel to client queue for {addr}: {e}")


def send_to_client_from_queue(conn: socket.socket, q: queue.Queue[Optional[str]], addr: Any):
    peer_name = addr
    try:
        peer_name = conn.getpeername()
    except OSError:
        pass

    while True:
        try:
            message_to_client = q.get()
            if message_to_client is None:
                break

            conn.sendall(message_to_client.encode('utf-8'))
            q.task_done()

        except ConnectionResetError:
            print(f"Send thread: Verbindung zu {peer_name} zurückgesetzt.")
            break
        except ConnectionAbortedError:
            print(f"Send thread: Verbindung zu {peer_name} abgebrochen.")
            break
        except OSError as e:
            print(f"Send thread: Socket-Fehler beim Senden an {peer_name}: {e}")
            break
        except Exception as e:
            print(f"Error in send_to_client_from_queue for {peer_name}: {e}")
            break


def connect(app_instance: 'MainApp'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server lauscht auf {HOST}:{PORT}")
        while True:
            try:
                conn, addr = s.accept()
                conn.settimeout(60)
                client_handler_thread = threading.Thread(
                    target=handle_client, args=(conn, addr, app_instance), daemon=True
                )
                client_handler_thread.start()
            except Exception as e:
                print(f"Fehler beim Akzeptieren einer Verbindung: {e}")


# DIESE FUNKTION (AUSSERHALB DER KLASSE) ERSETZEN

def message_receive(data: str):
    data_list = data.split("$#")
    p: Dict[str, Any] = {}

    # Expected from scanner: timestamp_scan_lokal_formatted$#start_nummer$#scan_id$#
    if len(data_list) < 4:  # Check for at least 3 values + trailing empty from $#
        print(f"Error: Received data not in expected format (timestamp, start_nr, scan_id): {data}")
        return

    # Timestamp from scanner is already formatted as HH:MM:SS (DD.MM)
    # We need to parse this into a datetime object for internal storage.
    timestamp_str_from_scanner = data_list[0]  # Format: "HH:MM:SS (DD.MM)"

    try:
        time_part_str, date_part_str_with_paren = timestamp_str_from_scanner.split(" (")
        date_part_str = date_part_str_with_paren[:-1]  # Remove trailing ")"

        day, month = map(int, date_part_str.split('.'))
        hour, minute, second = map(int, time_part_str.split(':'))

        current_year = datetime.datetime.now().year  # Assume current year for scanner's timestamp

        # This will be stored as 'timestamp_scan_ankunft'
        scanner_dt_object = datetime.datetime(current_year, month, day, hour, minute, second)
        p["timestamp_scan_ankunft"] = scanner_dt_object.isoformat()  # Store as ISO string

    except (ValueError, IndexError) as e:
        print(f"Error parsing scanner timestamp: '{timestamp_str_from_scanner}'. Error: {e}. Using current time.")
        p["timestamp_scan_ankunft"] = datetime.datetime.now().isoformat()

    try:
        p["start_nummer"] = data_list[1]
    except ValueError:  # Should not happen if scanner sends string
        print(f"Error: Invalid start_nummer from client: {data_list[1]}")
        return

    p["scan_id"] = data_list[2]  # This is the ScanLogEntry.scan_id from ScannerApp
    p["zugeordneter_scan_id"] = p["scan_id"]  # Link it immediately for clarity

    if MainApp._instance and "Runde" in MainApp._instance.settings_data:
        p["round_number"] = MainApp._instance.settings_data["Runde"]
    else:
        p["round_number"] = "PR"  # <<< GEÄNDERT von 0 auf "PR"

    if MainApp._instance:
        data_to_add = p.copy()
        # 'timestamp_messung' will be None initially for entries from scanner,
        # until Arduino/Manual entry provides it.
        # 'timestamp_scan_ankunft' is now set from the scanner's message.
        MainApp._instance.after(0, lambda: MainApp._instance.add_item_to_tree(data_to_add))
    else:
        print("ERROR: MainApp instance not available. Cannot add item to tree via message_receive.")


try:
    from common.constants import (
        STATUS_NEW, STATUS_MODIFIED, STATUS_DELETED, STATUS_SYNCED_LOCAL, STATUS_SYNCED, STATUS_COMPLETE,
        COLOR_STATUS_NEW_BG, COLOR_STATUS_MODIFIED_BG, COLOR_STATUS_DELETED_FG, COLOR_STATUS_COMPLETE_BG,
        COLOR_STATUS_SYNCED_LOCAL_BG, ROUND_NAMES,
    )
    from common.data_models import MainDataEntry, DisplayableMainData
except ImportError as e:
    print(e)
    print("FEHLER: common.constants oder common.data_models nicht gefunden.")
    STATUS_NEW, STATUS_MODIFIED, STATUS_DELETED, STATUS_SYNCED, STATUS_SYNCED_LOCAL, STATUS_COMPLETE = "new", "modified", "deleted", "synced", 'saved internally', "complete"
    COLOR_STATUS_NEW_BG, COLOR_STATUS_MODIFIED_BG, COLOR_STATUS_DELETED_FG, COLOR_STATUS_COMPLETE_BG, COLOR_STATUS_SYNCED_LOCAL_BG = "lightgreen", "lightyellow", "red", "lightblue", "lightgrey"
    ROUND_NAMES = ["PR", "H1", "H2"]

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class MainApp(ctk.CTk):
    _instance: Optional['MainApp'] = None

    def __init__(self):
        super().__init__()
        self.headers = None
        self.add_item_button = None
        self.tree_columns = None
        MainApp._instance = self
        self.title("Main App (Standalone)")
        self.geometry("1100x750")

        self.data_items: Dict[str, Dict[str, Any]] = {}
        self.data_lock = threading.RLock()
        self._context_menu_item_id: Optional[str] = None

        self.settings_data: Dict[str, Any] = {
            "Runde": "PR",  # <<< GEÄNDERT von 0 auf "PR"
            "Server Adresse (für API)": "localhost",
            "API Endpoint Website": "http://localhost:8000/api/",
            "username": "Josua",
            "password": "hallo1234"
        }
        self.setting_widgets: Dict[str, ctk.CTkBaseClass] = {}
        self._settings_ui_built = False
        self.versions: List[Dict[str, Any]] = []

        self.clients: Dict[Any, queue.Queue[Optional[str]]] = {}
        self.client_management_lock = threading.Lock()

        self.racers: List[Dict[str, Any]] = []
        self.racer_names_by_start_number: Dict[str, str] = {}

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.top_button_frame = ctk.CTkFrame(self.main_container, height=60)
        self.top_button_frame.pack(fill="x", pady=(0, 10))

        self.show_data_view_button = ctk.CTkButton(self.top_button_frame, text="Datenansicht",
                                                   command=self.show_data_view)
        self.show_data_view_button.pack(side="left", padx=5, pady=5)
        self.show_settings_view_button = ctk.CTkButton(self.top_button_frame, text="Einstellungen",
                                                       command=self.show_settings_view)
        self.show_settings_view_button.pack(side="left", padx=5, pady=5)
        self.push_button = ctk.CTkButton(self.top_button_frame, text="Sichern (Intern)",
                                         command=self.push_data_internally)
        self.push_button.pack(side="left", padx=10, pady=5)
        self.versions_button = ctk.CTkButton(self.top_button_frame, text="Vorige Sicherungen",
                                             command=self.show_previous_versions)
        self.versions_button.pack(side="left", padx=5, pady=5)
        self.push_to_website_button = ctk.CTkButton(self.top_button_frame, text="Push to Website",
                                                    command=self.initiate_push_to_website, fg_color="red",
                                                    state="disabled")
        self.push_to_website_button.pack(side="left", padx=10, pady=5)
        self.pull_from_website_button = ctk.CTkButton(self.top_button_frame, text="Pull von Website",
                                                      command=self.open_pull_selection_dialog, fg_color="red",
                                                      state="disabled")
        self.pull_from_website_button.pack(side="left", padx=5, pady=5)
        self.connect_to_website_button = ctk.CTkButton(self.top_button_frame, text="Connect to Website",
                                                       command=self.start_connection, fg_color="red")
        self.connect_to_website_button.pack(side="left", padx=5, pady=5)
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)
        self.data_view_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.settings_view_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.settings_scroll_frame: Optional[ctk.CTkScrollableFrame] = None

        self.tree: Optional[ttk.Treeview] = None
        self.setup_data_view()
        self.setup_settings_view()
        self.tree_context_menu = tk.Menu(self, tearoff=0, font=ctk.CTkFont(size=12))

        self.show_data_view()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.server_thread = threading.Thread(target=connect, args=(self,), daemon=True)
        self.server_thread.start()

        self.arduino_thread = threading.Thread(target=self.arduino_connection, args=(), daemon=True)
        self.arduino_thread.start()

        self.website_thread = threading.Thread(target=self.start_connection, args=(), daemon=True)
        self.website_thread.start()

    def connect_to_website(self):
        try:
            username = self.settings_data["username"]
            password = self.settings_data["password"]
            auth_endpoint = self.settings_data["API Endpoint Website"] + "token/"
            auth_response = requests.post(auth_endpoint, json={
                "username": username,
                "password": password
            })

            json_response = auth_response.json()
            refresh_token = json_response["refresh"]
            print(refresh_token)

            refresh_endpoint = self.settings_data["API Endpoint Website"] + "token/refresh/"
            refresh_response = requests.post(refresh_endpoint, json={
                "refresh": refresh_token
            })

            json_response = auth_response.json()
            access_token = json_response["access"]
            print(access_token)
            return access_token
        except Exception as e:
            print(f"Error bei der Verbindung mit dem Server: {e}")
            return None

    def start_connection(self):
        self.website_connect()
        if not self.headers:
            return
        self.pull_race_runs_from_website()
        if not self.racers:
            current_racers = self.get_data_website(f"{self.settings_data['API Endpoint Website']}racers/")
            self._update_racer_data_store(current_racers, from_website_pull=False)

    def website_connect(self):
        access_token = None
        for i in range(5):
            access_token = self.connect_to_website()
            if access_token:
                self.connect_to_website_button.configure(text="Connected to Website", fg_color="green",
                                                         state="disabled")
                self.pull_from_website_button.configure(fg_color="darkblue", state="normal")
                self.push_to_website_button.configure(fg_color="darkgreen", state="normal")
                break
        if not access_token:
            print("Die Verbindung hat nicht funktioniert, ändere die Einstellunge oder starte den Server.")
            return
        self.headers = {"Authorization": f"Bearer {access_token}"}
        return

    def get_data_website(self, url):
        for i in range(5):
            try:
                return requests.get(url, headers=self.headers).json()
            except Exception as e:
                print(f"Error: {e}. Website connect wird gestartet")
                self.website_connect()
        self.connect_to_website_button.configure(text="Connect to Website", fg_color="red", state="normal")
        self.pull_from_website_button.configure(fg_color="red", state="disabled")
        self.push_to_website_button.configure(fg_color="red", state="disabled")
        return None

    def push_data_website(self, data, run_identifier = 1):
        print("Pushing data:", data)
        try:
            # Gemeinsame URL-Basis und Daten definieren, um Wiederholungen zu vermeiden
            base_url = f"{self.settings_data['API Endpoint Website']}raceruns/"
            response = None  # Initialisieren Sie die response-Variable

            if data.get('_action') == "upsert":
                # Daten für POST-Request vorbereiten
                payload = {
                    "racer_start_number": str(data.get("start_nummer")),
                    "time_in_seconds": data.get("renn_zeit"),
                    "run_identifier": run_identifier,
                    "run_type": data.get("round_number"),
                    "recorded_at": data.get('timestamp_messung')
                }
                response = requests.post(base_url, json=payload,
                                         headers=self.headers)

            elif data.get('_action') == "delete":
                item_id = data.get('app_item_id')
                response = requests.delete(f"{base_url}{item_id}/", headers=self.headers)

            elif data.get('_action') == "changed":
                item_id = data.get('app_item_id')
                # Daten für PATCH-Request vorbereiten
                payload = {
                    "racer_start_number": str(data.get("start_nummer")),
                    "time_in_seconds": data.get("renn_zeit"),
                    "run_identifier": run_identifier,
                    "run_type": data.get("round_number"),
                    "recorded_at": data.get('timestamp_messung')
                }
                response = requests.patch(f"{base_url}{item_id}/", json=payload, headers=self.headers)
            else:
                print(f"Error: Unbekannte Aktion '{data.get('_action')}'")
                return False

            # Diese Zeile löst bei einem 4xx oder 5xx Fehler eine HTTPError Exception aus
            response.raise_for_status()

            # Dieser Code wird nur bei Erfolg (Status 2xx) ausgeführt
            print("Push erfolgreich!", response.status_code)
            # Optional: API-Antwort verarbeiten, falls es eine gibt
            # print(response.json())
            return True

        except requests.HTTPError as http_err:
            print(
                f"HTTP-Fehler beim Pushen: {http_err}")  # Gibt die volle Fehlermeldung aus, z.B. "400 Client Error..."
            try:
                print(f"API-Antwort: {http_err.response.json()}")
            except ValueError:
                print(f"API-Antwort (Text): {http_err.response.text}")
            return False

        # Fangen Sie andere Fehler ab (z.B. Netzwerkprobleme, DNS-Fehler)
        except requests.RequestException as req_err:
            print(f"Netzwerk- oder Verbindungsfehler: {req_err}")
            # self.connect_to_website_button.configure(...)
            return False

        # Ein allgemeiner Fallback für unerwartete Fehler
        except Exception as e:
            print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
            return False

    def _update_racer_data_store(self, new_racers_list: List[Dict[str, Any]], from_website_pull: bool = True):
        self.racers = new_racers_list
        self.racer_names_by_start_number.clear()
        for racer in self.racers:
            start_num = racer.get("start_number")
            full_name = racer.get("full_name")
            if start_num and full_name:
                self.racer_names_by_start_number[str(start_num)] = str(full_name)

        if self.tree and self.winfo_exists():
            self.after(0, self.refresh_treeview_display_fully)

        self.broadcast_racer_data()

        if from_website_pull:
            messagebox.showinfo("Racer Daten Update", f"{len(new_racers_list)} Racer-Einträge aktualisiert/geladen.",
                                parent=self)

    def arduino_connection(self):
        while True:
            run_time = None
            if run_time is not None:
                with self.data_lock:
                    if not self.tree:
                        time.sleep(0.1)
                        continue
                    children = self.tree.get_children("")
                    if children:
                        target_item_id = None
                        # Prioritize items that have a start_nummer but no renn_zeit
                        # This implies they came from a scanner and are awaiting time.
                        for item_id_check in children:
                            if item_id_check in self.data_items:
                                item_details = self.data_items[item_id_check]
                                data_dict = item_details.get("data", {})
                                if data_dict.get("start_nummer") and data_dict.get("renn_zeit") is None:
                                    target_item_id = item_id_check
                                    break  # Found a suitable item

                        if not target_item_id and children:  # Fallback: pick the first item without renn_zeit
                            for item_id_check in children:
                                if item_id_check in self.data_items:
                                    item_details = self.data_items[item_id_check]
                                    if item_details.get("data", {}).get("renn_zeit") is None:
                                        target_item_id = item_id_check
                                        break

                        if target_item_id:
                            current_item_data = self.data_items[target_item_id].get("data",
                                                                                    {})  # No need for deepcopy before update
                            update_payload = {"renn_zeit": run_time}
                            # Arduino provides measurement, so this is timestamp_messung
                            update_payload["timestamp_messung"] = datetime.datetime.now().isoformat()
                            self.update_tree_item(target_item_id, update_payload)
                            print(
                                f"Arduino: Rennzeit {run_time} für Item {target_item_id} (Startnr: {current_item_data.get('start_nummer', 'N/A')}) gesetzt.")
            time.sleep(0.05)

    def on_closing(self):
        print("MainApp wird geschlossen...")
        with self.client_management_lock:
            for client_q in list(self.clients.values()):
                try:
                    client_q.put(None)
                except Exception as e:
                    print(f"Error sending sentinel to client queue on closing: {e}")
        time.sleep(0.2)
        self.destroy()

    def add_client_queue(self, addr: Any, client_q: queue.Queue[Optional[str]]):
        with self.client_management_lock:
            self.clients[addr] = client_q
        print(f"Client queue for {addr} added. Sending initial data sets.")
        self.send_all_data_to_client(client_q)
        self.send_racer_data_to_client(client_q)

    def remove_client_queue(self, addr: Any):
        with self.client_management_lock:
            if addr in self.clients:
                del self.clients[addr]
                print(f"Client queue for {addr} removed.")

    def _format_item_for_client(self, item_id: str, details: Dict[str, Any]) -> Optional[str]:
        data = details.get("data", {})
        start_nummer_str = str(data.get("start_nummer", ""))
        racer_name_str = self.racer_names_by_start_number.get(start_nummer_str, "-")
        round_number_str = str(data.get("round_number", ""))
        renn_zeit_raw = data.get("renn_zeit")
        renn_zeit_str = f"{renn_zeit_raw:.3f}" if isinstance(renn_zeit_raw, (float, int)) else \
            str(renn_zeit_raw if renn_zeit_raw is not None else "")

        # For client, send timestamp_messung if available, otherwise timestamp_scan_ankunft
        # The client ("Alle Renndaten" tab) will display this as "Messzeit (MainApp)"
        ts_to_send_raw = data.get("timestamp_messung") or data.get("timestamp_scan_ankunft")

        timestamp_display_str = ""
        if ts_to_send_raw:
            try:
                # Ensure it's a datetime object if it's not already an ISO string
                if isinstance(ts_to_send_raw, str):
                    dt_obj = datetime.datetime.fromisoformat(ts_to_send_raw.replace(" ", "T"))
                elif isinstance(ts_to_send_raw, datetime.datetime):
                    dt_obj = ts_to_send_raw
                else:  # Should not happen if data is consistently ISO strings or datetime
                    raise ValueError("Unsupported timestamp type for client formatting")

                timestamp_display_str = dt_obj.strftime("%H:%M:%S (%d.%m.%Y)")
            except ValueError:
                timestamp_display_str = str(ts_to_send_raw)  # Fallback to raw string

        return f"{item_id}$#{start_nummer_str}$#{racer_name_str}$#{round_number_str}$#{renn_zeit_str}$#{timestamp_display_str}"

    def _get_all_data_for_clients_payload(self) -> str:
        all_items_formatted_strings = []
        with self.data_lock:
            for item_id, details in self.data_items.items():
                if details.get("status") == STATUS_DELETED:
                    continue
                formatted_item = self._format_item_for_client(item_id, details)
                if formatted_item:
                    all_items_formatted_strings.append(formatted_item)

        if not all_items_formatted_strings:
            return "ALL_DATA_EMPTY"
        return "ALL_DATA:" + "|".join(all_items_formatted_strings)

    def send_all_data_to_client(self, client_q: queue.Queue[Optional[str]]):
        payload = self._get_all_data_for_clients_payload()
        try:
            client_q.put(payload)
        except Exception as e:
            print(f"Error putting all_data (race runs) payload to client queue: {e}")

    def _get_racer_data_payload(self) -> str:
        if not self.racer_names_by_start_number:
            return "RACER_DATA_EMPTY"
        payload_parts = [f"{sn}:{name}" for sn, name in self.racer_names_by_start_number.items()]
        return "RACER_DATA_UPDATE:" + "|".join(payload_parts)

    def send_racer_data_to_client(self, client_q: queue.Queue[Optional[str]]):
        payload = self._get_racer_data_payload()
        try:
            client_q.put(payload)
        except Exception as e:
            print(f"Error putting racer_data payload to client queue: {e}")

    def broadcast_racer_data(self):
        payload = self._get_racer_data_payload()
        if payload is None:
            print("No racer data payload to broadcast.")
            return
        with self.client_management_lock:
            for addr, client_q in self.clients.items():
                try:
                    client_q.put(payload)
                except Exception as e:
                    print(f"Error putting racer_data message to client queue for {addr}: {e}")
        print(f"Racer data broadcasted to {len(self.clients)} clients.")

    def broadcast_data_update(self, item_id_updated: Optional[str] = None, is_delete: bool = False):
        payload: Optional[str] = None
        if item_id_updated and is_delete:
            payload = f"DELETE_DATA:{item_id_updated}"
        elif item_id_updated:
            with self.data_lock:
                if item_id_updated in self.data_items and self.data_items[item_id_updated].get(
                        "status") != STATUS_DELETED:
                    details = self.data_items[item_id_updated]
                    formatted_item = self._format_item_for_client(item_id_updated, details)
                    if formatted_item:
                        payload = f"UPDATE_DATA:{formatted_item}"
                    else:
                        print(f"Error formatting item {item_id_updated} for broadcast.")
                        return
                elif item_id_updated in self.data_items and self.data_items[item_id_updated].get(
                        "status") == STATUS_DELETED:
                    payload = f"DELETE_DATA:{item_id_updated}"
                else:
                    payload = f"DELETE_DATA:{item_id_updated}"
        else:
            payload = self._get_all_data_for_clients_payload()

        if payload is None:
            print("No race run data payload to broadcast.")
            return
        with self.client_management_lock:
            for addr, client_q in self.clients.items():
                try:
                    client_q.put(payload)
                except Exception as e:
                    print(f"Error putting race run message to client queue for {addr}: {e}")

    def setup_data_view(self):
        self.add_item_button = ctk.CTkButton(self.data_view_frame, text="Manueller Eintrag",
                                             command=lambda: self.open_manual_entry_dialog())
        self.add_item_button.pack(pady=10, padx=10, anchor="nw")
        tree_container = ctk.CTkFrame(self.data_view_frame)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree_columns = ("status_indicator", "timestamp_combined", "start_number", "racer_name",
                             "round_number", "time_required", "scan_id_col")
        self.tree = ttk.Treeview(tree_container, columns=self.tree_columns, show="headings")

        vsb = ctk.CTkScrollbar(tree_container, command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ctk.CTkScrollbar(tree_container, command=self.tree.xview, orientation="horizontal")
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.heading("status_indicator", text="S", anchor=tk.W)
        self.tree.heading("timestamp_combined", text="Zeit", anchor=tk.W)  # Changed from "Uhrzeit" to generic "Zeit"
        self.tree.heading("start_number", text="Startnr.", anchor=tk.W)
        self.tree.heading("racer_name", text="Name", anchor=tk.W)
        self.tree.heading("round_number", text="Runde", anchor=tk.CENTER)
        self.tree.heading("time_required", text="Rennzeit", anchor=tk.E)
        self.tree.heading("scan_id_col", text="Scan ID", anchor=tk.W)

        self.tree.column("status_indicator", width=30, minwidth=30, stretch=tk.NO, anchor=tk.CENTER)
        self.tree.column("timestamp_combined", width=160, minwidth=130, stretch=tk.YES)
        self.tree.column("start_number", width=80, minwidth=60, anchor=tk.W, stretch=tk.NO)
        self.tree.column("racer_name", width=180, minwidth=120, stretch=tk.YES)
        self.tree.column("round_number", width=60, minwidth=50, anchor=tk.CENTER, stretch=tk.NO)
        self.tree.column("time_required", width=100, minwidth=80, anchor=tk.E, stretch=tk.NO)
        self.tree.column("scan_id_col", width=120, minwidth=100, stretch=tk.NO)

        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self._apply_treeview_styling()

    def _apply_treeview_styling(self):
        style = ttk.Style(self)
        style.theme_use("default")
        frame_fg = self._get_theme_color("CTkFrame", "fg_color", default_light="#DBDBDB", default_dark="#2B2B2B")
        label_text = self._get_theme_color("CTkLabel", "text_color", default_light="#000000", default_dark="#FFFFFF")
        btn_fg = self._get_theme_color("CTkButton", "fg_color", default_light="#3A7EBF", default_dark="#1F538D")
        btn_text_sel = self._get_theme_color("CTkButton", "text_color", default_light="#FFFFFF", default_dark="#FFFFFF")
        btn_hover = self._get_theme_color("CTkButton", "hover_color", default_light="#325882", default_dark="#14375E")

        style.configure("Treeview", background=frame_fg, foreground=label_text, fieldbackground=frame_fg, rowheight=28,
                        font=ctk.CTkFont(size=12))
        style.map("Treeview", background=[('selected', btn_fg)], foreground=[('selected', btn_text_sel)])
        style.configure("Treeview.Heading", background=btn_hover, foreground=label_text, relief="flat",
                        font=ctk.CTkFont(size=13, weight="bold"))
        style.map("Treeview.Heading", background=[('active', btn_fg)])
        style.configure(f"{STATUS_NEW}.Treeview", background=COLOR_STATUS_NEW_BG)
        style.configure(f"{STATUS_MODIFIED}.Treeview", background=COLOR_STATUS_MODIFIED_BG)
        style.configure(f"{STATUS_DELETED}.Treeview", foreground=COLOR_STATUS_DELETED_FG)
        style.configure(f"{STATUS_COMPLETE}.Treeview", background=COLOR_STATUS_COMPLETE_BG)
        style.configure(f"{STATUS_SYNCED_LOCAL}.Treeview", background=COLOR_STATUS_SYNCED_LOCAL_BG)
        style.configure(f"{STATUS_SYNCED}.Treeview")

    def _get_theme_color(self, widget_name: str, color_type: str, default_light: str = "#FFFFFF",
                         default_dark: str = "#000000") -> str:
        try:
            val = ctk.ThemeManager.theme[widget_name][color_type]
            return str(val[1] if ctk.get_appearance_mode().lower() == "dark" else val[0]) if isinstance(val, (list,
                                                                                                              tuple)) else str(
                val)
        except:
            return default_dark if ctk.get_appearance_mode().lower() == "dark" else default_light

    def setup_settings_view(self):
        if self._settings_ui_built:
            for key, value in self.settings_data.items():
                widget = self.setting_widgets.get(key)
                if not widget: continue
                if key in ["Server Port (eigener)", "Automatischer Start Server"]: continue
                if isinstance(widget, ctk.CTkCheckBox):
                    var_ref = widget.cget("variable")
                    actual_var = widget.nametowidget(var_ref) if isinstance(var_ref, str) else var_ref
                    if isinstance(actual_var, tk.BooleanVar): actual_var.set(bool(value))
                elif isinstance(widget, ctk.CTkComboBox):
                    widget.set(str(value))
                elif isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))
            return

        if self.settings_scroll_frame is None:
            self.settings_scroll_frame = ctk.CTkScrollableFrame(self.settings_view_frame,
                                                                label_text="App Einstellungen")
            self.settings_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            for child in self.settings_scroll_frame.winfo_children():
                child.destroy()
        self.setting_widgets.clear()
        for idx, (key, value) in enumerate(self.settings_data.items()):
            if key in ["Server Port (eigener)", "Automatischer Start Server"]: continue
            setting_frame = ctk.CTkFrame(self.settings_scroll_frame)
            setting_frame.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(setting_frame, text=f"{key}:", width=220, anchor="w").pack(side="left", padx=(0, 10))
            widget: Optional[ctk.CTkBaseClass] = None
            if isinstance(value, bool):
                bool_var = tk.BooleanVar(value=value)
                widget = ctk.CTkCheckBox(setting_frame, text="", variable=bool_var,
                                         command=lambda k=key, v=bool_var: self._on_setting_changed(k, v))
            # <<< GEÄNDERT: Eigene Logik für die "Runde"-Einstellung
            elif key == "Runde":
                widget = ctk.CTkComboBox(setting_frame, values=["PR", "H1", "H2"],
                                         command=lambda choice, k=key: self._on_setting_changed(k, choice))
                widget.set(str(value))
            elif key == "Server Adresse (für API)" and isinstance(value, str):
                options = ["localhost", "127.0.0.1", str(self.settings_data.get(key, "localhost"))]
                unique_options = sorted(list(set(filter(None, options))))
                widget = ctk.CTkComboBox(setting_frame, values=unique_options,
                                         command=lambda choice, k=key: self._on_setting_changed(k, choice))
                widget.set(str(value))
            elif isinstance(value, (int, float, str)):
                widget = ctk.CTkEntry(setting_frame)
                widget.insert(0, str(value))
                widget.bind("<Return>", lambda event, k=key, w=widget: self._on_setting_changed(k, w))
                widget.bind("<FocusOut>", lambda event, k=key, w=widget: self._on_setting_changed(k, w))
            else:
                widget = ctk.CTkLabel(setting_frame, text=f"Unsupported type: {type(value)}")
            if widget:
                widget.pack(side="left", fill="x", expand=True, padx=5)
                self.setting_widgets[key] = widget
        self._settings_ui_built = True

    def _on_setting_changed(self, key: str, value_or_widget_or_var: Any):
        if key in ["Server Port (eigener)", "Automatischer Start Server"]: return

        current_setting_value = self.settings_data[key]
        widget = self.setting_widgets.get(key)
        new_value: Any = None

        if isinstance(widget, ctk.CTkCheckBox) and isinstance(value_or_widget_or_var, tk.BooleanVar):
            new_value = value_or_widget_or_var.get()
        elif isinstance(widget, ctk.CTkComboBox) and isinstance(value_or_widget_or_var, str):
            new_value = value_or_widget_or_var
        elif isinstance(widget, ctk.CTkEntry) and value_or_widget_or_var == widget:
            new_value_str = widget.get()
            try:
                if isinstance(current_setting_value, int):
                    new_value = int(new_value_str)
                elif isinstance(current_setting_value, float):
                    new_value = float(new_value_str)
                else:
                    new_value = new_value_str
            except ValueError:
                messagebox.showerror("Error",
                                     f"Invalid value for '{key}': '{new_value_str}'. Expected type: {type(current_setting_value).__name__}.",
                                     parent=self)
                widget.delete(0, tk.END)
                widget.insert(0, str(current_setting_value))
                return
        else:
            print(f"Warning: _on_setting_changed called with unexpected parameters for key '{key}'")
            return

        if self.settings_data.get(key) != new_value:
            self.settings_data[key] = new_value
            print(f"Setting '{key}' changed to: {new_value}")
            if isinstance(widget, ctk.CTkComboBox) and widget.get() != str(new_value):
                widget.set(str(new_value))

    def show_data_view(self):
        self.settings_view_frame.pack_forget()
        self.data_view_frame.pack(fill="both", expand=True)
        self.title("Main App - Daten (Standalone)")

    def show_settings_view(self):
        self.data_view_frame.pack_forget()
        self.setup_settings_view()
        self.settings_view_frame.pack(fill="both", expand=True)
        self.title("Main App - Einstellungen (Standalone)")

    def _get_status_indicator(self, status: Optional[str]) -> str:
        return {
            STATUS_NEW: "➕",
            STATUS_MODIFIED: "✏️",
            STATUS_DELETED: "🗑️",
            STATUS_SYNCED: "✔️",  # Synced to website
            STATUS_SYNCED_LOCAL: "💾",  # Synced locally
            STATUS_COMPLETE: "🏁"
        }.get(status or "", "?")

    def _create_tree_item_values(self, item_id: str, item_details: Dict[str, Any]) -> tuple:
        data = item_details.get("data", {})
        status_ind = self._get_status_indicator(item_details.get("status"))

        # ***** MODIFIZIERT: Timestamp-Logik für Anzeige *****
        # Prioritize timestamp_messung (from Arduino/Manual)
        # Fallback to timestamp_scan_ankunft (from Scanner)
        # Fallback to created_at if neither is present
        ts_for_display_raw = data.get("timestamp_messung") or data.get("timestamp_scan_ankunft") or data.get(
            "created_at")
        ts_combined_display = "-"

        if ts_for_display_raw:
            try:
                # All stored timestamps should be ISO format strings or datetime objects
                if isinstance(ts_for_display_raw, str):
                    dt_obj = datetime.datetime.fromisoformat(ts_for_display_raw.replace(" ", "T"))
                elif isinstance(ts_for_display_raw, datetime.datetime):
                    dt_obj = ts_for_display_raw
                else:  # Should not happen
                    dt_obj = None

                if dt_obj:
                    # Show with milliseconds if it's likely a scan timestamp and no measurement time yet
                    if ts_for_display_raw == data.get("timestamp_scan_ankunft") and not data.get("timestamp_messung"):
                        ts_combined_display = dt_obj.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
                    else:  # Otherwise, just HH:MM:SS
                        ts_combined_display = dt_obj.strftime("%H:%M:%S")
                else:
                    ts_combined_display = str(ts_for_display_raw)[:12]  # Fallback to raw string part

            except ValueError:  # If fromisoformat fails for a string
                ts_combined_display = str(ts_for_display_raw)[:12]  # Fallback display for unparsable string

        renn_zeit_val = data.get("renn_zeit")
        renn_zeit_display = f"{renn_zeit_val:.3f}s" if isinstance(renn_zeit_val, (float, int)) else "-"

        # Use zugeordneter_scan_id if present, otherwise the item's own scan_id (if it's from a direct scan message)
        scan_id_val = data.get("zugeordneter_scan_id") or data.get("scan_id")
        scan_id_display = (str(scan_id_val)[:8] + "...") if scan_id_val and len(str(scan_id_val)) > 8 else str(
            scan_id_val or "-")

        start_nummer_val = str(data.get("start_nummer", ""))
        racer_name_display = self.racer_names_by_start_number.get(start_nummer_val, "Startnummer unbekannt!")

        return (
            status_ind,
            ts_combined_display,
            start_nummer_val if start_nummer_val else "-",
            racer_name_display,
            str(data.get("round_number", "-")),
            renn_zeit_display,
            scan_id_display
        )

    def _update_tree_item_display(self, item_id: str):
        if not self.tree or not self.winfo_exists(): return
        if item_id not in self.data_items:
            if self.tree.exists(item_id): self.tree.delete(item_id)
            return

        try:
            item_details = self.data_items[item_id]
        except KeyError:
            if self.tree.exists(item_id): self.tree.delete(item_id)
            return

        values = self._create_tree_item_values(item_id, item_details)
        tag = item_details.get("status", "")

        if self.tree.exists(item_id):
            self.tree.item(item_id, values=values, tags=(tag,))
        else:
            self.tree.insert("", 0, iid=item_id, values=values, tags=(tag,))

    def add_item_to_tree(self, current_data_dict: Dict[str, Any], item_id: Optional[str] = None) -> str:
        new_item_id = item_id or str(uuid.uuid4())
        with self.data_lock:
            # Ensure timestamps are in ISO format strings
            # timestamp_scan_ankunft comes from message_receive, already isoformat
            current_data_dict.setdefault("created_at", datetime.datetime.now().isoformat())
            current_data_dict["updated_at"] = datetime.datetime.now().isoformat()

            # If 'scan_id' is present from scanner, make sure 'zugeordneter_scan_id' is also set
            if "scan_id" in current_data_dict and "zugeordneter_scan_id" not in current_data_dict:
                current_data_dict["zugeordneter_scan_id"] = current_data_dict["scan_id"]

            self.data_items[new_item_id] = {
                "data": current_data_dict,
                "status": STATUS_NEW,
                "original_data_snapshot": None,
                "data_before_delete": None
            }
            self.after(0, self._update_tree_item_display, new_item_id)

        self.broadcast_data_update(new_item_id)
        return new_item_id

    def update_tree_item(self, item_id: str, new_data_dict: Dict[str, Any]):
        with self.data_lock:
            if item_id not in self.data_items or self.data_items[item_id]["status"] == STATUS_DELETED:
                return

            details = self.data_items[item_id]
            # Create a snapshot if the item is in any 'clean' state (local or web synced) before modifying it
            if details["status"] in [STATUS_SYNCED, STATUS_SYNCED_LOCAL] and details["original_data_snapshot"] is None:
                details["original_data_snapshot"] = copy.deepcopy(details["data"])

            details["data"]["updated_at"] = datetime.datetime.now().isoformat()
            if "renn_zeit" in new_data_dict and new_data_dict["renn_zeit"] is not None:
                if details["data"].get("renn_zeit") != new_data_dict["renn_zeit"]:
                    new_data_dict.setdefault("timestamp_messung", datetime.datetime.now().isoformat())

            if "timestamp_messung" in new_data_dict and isinstance(new_data_dict["timestamp_messung"],
                                                                   datetime.datetime):
                new_data_dict["timestamp_messung"] = new_data_dict["timestamp_messung"].isoformat()

            details["data"].update(new_data_dict)
            if details["status"] != STATUS_NEW:
                details["status"] = STATUS_MODIFIED

            if (details["data"].get("start_nummer") and
                    details["data"].get("renn_zeit") is not None and
                    details["status"] not in [STATUS_NEW, STATUS_SYNCED, STATUS_DELETED, STATUS_COMPLETE]):
                details["status"] = STATUS_COMPLETE

            self.after(0, self._update_tree_item_display, item_id)

        self.broadcast_data_update(item_id)

    def open_manual_entry_dialog(self, item_id_to_edit: Optional[str] = None):
        is_edit = item_id_to_edit is not None
        initial_data = {}
        if is_edit and item_id_to_edit:
            with self.data_lock:
                if item_id_to_edit not in self.data_items or self.data_items[item_id_to_edit].get(
                        "status") == STATUS_DELETED:
                    messagebox.showinfo("Info", "Eintrag nicht bearbeitbar oder bereits gelöscht.", parent=self)
                    return
                initial_data = copy.deepcopy(self.data_items[item_id_to_edit].get("data", {}))
        else:
            item_id_to_edit = None

        dialog = ctk.CTkToplevel(self)
        dialog.title("Manueller Eintrag" if not is_edit else "Eintrag Bearbeiten")
        dialog.geometry("450x380")
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        dialog.columnconfigure(1, weight=1)

        row_idx = 0
        ctk.CTkLabel(dialog, text="Startnummer:").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        e_sn = ctk.CTkEntry(dialog)
        e_sn.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        e_sn.insert(0, str(initial_data.get("start_nummer", "")))
        row_idx += 1

        name_var = tk.StringVar(
            value=self.racer_names_by_start_number.get(str(initial_data.get("start_nummer", "")), "-"))
        ctk.CTkLabel(dialog, text="Name:").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        l_name = ctk.CTkLabel(dialog, textvariable=name_var, anchor="w")
        l_name.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        row_idx += 1

        def _update_name_in_dialog_manual_entry(*args):
            sn_val = e_sn.get().strip()
            name_var.set(self.racer_names_by_start_number.get(sn_val, "Startnummer unbekannt!"))

        e_sn_var = tk.StringVar(value=str(initial_data.get("start_nummer", "")))
        e_sn.configure(textvariable=e_sn_var)
        e_sn_var.trace_add("write", _update_name_in_dialog_manual_entry)
        _update_name_in_dialog_manual_entry()

        # <<< GEÄNDERT: CTkEntry zu CTkComboBox für Runde
        ctk.CTkLabel(dialog, text="Runde:").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        combo_rd = ctk.CTkComboBox(dialog, values=["PR", "H1", "H2"])
        combo_rd.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        default_round = self.settings_data.get("Runde", "PR")
        combo_rd.set(str(initial_data.get("round_number", default_round)))
        row_idx += 1

        ctk.CTkLabel(dialog, text="Rennzeit (s):").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        e_rz = ctk.CTkEntry(dialog)
        e_rz.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        rz_val = initial_data.get('renn_zeit')
        e_rz.insert(0, f"{rz_val:.3f}" if isinstance(rz_val, (float, int)) else "")
        row_idx += 1

        ctk.CTkLabel(dialog, text="Messzeit (leer=auto):").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        e_mz = ctk.CTkEntry(dialog)
        e_mz.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        ts_messung_val = initial_data.get("timestamp_messung", "")
        if ts_messung_val:
            try:
                dt_obj = datetime.datetime.fromisoformat(str(ts_messung_val).replace(" ", "T"))
                e_mz.insert(0, dt_obj.strftime("%Y-%m-%d %H:%M:%S"))
            except ValueError:
                e_mz.insert(0, str(ts_messung_val))
        else:
            e_mz.insert(0, "")
        row_idx += 1

        def save():
            sn_str = e_sn.get().strip()
            # <<< GEÄNDERT: Wert von ComboBox statt Entry holen
            rd_str = combo_rd.get().strip()
            rz_str = e_rz.get().strip().replace(",", ".")
            mz_str = e_mz.get().strip()

            if not sn_str:
                messagebox.showerror("Fehler", "Startnummer muss angegeben werden.", parent=dialog)
                return
            payload: Dict[str, Any] = {"start_nummer": sn_str}

            # <<< GEÄNDERT: Logik für Runde angepasst (keine int-Konvertierung mehr)
            if rd_str:
                payload["round_number"] = rd_str
            elif not is_edit or "round_number" not in initial_data:
                payload["round_number"] = self.settings_data.get("Runde", "PR")

            if rz_str:
                try:
                    payload["renn_zeit"] = float(rz_str)
                    if not mz_str:
                        payload["timestamp_messung"] = datetime.datetime.now().isoformat()
                except ValueError:
                    messagebox.showerror("Fehler", "Ungültige Rennzeit.", parent=dialog)
                    return
            if mz_str:
                try:
                    cleaned_mz_str = mz_str.strip().replace(" ", "T")
                    if '.' in cleaned_mz_str and len(cleaned_mz_str.split('.')[-1]) > 6:
                        parts = cleaned_mz_str.split('.')
                        cleaned_mz_str = parts[0] + '.' + parts[1][:6]
                    dt_obj = datetime.datetime.fromisoformat(cleaned_mz_str)
                    payload["timestamp_messung"] = dt_obj.isoformat()
                except ValueError:
                    messagebox.showerror("Fehler", "Ungültiges Messzeit-Format. Erwartet: YYYY-MM-DD HH:MM:SS.",
                                         parent=dialog)
                    return
            if is_edit and item_id_to_edit:
                self.update_tree_item(item_id_to_edit, payload)
            else:
                self.add_item_to_tree(payload)
            dialog.destroy()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.grid(row=row_idx, column=0, columnspan=2, pady=10, sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        save_button = ctk.CTkButton(button_frame, text="Speichern", command=save)
        save_button.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        cancel_button = ctk.CTkButton(button_frame, text="Abbrechen", command=dialog.destroy, fg_color="gray50")
        cancel_button.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        dialog.after(100, e_sn.focus)

    def on_tree_right_click(self, event: tk.Event):
        if not self.tree: return
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            self._context_menu_item_id = None
            return
        if not self.tree.selection() or item_id not in self.tree.selection(): self.tree.selection_set(item_id)
        self.tree.focus(item_id)
        self._context_menu_item_id = item_id
        self.tree_context_menu.delete(0, tk.END)
        with self.data_lock:
            item_details = self.data_items.get(item_id)
            if item_details:
                current_status = item_details.get("status")
                if current_status == STATUS_DELETED:
                    self.tree_context_menu.add_command(label="Wiederherstellen", command=self.restore_deleted_item)
                else:
                    self.tree_context_menu.add_command(label="Bearbeiten...", command=self.edit_selected_tree_item)
                    if current_status == STATUS_MODIFIED and item_details.get("original_data_snapshot"):
                        self.tree_context_menu.add_command(label="Änderungen verwerfen...",
                                                           command=self.revert_item_changes_dialog)
                    self.tree_context_menu.add_separator()
                    self.tree_context_menu.add_command(label="Löschen", command=self.delete_selected_tree_item)
        if self.tree_context_menu.index(tk.END) is not None:
            self.tree_context_menu.tk_popup(event.x_root, event.y_root)

    def on_tree_double_click(self, event: tk.Event):
        if not self.tree: return
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        can_edit = False
        with self.data_lock:
            if item_id in self.data_items and self.data_items[item_id].get("status") != STATUS_DELETED:
                can_edit = True
        if can_edit: self.open_manual_entry_dialog(item_id_to_edit=item_id)

    def _get_id_for_context_action(self) -> Optional[str]:
        item_id = self._context_menu_item_id
        if not item_id and self.tree and self.tree.selection():
            selections = self.tree.selection()
            if selections: item_id = selections[0]
        if not item_id:
            messagebox.showinfo("Info", "Kein Element ausgewählt.", parent=self)
            return None
        return item_id

    def edit_selected_tree_item(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        can_edit = False
        with self.data_lock:
            if item_id in self.data_items and self.data_items[item_id].get("status") != STATUS_DELETED:
                can_edit = True
        if can_edit:
            self.open_manual_entry_dialog(item_id_to_edit=item_id)
        else:
            messagebox.showinfo("Info", "Element nicht bearbeitbar.", parent=self)
        self._context_menu_item_id = None

    def delete_selected_tree_item(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        item_exists_and_not_deleted_logically = False
        with self.data_lock:
            if item_id in self.data_items and self.data_items[item_id].get("status") != STATUS_DELETED:
                item_exists_and_not_deleted_logically = True
        if not item_exists_and_not_deleted_logically:
            self._context_menu_item_id = None
            return

        item_removed_from_data_items_and_tree = False
        broadcast_delete_signal = False
        with self.data_lock:
            if item_id not in self.data_items or self.data_items[item_id].get("status") == STATUS_DELETED:
                self._context_menu_item_id = None
                return
            details_to_delete = self.data_items[item_id]
            if details_to_delete.get("status") == STATUS_NEW:
                del self.data_items[item_id]
                item_removed_from_data_items_and_tree = True
                broadcast_delete_signal = True
            else:
                if details_to_delete.get("data_before_delete") is None:
                    details_to_delete["data_before_delete"] = {
                        "data": copy.deepcopy(details_to_delete.get("data", {})),
                        "original_status": details_to_delete.get("status"),
                        "original_snapshot_if_modified": copy.deepcopy(details_to_delete.get("original_data_snapshot"))
                    }
                details_to_delete["status"] = STATUS_DELETED
                details_to_delete["original_data_snapshot"] = None
                self.after(0, self._update_tree_item_display, item_id)
                broadcast_delete_signal = True
        if item_removed_from_data_items_and_tree and self.tree and self.tree.exists(item_id):
            self.tree.delete(item_id)
        if broadcast_delete_signal: self.broadcast_data_update(item_id, is_delete=True)
        self._context_menu_item_id = None

    def revert_item_changes_dialog(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        show_dialog = False
        item_details_snapshot_for_dialog: Optional[Dict[str, Any]] = None
        with self.data_lock:
            if item_id not in self.data_items:
                self._context_menu_item_id = None
                return
            item_details = self.data_items[item_id]
            if item_details.get("status") == STATUS_MODIFIED and item_details.get("original_data_snapshot"):
                show_dialog = True
                item_details_snapshot_for_dialog = copy.deepcopy(item_details)
            else:
                messagebox.showinfo("Info", "Keine Änderungen zum Verwerfen.", parent=self)
        if not show_dialog or not item_details_snapshot_for_dialog:
            self._context_menu_item_id = None
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Änderungen Verwerfen?")
        dialog.geometry("600x450")
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=15, pady=15)
        start_nr = item_details_snapshot_for_dialog.get("data", {}).get('start_nummer', 'N/A')
        ctk.CTkLabel(main_frame, text=f"Änderungen für Startnr: {start_nr} verwerfen?",
                     font=ctk.CTkFont(weight="bold")).pack(pady=(0, 10))
        diff_scroll_frame = ctk.CTkScrollableFrame(main_frame, label_text="Unterschiede")
        diff_scroll_frame.pack(fill="both", expand=True, pady=5)
        diff_scroll_frame.columnconfigure(0, weight=1)
        diff_scroll_frame.columnconfigure(1, weight=2)
        diff_scroll_frame.columnconfigure(2, weight=2)
        ctk.CTkLabel(diff_scroll_frame, text="Feld", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5,
                                                                                           pady=2, sticky="w")
        ctk.CTkLabel(diff_scroll_frame, text="Ursprünglich", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1,
                                                                                                   padx=5, pady=2,
                                                                                                   sticky="w")
        ctk.CTkLabel(diff_scroll_frame, text="Aktuell Geändert", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2,
                                                                                                       padx=5, pady=2,
                                                                                                       sticky="w")
        current_row = 1
        original_data = item_details_snapshot_for_dialog.get("original_data_snapshot", {})
        current_data = item_details_snapshot_for_dialog.get("data", {})
        all_keys = sorted(list(set(original_data.keys()) | set(current_data.keys())))
        diff_found_overall = False
        ignored_keys = {"updated_at", "created_at", "timestamp_scan_ankunft", "sensor_info", "zugeordneter_scan_id",
                        "_synced_to_website"}
        for key_loop in all_keys:
            if key_loop in ignored_keys: continue
            val_orig_raw = original_data.get(key_loop)
            val_curr_raw = current_data.get(key_loop)
            is_different = False
            if isinstance(val_orig_raw, float) or isinstance(val_curr_raw, float):
                if not (val_orig_raw is None and val_curr_raw is None) and \
                        (val_orig_raw is None or val_curr_raw is None or not abs(
                            float(val_orig_raw or 0.0) - float(val_curr_raw or 0.0)) < 1e-9):
                    is_different = True
            elif str(val_orig_raw) != str(val_curr_raw):
                is_different = True
            if is_different:
                diff_found_overall = True
                val_orig_display = str(val_orig_raw if val_orig_raw is not None else "-")
                val_curr_display = str(val_curr_raw if val_curr_raw is not None else "-")
                ctk.CTkLabel(diff_scroll_frame, text=f"{key_loop}:").grid(row=current_row, column=0, padx=5, pady=1,
                                                                          sticky="w")
                ctk.CTkLabel(diff_scroll_frame, text=val_orig_display, text_color="gray50").grid(row=current_row,
                                                                                                 column=1, padx=5,
                                                                                                 pady=1, sticky="w")
                ctk.CTkLabel(diff_scroll_frame, text=val_curr_display).grid(row=current_row, column=2, padx=5, pady=1,
                                                                            sticky="w")
                current_row += 1
        if not diff_found_overall: ctk.CTkLabel(diff_scroll_frame, text="Keine relevanten Unterschiede gefunden.").grid(
            row=1, column=0, columnspan=3, pady=10)

        def confirm_revert():
            with self.data_lock:
                if item_id not in self.data_items: return
                item_to_revert = self.data_items[item_id]
                if item_to_revert.get("original_data_snapshot"):
                    item_to_revert["data"] = copy.deepcopy(item_to_revert["original_data_snapshot"])
                    item_to_revert["original_data_snapshot"] = None
                    # Revert to 'saved internally' as it's the safe 'clean' state before a web push.
                    # This prevents wrongly marking an item as web-synced.
                    item_to_revert["status"] = STATUS_SYNCED_LOCAL
                    self.after(0, self._update_tree_item_display, item_id)
                else:
                    messagebox.showinfo("Info", "Originaldaten für Revert nicht mehr vorhanden.", parent=dialog)
            self.broadcast_data_update(item_id)
            dialog.destroy()
            self._context_menu_item_id = None

        button_bar = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_bar.pack(fill="x", pady=(15, 0))
        ctk.CTkButton(button_bar, text="Änderungen Verwerfen", command=confirm_revert, fg_color="orange red").pack(
            side="left", padx=(0, 10))
        ctk.CTkButton(button_bar, text="Abbrechen", command=dialog.destroy).pack(side="left")
        self._context_menu_item_id = None

    def restore_deleted_item(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        can_restore = False
        start_nr_display = item_id
        with self.data_lock:
            if item_id not in self.data_items:
                self._context_menu_item_id = None
                return
            item_details = self.data_items[item_id]
            if item_details.get("status") == STATUS_DELETED and item_details.get("data_before_delete"):
                can_restore = True
                start_nr_display = str(item_details["data_before_delete"].get("data", {}).get('start_nummer', item_id))
            else:
                messagebox.showinfo("Info", "Element nicht wiederherstellbar.", parent=self)
        if not can_restore:
            self._context_menu_item_id = None
            return
        if messagebox.askyesno("Wiederherstellen", f"Eintrag für Startnr. '{start_nr_display}' wiederherstellen?",
                               parent=self):
            with self.data_lock:
                if item_id not in self.data_items: return
                details_to_restore = self.data_items[item_id]
                if not (details_to_restore.get("status") == STATUS_DELETED and details_to_restore.get(
                        "data_before_delete")):
                    messagebox.showinfo("Info", "Wiederherstellung nicht möglich.", parent=self)
                    self._context_menu_item_id = None
                    return
                restore_info = details_to_restore["data_before_delete"]
                details_to_restore["data"] = copy.deepcopy(restore_info["data"])
                details_to_restore["status"] = restore_info.get("original_status", STATUS_MODIFIED)
                details_to_restore["original_data_snapshot"] = copy.deepcopy(
                    restore_info.get("original_snapshot_if_modified"))
                details_to_restore["data_before_delete"] = None
                self.after(0, self._update_tree_item_display, item_id)
            self.broadcast_data_update(item_id)
        self._context_menu_item_id = None

    def push_data_internally(self):
        with self.data_lock:
            made_any_change_requiring_save = False
            items_to_include_in_version = []
            has_pending_deletions = False
            for iid, dets in self.data_items.items():
                if dets.get("status") != STATUS_DELETED:
                    item_data_copy = copy.deepcopy(dets.get("data", {}))
                    items_to_include_in_version.append({"_id_internal": iid, "_status_at_version": dets.get("status"),
                                                        "_synced_to_website_at_version": dets.get("_synced_to_website",
                                                                                                  False),
                                                        **item_data_copy})
                    if dets.get("status") in [STATUS_NEW, STATUS_MODIFIED,
                                              STATUS_COMPLETE]: made_any_change_requiring_save = True
                elif dets.get("status") == STATUS_DELETED:
                    has_pending_deletions = True
            if not made_any_change_requiring_save and not has_pending_deletions:
                messagebox.showinfo("Intern Sichern", "Keine ungesicherten Änderungen oder Löschungen.", parent=self)
                return
            self.versions.append({"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  "data_snapshot": items_to_include_in_version, "type": "internal_save"})
            version_number = len(self.versions)
            items_marked_synced_count = 0
            items_permanently_deleted_count = 0
            item_ids_to_process = list(self.data_items.keys())
            for item_id in item_ids_to_process:
                if item_id in self.data_items:
                    details = self.data_items[item_id]
                    if details.get("status") in [STATUS_NEW, STATUS_MODIFIED, STATUS_COMPLETE]:
                        details["status"] = STATUS_SYNCED_LOCAL
                        details["original_data_snapshot"] = None
                        self.after(0, self._update_tree_item_display, item_id)
                        items_marked_synced_count += 1
            ids_to_remove_permanently = [item_id for item_id in list(self.data_items.keys())
                                         if item_id in self.data_items and self.data_items[item_id].get(
                    "status") == STATUS_DELETED]
            if ids_to_remove_permanently:
                for item_id_to_remove in ids_to_remove_permanently:
                    if item_id_to_remove in self.data_items:
                        del self.data_items[item_id_to_remove]
                        items_permanently_deleted_count += 1
                        if self.tree and self.tree.exists(item_id_to_remove): self.tree.delete(item_id_to_remove)
        msg_parts = [f"Snapshot Version {version_number} erstellt."]
        if items_marked_synced_count > 0: msg_parts.append(
            f"{items_marked_synced_count} Element(e) als 'Gesichert' markiert.")
        if items_permanently_deleted_count > 0: msg_parts.append(
            f"{items_permanently_deleted_count} Element(e) endgültig entfernt.")
        messagebox.showinfo("Intern Sichern - Ergebnis", "\n".join(msg_parts), parent=self)
        self.broadcast_data_update()

    def _collect_data_for_website_push(self) -> tuple[List[Dict[str, Any]], List[str], List[str]]:
        data_for_website = []
        items_to_mark_synced_after_push = []
        items_to_delete_permanently_after_push = []
        with self.data_lock:
            for item_id, details in self.data_items.items():
                payload = copy.deepcopy(details.get("data", {}))
                payload["app_item_id"] = item_id
                start_nr = payload.get("start_nummer")
                if start_nr: payload["racer_name"] = self.racer_names_by_start_number.get(str(start_nr))

                status = details.get("status")
                if status == STATUS_DELETED:
                    # Only send delete action if it was previously synced or has a persistent ID
                    if details.get("data_before_delete") or details.get("_synced_to_website"):
                        payload["_action"] = "delete"
                        data_for_website.append(payload)
                        items_to_delete_permanently_after_push.append(item_id)
                else:
                    if not payload.get('renn_zeit'):
                        print(f"Rennzeit fehlt, überspringe: {payload}")
                        continue

                # Push any item that is not yet fully synced with the website
                if status in [STATUS_NEW, STATUS_SYNCED_LOCAL]:
                    payload["_action"] = "upsert"
                    data_for_website.append(payload)
                    items_to_mark_synced_after_push.append(item_id)
                elif status in [STATUS_MODIFIED, STATUS_COMPLETE]:
                    payload["_action"] = "changed"
                    data_for_website.append(payload)
                    items_to_mark_synced_after_push.append(item_id)

        return data_for_website, items_to_mark_synced_after_push, items_to_delete_permanently_after_push

    def initiate_push_to_website(self):
        data_to_send, ids_to_flag_synced_website, ids_to_remove_locally_after_web_delete = self._collect_data_for_website_push()
        if not data_to_send:
            messagebox.showinfo("Push to Website", "Keine Daten für Push.", parent=self)
            return
        server_response_success = True
        for p_idx, p_data in enumerate(data_to_send):
            finished = self.push_data_website(p_data)
            if not finished:
                finished = self.push_data_website(p_data)
                if not finished:
                    print(f"Error bei {p_data}")
                    server_response_success = False

        def _do_push_request():
            self.after(0, self._finalize_website_push, server_response_success, ids_to_flag_synced_website,
                       ids_to_remove_locally_after_web_delete)
        def _do_pull_request():
            self.pull_race_runs_from_website()

        threading.Thread(target=_do_push_request, daemon=True).start()
        threading.Thread(target=_do_pull_request, daemon=True).start()

    def _finalize_website_push(self, success: bool, ids_successfully_upserted_on_server: List[str],
                               ids_successfully_deleted_on_server: List[str]):
        if success:
            updated_on_website_count = 0
            deleted_on_website_and_locally_count = 0
            with self.data_lock:
                for item_id in ids_successfully_upserted_on_server:
                    if item_id in self.data_items:
                        details = self.data_items[item_id]
                        if details.get("status") == STATUS_DELETED: continue
                        details["status"] = STATUS_SYNCED
                        details["original_data_snapshot"] = None
                        details["_synced_to_website"] = True
                        self.after(0, self._update_tree_item_display, item_id)
                        updated_on_website_count += 1
                ids_actually_removed_from_gui_tree = []
                for item_id in ids_successfully_deleted_on_server:
                    if item_id in self.data_items:
                        del self.data_items[item_id]
                        ids_actually_removed_from_gui_tree.append(item_id)
                        deleted_on_website_and_locally_count += 1
            if self.tree and ids_actually_removed_from_gui_tree:
                for tree_id_to_remove in ids_actually_removed_from_gui_tree:
                    if self.tree.exists(tree_id_to_remove): self.tree.delete(tree_id_to_remove)
            messagebox.showinfo("Push zu Website",
                                f"Push erfolgreich.\n{updated_on_website_count} Upserted.\n{deleted_on_website_and_locally_count} Deleted.",
                                parent=self)
            self.broadcast_data_update()
        else:
            messagebox.showerror("Push zu Website", "Fehler beim Push.", parent=self)

    def open_pull_selection_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Pull von Website - Auswahl")
        dialog.geometry("350x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        ctk.CTkLabel(dialog, text="Was soll von der Website geladen werden?").pack(pady=10)
        pull_racers_var = tk.BooleanVar(value=True)
        pull_runs_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(dialog, text="Rennfahrer-Liste", variable=pull_racers_var).pack(pady=5, anchor="w", padx=20)
        ctk.CTkCheckBox(dialog, text="Renndurchläufe", variable=pull_runs_var).pack(pady=5, anchor="w", padx=20)

        def start_pull():
            pull_racers = pull_racers_var.get()
            pull_runs = pull_runs_var.get()
            dialog.destroy()
            if not pull_racers and not pull_runs:
                messagebox.showinfo("Pull Auswahl", "Nichts ausgewählt.",
                                    parent=self)
                return
            items_before_pull = []
            with self.data_lock:
                items_before_pull = [{"_id_internal": iid, "_status_at_version": dets.get("status"),
                                      "_synced_to_website_at_version": dets.get("_synced_to_website", False),
                                      **copy.deepcopy(dets.get("data", {}))} for iid, dets in
                                     self.data_items.items()]
            if items_before_pull or not self.data_items:
                self.versions.append({"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                      "data_snapshot": items_before_pull, "type": "pre_pull_backup"})
                print(f"Pre-Pull Backup Version {len(self.versions)} erstellt.")
            if pull_racers: self.pull_racers_from_website()
            if pull_runs: self.pull_race_runs_from_website()

        ctk.CTkButton(dialog, text="Pull Starten", command=start_pull).pack(pady=10)
        ctk.CTkButton(dialog, text="Abbrechen", command=dialog.destroy, fg_color="gray50").pack(pady=5)

    def pull_racers_from_website(self):
        api_endpoint = self.settings_data.get('API Endpoint Website', 'N/A')
        print(f"--- Pull von Racer-Daten von ({api_endpoint}) ---")

        def _do_racer_pull():
            racers_payload = self.get_data_website(api_endpoint + "racers/")
            if not racers_payload:
                return
            self.after(0, self._update_racer_data_store, racers_payload, True)

        threading.Thread(target=_do_racer_pull, daemon=True).start()

    def pull_race_runs_from_website(self):
        api_endpoint = self.settings_data.get('API Endpoint Website', 'N/A')
        print(f"--- Pull von Renndurchläufen von ({api_endpoint}) ---")

        def _do_race_run_pull():
            time.sleep(1)
            website_data_payload = self.get_data_website(api_endpoint + "raceruns/")

            if website_data_payload is None:
                self.after(0, lambda: messagebox.showerror("Pull Fehler",
                                                           "Konnte keine Renndaten von der Website abrufen.",
                                                           parent=self))
                return

            self.after(0, self._process_pulled_website_data, website_data_payload)

        threading.Thread(target=_do_race_run_pull, daemon=True).start()

    def _process_pulled_website_data(self, website_data_list: List[Dict[str, Any]]):
        if not website_data_list:
            messagebox.showinfo("Pull Renndaten", "Keine Renndaten von der Website empfangen.", parent=self)
            return
        self.data_items = {}
        with self.data_lock:
            for web_item_payload in website_data_list:
                # 'id' aus der Web-Nutzlast als eindeutigen Bezeichner verwenden
                item_id_from_web = web_item_payload.get("id")
                if not item_id_from_web:
                    print(f"Warnung: Renndaten-Eintrag von Website ohne 'id': {web_item_payload}")
                    continue

                # Treeview-IIDs sollten Strings sein
                item_id_from_web = str(item_id_from_web)

                try:
                    # 'time_in_seconds' (String) in Float für 'renn_zeit' umwandeln
                    renn_zeit_val = float(web_item_payload.get("time_in_seconds")) if web_item_payload.get(
                        "time_in_seconds") is not None else None
                except (ValueError, TypeError):
                    renn_zeit_val = None
                    print(
                        f"Warnung: Ungültiger Wert für 'time_in_seconds' in Payload: {web_item_payload.get('time_in_seconds')}")

                # Felder aus der Website-Nutzlast der lokalen Datenstruktur zuordnen
                local_data_format = {
                    "start_nummer": web_item_payload.get("racer_start_number"),
                    "round_number": web_item_payload.get("run_type"),
                    "renn_zeit": renn_zeit_val,
                    "disqualified": web_item_payload.get("disqualified"),
                    "notes": web_item_payload.get("notes"),
                    "run_type": web_item_payload.get("run_type"),
                    "updated_at": datetime.datetime.now().isoformat()
                }

                # NEU: Timestamp von der Website ('recorded_at') holen und als 'timestamp_messung' speichern
                recorded_at_str = web_item_payload.get("recorded_at")
                if recorded_at_str:
                    try:
                        # fromisoformat kann das Format inkl. Zeitzone direkt verarbeiten
                        dt_obj = datetime.datetime.fromisoformat(recorded_at_str)
                        # Im internen Format (ISO-String) speichern, was die App erwartet
                        local_data_format["timestamp_messung"] = dt_obj.isoformat()
                    except (ValueError, TypeError) as e:
                        print(f"Warnung: Ungültiges 'recorded_at'-Format von der Website: {recorded_at_str}. Fehler: {e}")


                # Schlüssel mit None-Werten entfernen, um das Überschreiben vorhandener Daten mit None zu vermeiden
                local_data_format = {k: v for k, v in local_data_format.items() if v is not None}
                local_data_format.setdefault("created_at", datetime.datetime.now().isoformat())
                self.data_items[item_id_from_web] = {"data": local_data_format,
                                                     "status": STATUS_SYNCED,
                                                     "_synced_to_website": True,
                                                     "original_data_snapshot": None,
                                                     "data_before_delete": None}

        self.refresh_treeview_display_fully()
        self.broadcast_data_update()

    def refresh_treeview_display_fully(self):
        if not self.tree or not self.winfo_exists(): return
        selected_iids = self.tree.selection()
        focused_iid = self.tree.focus()
        for i in self.tree.get_children(""): self.tree.delete(i)
        with self.data_lock:
            def get_sort_key(item_id_key: str) -> datetime.datetime:
                if item_id_key not in self.data_items: return datetime.datetime.min
                item_data = self.data_items[item_id_key].get('data', {})
                ts_str = item_data.get('timestamp_messung') or item_data.get('timestamp_scan_ankunft') or item_data.get(
                    'created_at')
                if ts_str:
                    try:
                        if isinstance(ts_str, str):
                            ts_str_cleaned = ts_str.replace("Z", "+00:00").replace(" ", "T")
                            if '.' in ts_str_cleaned:
                                base, micros = ts_str_cleaned.split('.', 1)
                                tz_marker = ""
                                if '+' in micros:
                                    tz_marker = micros[micros.find('+'):]
                                    micros = micros[:micros.find('+')]
                                elif '-' in micros and not micros.startswith(
                                        '-'):  # Ensure not negative number for time part
                                    # check if it's a timezone offset like -07:00 vs. a date like 2023-10-26
                                    if len(micros[micros.find('-'):].split(':')) == 2:  # Likely timezone
                                        tz_marker = micros[micros.find('-'):]
                                        micros = micros[:micros.find('-')]
                                micros = micros[:6]  # truncate microseconds
                                ts_str_cleaned = f"{base}.{micros}{tz_marker}" if tz_marker else f"{base}.{micros}"

                            return datetime.datetime.fromisoformat(ts_str_cleaned)
                        elif isinstance(ts_str, datetime.datetime):
                            return ts_str
                        return datetime.datetime.min
                    except ValueError:
                        return datetime.datetime.min
                return datetime.datetime.min

            sorted_item_ids = sorted(list(self.data_items.keys()), key=get_sort_key, reverse=True)
            for item_id in sorted_item_ids:
                if item_id in self.data_items:
                    item_details = self.data_items[item_id]
                    values = self._create_tree_item_values(item_id, item_details)
                    tag = item_details.get("status", "")
                    self.tree.insert("", 0, iid=item_id, values=values, tags=(tag,))
        if selected_iids:
            valid_selection = [sid for sid in selected_iids if self.tree.exists(sid)]
            if valid_selection: self.tree.selection_set(valid_selection)
        if focused_iid and self.tree.exists(focused_iid): self.tree.focus(focused_iid)

    def show_previous_versions(self):
        if not self.versions:
            messagebox.showinfo("Info", "Keine Sicherungen vorhanden.", parent=self)
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Gesicherte Versionen")
        dialog.geometry("750x550")
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="Gespeicherte Versionen", font=ctk.CTkFont(size=14, weight="bold")).pack(
            pady=(0, 10))
        listbox_frame = ctk.CTkScrollableFrame(main_frame, height=300)
        listbox_frame.pack(pady=5, padx=5, fill="both", expand=True)
        listbox_font = ctk.CTkFont(size=12)
        listbox_bg = self._get_theme_color("CTkFrame", "fg_color")
        listbox_fg = self._get_theme_color("CTkLabel", "text_color")
        listbox_select_bg = self._get_theme_color("CTkButton", "fg_color")
        listbox_select_fg = self._get_theme_color("CTkButton", "text_color")
        vlb = tk.Listbox(listbox_frame, selectmode="single", exportselection=False, font=listbox_font, relief="sunken",
                         borderwidth=1, bg=listbox_bg, fg=listbox_fg, selectbackground=listbox_select_bg,
                         selectforeground=listbox_select_fg, highlightthickness=0, activestyle="none")
        vlb.pack(fill="both", expand=True)
        for i, version_info in enumerate(reversed(self.versions)):
            version_num_display = len(self.versions) - i
            timestamp = version_info.get('timestamp', 'N/A')
            num_entries = len(version_info.get('data_snapshot', []))
            version_type_raw = version_info.get('type', 'unbekannt')
            type_display_map = {"internal_save": "Interne Sicherung", "pre_pull_backup": "Backup (Vor Website-Pull)"}
            type_display = type_display_map.get(version_type_raw, version_type_raw.replace("_", " ").title())
            vlb.insert(tk.END,
                       f"Version {version_num_display} ({timestamp}) - {num_entries} Einträge - Typ: {type_display}")
        if vlb.size() > 0: vlb.selection_set(0)

        def on_revert_to_version_selected():
            selection_indices = vlb.curselection()
            if selection_indices:
                selected_listbox_index = selection_indices[0]
                original_version_index_in_self_versions = len(self.versions) - 1 - selected_listbox_index
                version_to_load_details = self.versions[original_version_index_in_self_versions]
                version_num_display_for_msg = len(self.versions) - selected_listbox_index
                if messagebox.askyesno("Version Wiederherstellen",
                                       f"Version {version_num_display_for_msg} ({version_to_load_details['timestamp']}) wiederherstellen?",
                                       parent=dialog, icon=messagebox.WARNING):
                    self.revert_to_version(original_version_index_in_self_versions)
                    dialog.destroy()
            else:
                messagebox.showwarning("Auswahl Erforderlich", "Bitte Version auswählen.", parent=dialog)

        button_bar = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_bar.pack(pady=(10, 5), padx=5, fill="x")
        revert_button = ctk.CTkButton(button_bar, text="Ausgewählte Version Laden",
                                      command=on_revert_to_version_selected)
        revert_button.pack(side="left", padx=(0, 10), expand=True)
        cancel_button = ctk.CTkButton(button_bar, text="Abbrechen", command=dialog.destroy, fg_color="gray50")
        cancel_button.pack(side="left", expand=True)

    def revert_to_version(self, version_index: int):
        if not (0 <= version_index < len(self.versions)):
            messagebox.showerror("Fehler", f"Ungültiger Index ({version_index}).",
                                 parent=self)
            return
        version_to_load = self.versions[version_index]
        version_num_display_for_msg = len(self.versions) - version_index
        version_timestamp_for_msg = version_to_load.get('timestamp', 'N/A')
        with self.data_lock:
            self.data_items.clear()
            for item_data_from_snapshot in version_to_load.get("data_snapshot", []):
                item_id = item_data_from_snapshot.get("_id_internal") or str(uuid.uuid4())
                data_content = {k: v for k, v in item_data_from_snapshot.items() if
                                k not in ["_id_internal", "_status_at_version", "_synced_to_website_at_version"]}
                restored_status = item_data_from_snapshot.get("_status_at_version", STATUS_SYNCED_LOCAL)
                self.data_items[item_id] = {"data": data_content, "status": restored_status,
                                            "original_data_snapshot": None, "data_before_delete": None,
                                            "_synced_to_website": item_data_from_snapshot.get(
                                                "_synced_to_website_at_version", False)}
        self.refresh_treeview_display_fully()
        messagebox.showinfo("Wiederherstellung Erfolgreich",
                            f"Version {version_num_display_for_msg} ({version_timestamp_for_msg}) geladen.",
                            parent=self)
        self.broadcast_data_update()
        self.broadcast_racer_data()


if __name__ == "__main__":
    import os

    if not os.path.exists("common"): os.makedirs("common")
    if not os.path.exists("common/__init__.py"): open("common/__init__.py", "w").close()
    if not os.path.exists("common/constants.py"):
        with open("common/constants.py", "w") as f: f.write(
            "STATUS_NEW = 'new'\nSTATUS_MODIFIED = 'modified'\nSTATUS_DELETED = 'deleted'\nSTATUS_SYNCED = 'synced'\nSTATUS_COMPLETE = 'complete'\nCOLOR_STATUS_NEW_BG = '#c8e6c9'\nCOLOR_STATUS_MODIFIED_BG = '#fff9c4'\nCOLOR_STATUS_DELETED_FG = '#e57373'\nCOLOR_STATUS_COMPLETE_BG = '#bbdefb'\n")
    if not os.path.exists("common/data_models.py"):
        with open("common/data_models.py", "w") as f: f.write(
            "import datetime\nimport uuid\nfrom typing import Optional, Any, Dict\n\nclass ScanLogEntry:\n    def __init__(self, start_nummer: str, status: str, scan_id: Optional[str] = None, timestamp_scan_lokal: Optional[datetime.datetime] = None, error_message: Optional[str] = None):\n        self.scan_id = scan_id or str(uuid.uuid4())\n        self.timestamp_scan_lokal = timestamp_scan_lokal or datetime.datetime.now()\n        self.start_nummer = start_nummer self.status = status self.error_message = error_message\n\nclass MainDataEntry(dict): pass\nclass DisplayableMainData(dict): pass\n")
    app = MainApp()
    app.mainloop()