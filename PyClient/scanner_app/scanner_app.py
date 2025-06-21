# --- START OF FILE scanner_app.py ---

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import uuid
import datetime
import threading
from typing import Dict, Any, Optional, List
import socket
import queue
import time
from pynput import keyboard

HOST = '127.0.0.1'
PORT = 65432
received_message_queue = queue.Queue()
message_to_server_queue = queue.Queue()


# --- NEUER, STABILER NETZWERK-CODE ---
def send_message_to_server_func(values: List[Any]):
    message_to_server_queue.put(values)


def receive_message_from_server_func(s: socket.socket):
    buffer = ""
    s.settimeout(1.0)
    while getattr(threading.current_thread(), "do_run", True):
        try:
            data_chunk = s.recv(8192)
            if not data_chunk:
                print("Verbindung vom Server geschlossen.")
                received_message_queue.put(("CONNECTION_LOST", None))
                return
            buffer += data_chunk.decode('utf-8')
            while "$END$" in buffer:
                message, buffer = buffer.split("$END$", 1)
                if message:
                    received_message_queue.put(("MESSAGE", message))
        except socket.timeout:
            continue
        except (socket.error, ConnectionResetError) as e:
            print(f"Socket-Fehler im Empfänger: {e}")
            received_message_queue.put(("CONNECTION_LOST", None))
            return
        except Exception as e:
            print(f"Unerwarteter Fehler im Empfänger: {e}")
            received_message_queue.put(("CONNECTION_LOST", None))
            return


def client_communication_thread_func(app_instance):
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"Versuche Verbindung zu Server {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            print(f"Verbunden mit Server {HOST}:{PORT}")
            app_instance.after(0, app_instance.update_connection_status, True)

            receiver_thread = threading.Thread(target=receive_message_from_server_func, args=(s,), daemon=True)
            receiver_thread.do_run = True
            receiver_thread.start()

            while receiver_thread.is_alive():
                try:
                    msg_list_to_send = message_to_server_queue.get(timeout=0.2)
                    text_to_server = "$#".join(map(str, msg_list_to_send)) + "$#$END$"
                    s.sendall(text_to_server.encode('utf-8'))
                except queue.Empty:
                    continue
                except socket.error as e:
                    print(f"Socket-Fehler beim Senden: {e}")
                    break

            receiver_thread.do_run = False
            s.close()
            print("Verbindung geschlossen. Versuche in 5 Sekunden erneut...")
            app_instance.after(0, app_instance.update_connection_status, False)
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"Verbindungsproblem: {e}. Warte 5s...")
            app_instance.after(0, app_instance.update_connection_status, False)
        time.sleep(5)


def process_server_messages_func(app_instance):
    while True:
        try:
            msg_type, payload = received_message_queue.get()
            if msg_type == "CONNECTION_LOST":
                app_instance.after(0, app_instance.update_connection_status, False)
                continue

            app_instance.after(0, app_instance.update_connection_status, True)

            if msg_type == "MESSAGE":
                if payload.startswith("ALL_DATA:"):
                    app_instance.after(0, app_instance.process_all_data_from_server, payload[len("ALL_DATA:"):])
                elif payload == "ALL_DATA_EMPTY":
                    app_instance.after(0, app_instance.process_all_data_from_server, "")
                elif payload.startswith("UPDATE_DATA:"):
                    app_instance.after(0, app_instance.process_update_data_from_server, payload[len("UPDATE_DATA:"):])
                elif payload.startswith("DELETE_DATA:"):
                    app_instance.after(0, app_instance.process_delete_data_from_server, payload[len("DELETE_DATA:"):])
                elif payload.startswith("RACER_DATA_UPDATE:"):
                    app_instance.after(0, app_instance.process_racer_data_from_server,
                                       payload[len("RACER_DATA_UPDATE:"):])
                elif payload == "RACER_DATA_EMPTY":
                    app_instance.after(0, app_instance.process_racer_data_from_server, "")
        except Exception as e:
            print(f"Fehler in process_server_messages_func: {e}")


# --- RESTLICHER CODE BLEIBT WIE ZUVOR ---
try:
    from common.data_models import ScanLogEntry
except ImportError:
    class ScanLogEntry:
        def __init__(self, start_nummer: str, status: str, scan_id: Optional[str] = None,
                     timestamp_scan_lokal: Optional[datetime.datetime] = None):
            self.scan_id = scan_id or str(uuid.uuid4())
            self.timestamp_scan_lokal = timestamp_scan_lokal or datetime.datetime.now()
            self.start_nummer = start_nummer
            self.status = status

SCAN_LOG_STATUS_PENDING = "Lokal Erfasst"
SCAN_LOG_STATUS_ERROR = "Fehler (Lokal)"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def get_scan():
    INPUT_TIMEOUT = 0.05
    data_queue = queue.Queue()
    state = {'buffer': [], 'last_key_time': 0}
    listener_ref = [None]

    def on_press(key):
        current_time = time.time()
        if current_time - state['last_key_time'] > INPUT_TIMEOUT: state['buffer'] = []
        state['last_key_time'] = current_time
        try:
            if key.char: state['buffer'].append(key.char)
        except AttributeError:
            if key == keyboard.Key.enter and state['buffer']:
                data_queue.put("".join(state['buffer']))
                if listener_ref[0]: listener_ref[0].stop()

    listener = keyboard.Listener(on_press=on_press)
    listener_ref[0] = listener
    listener.start()
    result = data_queue.get()
    listener.join()
    return result


def read_from_scanner_device():
    while True:
        data = get_scan()
        if data.isdigit(): return data


class ScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scanner-App")
        self.geometry("1100x700")

        self.scan_log_entries: List[ScanLogEntry] = []
        self._scan_log_lock = threading.Lock()
        self.all_race_data_dict: Dict[str, Dict[str, Any]] = {}
        self._all_race_data_lock = threading.Lock()
        self.racer_data_by_start_number: Dict[str, Dict[str, str]] = {}
        self._racer_data_lock = threading.Lock()

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.top_bar = ctk.CTkFrame(self.main_container, height=40)
        self.top_bar.pack(fill="x", pady=(0, 5))
        self.status_label = ctk.CTkLabel(self.top_bar, text="Verbinde...", text_color="orange")
        self.status_label.pack(side="left", padx=10)

        self.tab_view = ctk.CTkTabview(self.main_container)
        self.tab_view.pack(fill="both", expand=True)
        self.scan_log_tab = self.tab_view.add("Scan-Protokoll")
        self.all_data_tab = self.tab_view.add("Alle Renndaten")

        self._setup_scan_log_tab()
        self._setup_all_data_tab()

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        threading.Thread(target=client_communication_thread_func, args=(self,), daemon=True).start()
        threading.Thread(target=process_server_messages_func, args=(self,), daemon=True).start()
        threading.Thread(target=self._real_scan_thread_target, daemon=True).start()

    def update_connection_status(self, is_connected: bool):
        if is_connected:
            self.status_label.configure(text="Verbunden", text_color="green")
        else:
            self.status_label.configure(text="Verbindung verloren...", text_color="red")

    def _get_theme_color(self, widget_name: str, color_type: str, default_light: str = "#FFFFFF",
                         default_dark: str = "#000000") -> str:
        try:
            val = ctk.ThemeManager.theme[widget_name][color_type]
            is_dark = ctk.get_appearance_mode().lower() == "dark"
            return str(val[1] if is_dark else val[0]) if isinstance(val, (list, tuple)) else str(val)
        except Exception:
            is_dark_fallback = ctk.get_appearance_mode().lower() == "dark"
            return default_dark if is_dark_fallback else default_light

    def _setup_scan_log_tab(self):
        input_frame = ctk.CTkFrame(self.scan_log_tab, height=80)
        input_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(input_frame, text="Startnummer:", font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        self.scan_input_entry = ctk.CTkEntry(input_frame, placeholder_text="Scannen/Eingeben",
                                             font=ctk.CTkFont(size=14))
        self.scan_input_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.scan_input_entry.bind("<Return>", lambda e: self._simulate_scan_from_input())
        self.manual_scan_button = ctk.CTkButton(input_frame, text="Erfassen", command=self._simulate_scan_from_input)
        self.manual_scan_button.pack(side="left", padx=10)

        tree_container = ctk.CTkFrame(self.scan_log_tab)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.scan_log_tree_columns = ("timestamp", "start_nummer", "racer_name_scan", "soapbox_class_scan",
                                      "scan_id_short", "status_scan")
        self.scan_log_tree = ttk.Treeview(tree_container, columns=self.scan_log_tree_columns, show="headings")
        vsb = ctk.CTkScrollbar(tree_container, command=self.scan_log_tree.yview);
        vsb.pack(side="right", fill="y")
        self.scan_log_tree.configure(yscrollcommand=vsb.set)
        self.scan_log_tree.pack(side="left", fill="both", expand=True)

        for col, name in [("timestamp", "Scan-Zeit"), ("start_nummer", "Startnr."), ("racer_name_scan", "Name"),
                          ("soapbox_class_scan", "Kistenklasse"), ("scan_id_short", "Scan ID"),
                          ("status_scan", "Status")]:
            self.scan_log_tree.heading(col, text=name)

        for col, w in [("timestamp", 160), ("start_nummer", 80), ("racer_name_scan", 180), ("soapbox_class_scan", 150),
                       ("scan_id_short", 100), ("status_scan", 120)]:
            self.scan_log_tree.column(col, width=w, stretch=(col in ["racer_name_scan", "soapbox_class_scan"]))

        self._apply_treeview_styling(self.scan_log_tree)

    def _setup_all_data_tab(self):
        tree_container = ctk.CTkFrame(self.all_data_tab)
        tree_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.all_data_tree_columns = ("start_nummer", "racer_name_all", "soapbox_class_all", "round_number_main",
                                      "renn_zeit", "mess_zeit_combined")
        self.all_data_tree = ttk.Treeview(tree_container, columns=self.all_data_tree_columns, show="headings")
        vsb = ctk.CTkScrollbar(tree_container, command=self.all_data_tree.yview);
        vsb.pack(side="right", fill="y")
        self.all_data_tree.configure(yscrollcommand=vsb.set)
        self.all_data_tree.pack(side="left", fill="both", expand=True)

        for col, name in [("start_nummer", "Startnr."), ("racer_name_all", "Name"),
                          ("soapbox_class_all", "Kistenklasse"), ("round_number_main", "Runde"),
                          ("renn_zeit", "Rennzeit"), ("mess_zeit_combined", "Messzeit")]:
            self.all_data_tree.heading(col, text=name)

        for col, w, stretch, anchor in [("start_nummer", 80, False, tk.W), ("racer_name_all", 180, True, tk.W),
                                        ("soapbox_class_all", 150, True, tk.W),
                                        ("round_number_main", 80, False, tk.CENTER), ("renn_zeit", 100, False, tk.E),
                                        ("mess_zeit_combined", 180, False, tk.W)]:
            self.all_data_tree.column(col, width=w, stretch=stretch, anchor=anchor)

        self._apply_treeview_styling(self.all_data_tree)

    def _apply_treeview_styling(self, tree: ttk.Treeview):
        style = ttk.Style(self)
        style.theme_use("default")
        bg_color = self._get_theme_color("CTkFrame", "fg_color")
        text_color = self._get_theme_color("CTkLabel", "text_color")
        selected_color = self._get_theme_color("CTkButton", "fg_color")
        style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, rowheight=28,
                        font=ctk.CTkFont(size=12))
        style.map("Treeview", background=[('selected', selected_color)])
        style.configure("Treeview.Heading", font=ctk.CTkFont(size=13, weight="bold"))

    def _real_scan_thread_target(self):
        while True:
            scanned_data = read_from_scanner_device()
            if scanned_data:
                self.after(0, self._add_scan_to_log_locally, scanned_data)

    def _simulate_scan_from_input(self):
        start_nummer = self.scan_input_entry.get().strip()
        if start_nummer:
            self._add_scan_to_log_locally(start_nummer)
            self.scan_input_entry.delete(0, tk.END)
            self.scan_input_entry.focus()

    def _add_scan_to_log_locally(self, start_nummer: str):
        new_entry = ScanLogEntry(start_nummer=start_nummer, status=SCAN_LOG_STATUS_PENDING)
        with self._scan_log_lock:
            self.scan_log_entries.insert(0, new_entry)
        values_to_send = [new_entry.timestamp_scan_lokal.strftime("%H:%M:%S (%d.%m)"), new_entry.start_nummer,
                          new_entry.scan_id]
        send_message_to_server_func(values_to_send)
        self._refresh_scan_log_treeview()

    def _refresh_scan_log_treeview(self):
        if not self.scan_log_tree or not self.scan_log_tree.winfo_exists(): return
        self.scan_log_tree.delete(*self.scan_log_tree.get_children())
        with self._scan_log_lock, self._racer_data_lock:
            for entry in self.scan_log_entries:
                racer_info = self.racer_data_by_start_number.get(entry.start_nummer, {'name': '-', 'class': '-'})
                values = (
                    entry.timestamp_scan_lokal.strftime("%H:%M:%S (%d.%m)"), entry.start_nummer,
                    racer_info['name'], racer_info['class'], entry.scan_id[:8], entry.status
                )
                self.scan_log_tree.insert("", "end", iid=entry.scan_id, values=values)

    def _sort_and_refresh_all_data_treeview(self, highlight_item_id: Optional[str] = None):
        if not self.all_data_tree or not self.all_data_tree.winfo_exists(): return
        self.all_data_tree.delete(*self.all_data_tree.get_children())
        with self._all_race_data_lock:
            def get_sort_key(item_id):
                time_str = self.all_race_data_dict.get(item_id, {}).get("mess_zeit_combined", "")
                try:
                    return datetime.datetime.strptime(time_str, "%H:%M:%S (%d.%m.%Y)")
                except (ValueError, TypeError):
                    return datetime.datetime.min

            sorted_ids = sorted(self.all_race_data_dict.keys(), key=get_sort_key, reverse=True)
            for item_id in sorted_ids:
                item_data = self.all_race_data_dict[item_id]
                values = (
                    item_data.get("start_nummer", "-"), item_data.get("racer_name", "-"),
                    item_data.get("soapbox_class", "-"), item_data.get("round_number_main", "-"),
                    item_data.get("renn_zeit", "-"), item_data.get("mess_zeit_combined", "-")
                )
                self.all_data_tree.insert("", "end", iid=item_id, values=values)
        if highlight_item_id and self.all_data_tree.exists(highlight_item_id):
            self.all_data_tree.selection_set(highlight_item_id)
            self.all_data_tree.see(highlight_item_id)

    def process_all_data_from_server(self, data_payload: str):
        new_data_dict = {}
        if data_payload:
            for item_str in data_payload.split('|'):
                if not item_str: continue
                parts = item_str.split('$#')
                if len(parts) >= 7:
                    item_id, start_nr, name, s_class, round_nr, run_time, ts = parts[:7]
                    new_data_dict[item_id] = {"start_nummer": start_nr, "racer_name": name, "soapbox_class": s_class,
                                              "round_number_main": round_nr, "renn_zeit": run_time,
                                              "mess_zeit_combined": ts}
        with self._all_race_data_lock:
            self.all_race_data_dict = new_data_dict
        self._sort_and_refresh_all_data_treeview()

    def process_update_data_from_server(self, item_payload: str):
        if not item_payload: return
        parts = item_payload.split('$#')
        if len(parts) >= 7:
            item_id, start_nr, name, s_class, round_nr, run_time, ts = parts[:7]
            updated_data = {"start_nummer": start_nr, "racer_name": name, "soapbox_class": s_class,
                            "round_number_main": round_nr, "renn_zeit": run_time, "mess_zeit_combined": ts}
            with self._all_race_data_lock:
                self.all_race_data_dict[item_id] = updated_data
            self._sort_and_refresh_all_data_treeview(highlight_item_id=item_id)

    def process_delete_data_from_server(self, item_id_to_delete: str):
        item_id = item_id_to_delete.strip()
        if item_id:
            with self._all_race_data_lock:
                if item_id in self.all_race_data_dict: del self.all_race_data_dict[item_id]
            self._sort_and_refresh_all_data_treeview()

    def process_racer_data_from_server(self, racer_data_payload: str):
        new_racer_data = {}
        if racer_data_payload:
            for pair_str in racer_data_payload.split('|'):
                if not pair_str: continue
                try:
                    start_nr, name, s_class = pair_str.split(':', 2)
                    new_racer_data[start_nr] = {'name': name, 'class': s_class}
                except ValueError:
                    try:
                        start_nr, name = pair_str.split(':', 1)
                        new_racer_data[start_nr] = {'name': name, 'class': 'N/A'}
                    except ValueError:
                        pass
        with self._racer_data_lock:
            self.racer_data_by_start_number = new_racer_data
        self._refresh_scan_log_treeview()
        self._sort_and_refresh_all_data_treeview()


if __name__ == "__main__":
    app = ScannerApp()
    app.mainloop()