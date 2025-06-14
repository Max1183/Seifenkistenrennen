import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import uuid
import datetime
import copy
import requests
import time
from typing import Dict, Any, Optional, List
import threading
import queue
import socket
import json
import os
import serial
import serial.tools.list_ports

HOST = '0.0.0.0'
PORT = 65432
SETTINGS_FILE = "app_settings.json"
VERSIONS_FILE = "versions.json"


# Die Hilfsfunktionen (handle_client, send_to_client_from_queue, connect, message_receive)
# bleiben unverändert und werden hier der Vollständigkeit halber eingefügt.
def handle_client(conn: socket.socket, addr: Any, app_instance: 'MainApp'):
    print(f"Verbunden mit {addr}")

    client_send_queue: queue.Queue[Optional[str]] = queue.Queue()
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
                message_receive(decoded_data)
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
            client_send_queue.put(None)
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
        except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
            print(f"Send thread: Socket-Fehler beim Senden an {peer_name}: {e}")
            break
        except Exception as e:
            print(f"Error in send_to_client_from_queue for {peer_name}: {e}")
            break


def connect(app_instance: 'MainApp'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((HOST, PORT))
        except OSError as e:
            print(f"FATAL ERROR: Could not bind to port {PORT}. Is another instance running? Error: {e}")
            if MainApp._instance:
                MainApp._instance.after(100, lambda: messagebox.showerror("Server Fehler",
                                                                          f"Konnte Server auf Port {PORT} nicht starten. Läuft bereits eine andere Instanz?"))
            return

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


def message_receive(data: str):
    data_list = data.split("$#")
    p: Dict[str, Any] = {}

    if len(data_list) < 4:
        print(f"Error: Received data not in expected format: {data}")
        return

    timestamp_str_from_scanner = data_list[0]

    try:
        time_part_str, date_part_str_with_paren = timestamp_str_from_scanner.split(" (")
        date_part_str = date_part_str_with_paren[:-1]
        day, month = map(int, date_part_str.split('.'))
        hour, minute, second = map(int, time_part_str.split(':'))
        current_year = datetime.datetime.now().year
        scanner_dt_object = datetime.datetime(current_year, month, day, hour, minute, second)
        p["timestamp_messung"] = scanner_dt_object.isoformat()
    except (ValueError, IndexError) as e:
        print(f"Error parsing scanner timestamp: '{timestamp_str_from_scanner}'. Error: {e}. Using current time.")
        p["timestamp_messung"] = datetime.datetime.now().isoformat()

    try:
        p["start_nummer"] = data_list[1]
    except ValueError:
        print(f"Error: Invalid start_nummer from client: {data_list[1]}")
        return

    p["scan_id"] = data_list[2]
    p["zugeordneter_scan_id"] = p["scan_id"]

    if MainApp._instance and "Runde" in MainApp._instance.settings_data:
        p["round_number"] = MainApp._instance.settings_data["Runde"]
    else:
        p["round_number"] = "PR"

    if MainApp._instance:
        data_to_add = p.copy()
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
    print("FEHLER: common-Dateien nicht gefunden.")
    STATUS_NEW, STATUS_MODIFIED, STATUS_DELETED, STATUS_SYNCED, STATUS_SYNCED_LOCAL, STATUS_COMPLETE = "new", "modified", "deleted", "synced", 'saved internally', "complete"
    COLOR_STATUS_NEW_BG, COLOR_STATUS_MODIFIED_BG, COLOR_STATUS_DELETED_FG, COLOR_STATUS_COMPLETE_BG, COLOR_STATUS_SYNCED_LOCAL_BG = "lightgreen", "lightyellow", "red", "lightblue", "lightgrey"
    ROUND_NAMES = ["PR", "H1", "H2"]

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class MergeView(ctk.CTkToplevel):
    def __init__(self, parent, local_data: Dict[str, Dict], remote_data: Dict[str, Dict], source_name: str,
                 callback_on_finish):
        super().__init__(parent)
        self.title(f"Datenabgleich: Lokale Daten vs. {source_name}")
        self.geometry("1200x700")
        self.transient(parent)
        self.grab_set()

        self.local_data = local_data
        self.remote_data = remote_data
        self.callback_on_finish = callback_on_finish
        self.source_name = source_name

        self.merge_items: Dict[str, Dict] = {}
        self.resolutions: Dict[str, str] = {}  # item_id -> 'local', 'remote', or 'discard'

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=3)
        self.grid_rowconfigure(1, weight=1)

        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left_frame, text="Betroffene Einträge", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0,
                                                                                                            column=0,
                                                                                                            pady=5,
                                                                                                            padx=5)
        self.item_listbox = tk.Listbox(left_frame, selectmode="single", font=("Segoe UI", 12), borderwidth=0,
                                       highlightthickness=0)
        self.item_listbox.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.item_listbox.bind("<<ListboxSelect>>", self._on_item_selected)

        self.local_frame = ctk.CTkFrame(self)
        self.local_frame.grid(row=1, column=1, padx=(0, 5), pady=(0, 10), sticky="nsew")
        ctk.CTkLabel(self, text="Lokale Version", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1,
                                                                                                 pady=(10, 0))
        self.local_details_frame = ctk.CTkFrame(self.local_frame, fg_color="transparent")
        self.local_details_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.remote_frame = ctk.CTkFrame(self)
        self.remote_frame.grid(row=1, column=2, padx=(5, 10), pady=(0, 10), sticky="nsew")
        ctk.CTkLabel(self, text=f"Version von {source_name}", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0,
                                                                                                             column=2,
                                                                                                             pady=(10,
                                                                                                                   0))
        self.remote_details_frame = ctk.CTkFrame(self.remote_frame, fg_color="transparent")
        self.remote_details_frame.pack(padx=10, pady=10, fill="both", expand=True)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")
        button_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.btn_keep_local = ctk.CTkButton(button_frame, text="✅ Lokale Version Behalten", state="disabled",
                                            command=lambda: self._resolve_conflict('local'))
        self.btn_keep_local.grid(row=0, column=0, padx=5, pady=5)

        self.btn_keep_remote = ctk.CTkButton(button_frame, text=f"✅ {source_name}-Version Nutzen", state="disabled",
                                             command=lambda: self._resolve_conflict('remote'))
        self.btn_keep_remote.grid(row=0, column=1, padx=5, pady=5)

        self.btn_discard = ctk.CTkButton(button_frame, text="🗑️ Eintrag Verwerfen", state="disabled",
                                         fg_color="#B80000", hover_color="#8F0000",
                                         command=lambda: self._resolve_conflict('discard'))
        self.btn_discard.grid(row=0, column=2, padx=5, pady=5)

        self.btn_finish = ctk.CTkButton(button_frame, text="Merge Abschließen & Anwenden", fg_color="darkgreen",
                                        command=self._apply_merge)
        self.btn_finish.grid(row=0, column=3, padx=5, pady=5)

        self.btn_cancel = ctk.CTkButton(button_frame, text="Abbrechen", fg_color="gray50", command=self.destroy)
        self.btn_cancel.grid(row=0, column=4, padx=5, pady=5)

        self._prepare_merge_data()
        self._on_item_selected()  # To set initial button states

    def _prepare_merge_data(self):
        all_ids = set(self.local_data.keys()) | set(self.remote_data.keys())
        jump_over_ids = []
        for item_id in sorted(list(all_ids)):
            if item_id in jump_over_ids:
                continue
            is_local = item_id in self.local_data
            is_remote = item_id in self.remote_data
            entry = {'local': self.local_data.get(item_id), 'remote': self.remote_data.get(item_id)}
            if is_local and not is_remote:
                entry['status'] = 'local_only'
                self.resolutions[item_id] = 'local'
                for key, value in self.remote_data.items():
                    value = value['data']
                    if value.get('renn_zeit', None) == entry['local']['data'].get('renn_zeit', None) and value['start_nummer'] == entry['local']['data']['start_nummer'] and value['timestamp_messung'] == entry['local']['data']['timestamp_messung'] and value['round_number'] == entry['local']['data']['round_number']:
                        if "Website" in self.source_name:
                            self.resolutions[item_id] = 'remote'
                        else:
                            self.resolutions[item_id] = 'local'
                        entry['status'] = 'identical'
                        entry["remote"] = self.remote_data.get(key)
                        jump_over_ids.append(key)

            elif not is_local and is_remote:
                entry['status'] = 'remote_only'
                self.resolutions[item_id] = 'remote'
                for key, value in self.local_data.items():
                    value = value['data']
                    if value.get('renn_zeit', None) == entry['remote']['data'].get('renn_zeit', None) and value['start_nummer'] == entry['remote']['data']['start_nummer'] and value['timestamp_messung'] == entry['remote']['data']['timestamp_messung'] and value['round_number'] == entry['remote']['data']['round_number']:
                        if "Website" in self.source_name:
                            self.resolutions[item_id] = 'remote'
                        else:
                            self.resolutions[item_id] = 'local'
                        entry['status'] = 'identical'
                        entry["local"] = self.local_data.get(key)
                        jump_over_ids.append(key)

            else:
                # Compare content, ignore timestamps and other metadata
                local_data_for_compare = entry['local']['data'].copy()
                local_data_for_compare.pop('updated_at', None)
                local_data_for_compare.pop('timestamp_messung', None)
                local_data_for_compare.pop('disqualified', None)
                local_data_for_compare.pop('notes', None)

                remote_data_for_compare = entry['remote']['data'].copy()
                remote_data_for_compare.pop('updated_at', None)
                remote_data_for_compare.pop('timestamp_messung', None)
                remote_data_for_compare.pop('disqualified', None)
                remote_data_for_compare.pop('notes', None)
                # Normalize empty values for better comparison
                if not remote_data_for_compare.get('renn_zeit'): remote_data_for_compare.pop('renn_zeit', None)
                if not local_data_for_compare.get('renn_zeit'): local_data_for_compare.pop('renn_zeit', None)

                local_data_str = json.dumps(local_data_for_compare, sort_keys=True, default=str)
                remote_data_str = json.dumps(remote_data_for_compare, sort_keys=True, default=str)
                print("lokal"+ local_data_str)
                print("Remote: " + remote_data_str)
                if local_data_str == remote_data_str:
                    entry['status'] = 'identical'
                    if "Website" in self.source_name:
                        self.resolutions[item_id] = 'remote'
                    else:
                        self.resolutions[item_id] = 'local'
                else:
                    entry['status'] = 'conflict'

            self.merge_items[item_id] = entry
        self._refresh_listbox()

    def _refresh_listbox(self):
        current_selection_index = self.item_listbox.curselection()

        self.item_listbox.delete(0, tk.END)
        status_map = {'conflict': ("[Konflikt]", "#FF8C00"), 'local_only': ("[Nur Lokal]", "#4682B4"),
                      'remote_only': ("[Nur Quelle]", "#32CD32"), 'identical': ("[Identisch]", "gray")}

        for item_id, details in self.merge_items.items():
            status_text, color = status_map.get(details['status'], ("[Unbekannt]", "white"))
            item_data = details['local'] or details['remote']
            print(item_data)
            sn = item_data['data'].get('start_nummer', 'N/A')
            rn = item_data['data'].get('round_number', 'N/A')

            resolution = self.resolutions.get(item_id)
            prefix = ""
            if resolution == 'local':
                prefix = "✅ Lokal → "
            elif resolution == 'remote':
                prefix = f"✅ Quelle → "
            elif resolution == 'discard':
                prefix = "❌ Verworfen → "

            display_text = f"{prefix}{status_text} SN:{sn} RD:{rn}"
            self.item_listbox.insert(tk.END, display_text)
            if resolution == 'discard':
                self.item_listbox.itemconfig(tk.END, {'fg': 'gray50'})
            else:
                self.item_listbox.itemconfig(tk.END, {'fg': color})

        if current_selection_index:
            try:
                self.item_listbox.selection_set(current_selection_index[0])
                self.item_listbox.see(current_selection_index[0])
            except tk.TclError:
                pass  # Listbox might be empty now

    def _on_item_selected(self, event=None):
        selection_indices = self.item_listbox.curselection()
        if not selection_indices:
            self.btn_keep_local.configure(state="disabled")
            self.btn_keep_remote.configure(state="disabled")
            self.btn_discard.configure(state="disabled")
            return

        selected_index = selection_indices[0]
        item_id = list(self.merge_items.keys())[selected_index]
        item_details = self.merge_items[item_id]

        for widget in self.local_details_frame.winfo_children(): widget.destroy()
        for widget in self.remote_details_frame.winfo_children(): widget.destroy()

        self._display_item_details(self.local_details_frame, item_details.get('local'), item_details.get('remote'))
        self._display_item_details(self.remote_details_frame, item_details.get('remote'), item_details.get('local'))

        self.btn_discard.configure(state="normal")
        if item_details['status'] == 'conflict':
            self.btn_keep_local.configure(state="normal")
            self.btn_keep_remote.configure(state="normal")
        else:
            self.btn_keep_local.configure(state="disabled")
            self.btn_keep_remote.configure(state="disabled")

    def _display_item_details(self, parent_frame, primary_data, secondary_data):
        if not primary_data:
            ctk.CTkLabel(parent_frame, text="Eintrag nicht vorhanden", text_color="gray").pack()
            return
        data = primary_data.get('data', {})
        display_keys = ['start_nummer', 'round_number', 'renn_zeit', 'timestamp_messung']
        row = 0
        for key in display_keys:
            val = data.get(key)
            val_str = str(val if val is not None else "-")
            highlight_color = None
            if secondary_data:
                sec_val = secondary_data.get('data', {}).get(key)
                # For comparison, ignore metadata that always differs
                if key not in ['updated_at', 'timestamp_messung']:
                    if str(val) != str(sec_val):
                        highlight_color = ("#FFDDC1", "#5B3E2D")
                else:
                    # Just show that timestamp is different without highlighting
                    if str(val) != str(sec_val):
                        pass

            ctk.CTkLabel(parent_frame, text=f"{key}:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0,
                                                                                             sticky="w", padx=5, pady=2)
            lbl_val = ctk.CTkLabel(parent_frame, text=val_str, wraplength=250, fg_color=highlight_color)
            lbl_val.grid(row=row, column=1, sticky="w", padx=5, pady=2)
            row += 1

    def _resolve_conflict(self, choice: str):
        selection_indices = self.item_listbox.curselection()
        if not selection_indices: return
        selected_index = selection_indices[0]
        item_id = list(self.merge_items.keys())[selected_index]
        self.resolutions[item_id] = choice
        self._refresh_listbox()

    def _apply_merge(self):
        final_data = {}
        for item_id, details in self.merge_items.items():
            resolution = self.resolutions.get(item_id)

            if resolution == 'discard':
                continue

            chosen_details = None
            if resolution == 'local' and details['local']:
                chosen_details = copy.deepcopy(details['local'])
            elif resolution == 'remote' and details['remote']:
                chosen_details = copy.deepcopy(details['remote'])

            if chosen_details:
                # Set sync status based on the chosen source
                if "Website" in self.source_name:
                    if resolution == 'remote':
                        chosen_details['_synced_to_website'] = True
                        chosen_details['status'] = STATUS_SYNCED
                    else:  # 'local' was chosen
                        chosen_details['_synced_to_website'] = False
                        # If content is identical, keep SYNCED status, else MODIFIED
                        if self.merge_items[item_id]['status'] != 'identical':
                            chosen_details['status'] = STATUS_MODIFIED
                else:  # Source is a Snapshot
                    # After merging from a snapshot, all items are considered locally saved but not synced to website
                    chosen_details['_synced_to_website'] = False
                    chosen_details['status'] = STATUS_SYNCED_LOCAL

                final_data[item_id] = chosen_details

        if self.callback_on_finish:
            self.callback_on_finish(final_data)
        self.destroy()

class MainApp(ctk.CTk):
    _instance: Optional['MainApp'] = None

    def __init__(self):
        super().__init__()
        self.headers = None
        self.tree_columns = None
        MainApp._instance = self
        self.title("Main App")
        self.geometry("1200x800")
        self.data_items: Dict[str, Dict[str, Any]] = {}
        self.data_lock = threading.RLock()
        self._context_menu_item_id: Optional[str] = None
        self.settings_data: Dict[str, Any] = {
            "Runde": "PR", "Arduino Port": "Keiner", "Server Adresse (für API)": "localhost",
            "API Endpoint Website": "http://localhost:8000/api/", "username": "Josua", "password": "hallo1234"
        }
        self.load_settings()
        self.setting_widgets: Dict[str, ctk.CTkBaseClass] = {}
        self.versions: List[Dict[str, Any]] = []
        self.load_versions()
        self.clients: Dict[Any, queue.Queue[Optional[str]]] = {}
        self.client_management_lock = threading.Lock()
        self.racers: List[Dict[str, Any]] = []
        self.racer_names_by_start_number: Dict[str, str] = {}

        self.sort_column = "timestamp_combined"
        self.sort_reverse = True

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.top_button_frame = ctk.CTkFrame(self.main_container, height=60)
        self.top_button_frame.pack(fill="x", pady=(0, 10))

        # Buttons with threaded commands
        self.push_button = ctk.CTkButton(self.top_button_frame, text="Snapshot Erstellen",
                                         command=lambda: self.button_threads(self.create_internal_snapshot))
        self.push_button.pack(side="left", padx=10, pady=5)

        self.versions_button = ctk.CTkButton(self.top_button_frame, text="Vorige Snapshots",
                                             command=lambda: self.button_threads(self.show_previous_versions))
        self.versions_button.pack(side="left", padx=5, pady=5)

        self.push_to_website_button = ctk.CTkButton(self.top_button_frame, text="Push to Website",
                                                    command=lambda: self.button_threads(self.initiate_push_to_website),
                                                    fg_color="red", state="disabled")
        self.push_to_website_button.pack(side="left", padx=10, pady=5)

        self.force_push_button = ctk.CTkButton(self.top_button_frame, text="Zwangspush",
                                               command=lambda: self.button_threads(self.initiate_force_push_to_website),
                                               fg_color="#B80000", hover_color="#8F0000", state="disabled")
        self.force_push_button.pack(side="left", padx=(0, 10), pady=5)

        self.pull_from_website_button = ctk.CTkButton(self.top_button_frame, text="Pull von Website",
                                                      command=lambda: self.button_threads(
                                                          self.open_pull_selection_dialog),
                                                      fg_color="red", state="disabled")
        self.pull_from_website_button.pack(side="left", padx=5, pady=5)

        self.connect_to_website_button = ctk.CTkButton(self.top_button_frame, text="Connect to Website",
                                                       command=lambda: self.button_threads(self.start_connection),
                                                       fg_color="red")
        self.connect_to_website_button.pack(side="left", padx=5, pady=5)

        self.tab_view = ctk.CTkTabview(self.main_container, fg_color="transparent")
        self.tab_view.pack(fill="both", expand=True)
        self.data_tab = self.tab_view.add("Datenansicht")
        self.settings_tab = self.tab_view.add("Einstellungen")
        self.tree: Optional[ttk.Treeview] = None
        self.setup_data_view(self.data_tab)
        self.setup_settings_view(self.settings_tab)
        self.tree_context_menu = tk.Menu(self, tearoff=0, font=ctk.CTkFont(size=12))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Existing threads for background tasks
        self.server_thread = threading.Thread(target=connect, args=(self,), daemon=True)
        self.server_thread.start()
        self.arduino_thread = threading.Thread(target=self.arduino_connection, daemon=True)
        self.arduino_thread.start()
        self.website_thread = threading.Thread(target=self.start_connection, daemon=True)
        self.website_thread.start()

    def button_threads(self, function):
        threading.Thread(target=function, daemon=True).start()

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings_data.update(loaded_settings)
                    print(f"Einstellungen aus {SETTINGS_FILE} geladen.")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Fehler beim Laden der Einstellungsdatei: {e}")

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings_data, f, indent=4)
            print(f"Einstellungen in {SETTINGS_FILE} gespeichert.")
            messagebox.showinfo("Gespeichert", "Einstellungen wurden erfolgreich gespeichert.",
                                parent=self.settings_tab)
        except IOError as e:
            print(f"Fehler beim Speichern der Einstellungsdatei: {e}")
            messagebox.showerror("Fehler beim Speichern",
                                 f"Die Einstellungen konnten nicht in {SETTINGS_FILE} gespeichert werden.")

    def load_versions(self):
        try:
            if os.path.exists(VERSIONS_FILE):
                with open(VERSIONS_FILE, 'r', encoding='utf-8') as f:
                    self.versions = json.load(f)
                    print(f"{len(self.versions)} Versionen aus {VERSIONS_FILE} geladen.")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Fehler beim Laden der Versionen-Datei: {e}")
            self.versions = []

    def save_versions(self):
        try:
            with open(VERSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.versions, f, indent=4)
            print(f"Versionen in {VERSIONS_FILE} gespeichert.")
        except IOError as e:
            print(f"Fehler beim Speichern der Versionen-Datei: {e}")

    def connect_to_website(self):
        try:
            username = self.settings_data["username"]
            password = self.settings_data["password"]
            auth_endpoint = self.settings_data["API Endpoint Website"] + "token/"
            auth_response = requests.post(auth_endpoint, json={"username": username, "password": password})
            json_response = auth_response.json()
            refresh_token = json_response["refresh"]
            refresh_endpoint = self.settings_data["API Endpoint Website"] + "token/refresh/"
            refresh_response = requests.post(refresh_endpoint, json={"refresh": refresh_token})
            json_response = auth_response.json()
            access_token = json_response["access"]
            return access_token
        except Exception as e:
            print(f"Error bei der Verbindung mit dem Server: {e}")
            return None

    def start_connection(self):
        self.website_connect()
        if not self.headers: return
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
                self.force_push_button.configure(state="normal")
                break
        if not access_token:
            print("Die Verbindung hat nicht funktioniert, ändere die Einstellunge oder starte den Server.")
            return
        self.headers = {"Authorization": f"Bearer {access_token}"}

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
        self.force_push_button.configure(state="disabled")
        return None

    def push_data_website(self, data, run_identifier=1):
        print("Pushing data:", data)
        try:
            base_url = f"{self.settings_data['API Endpoint Website']}raceruns/"
            response = None
            payload = {
                "racer_start_number": str(data.get("start_nummer")),
                "time_in_seconds": data.get("renn_zeit"),
                "run_identifier": run_identifier,
                "run_type": data.get("round_number"),
                "recorded_at": data.get('timestamp_messung')
            }
            if data.get('_action') == "upsert":
                response = requests.post(base_url, json=payload, headers=self.headers)
            elif data.get('_action') == "delete":
                item_id = data.get('app_item_id')
                response = requests.delete(f"{base_url}{item_id}/", headers=self.headers)
            elif data.get('_action') == "changed":
                item_id = data.get('app_item_id')
                response = requests.patch(f"{base_url}{item_id}/", json=payload, headers=self.headers)
            else:
                print(f"Error: Unbekannte Aktion '{data.get('_action')}'")
                return False, data.get("app_item_id")
            response.raise_for_status()
            print("Push erfolgreich!", response.status_code)
            return True, data.get("app_item_id")
        except requests.HTTPError as http_err:
            print(f"HTTP-Fehler beim Pushen: {http_err}")
            try:
                print(f"API-Antwort: {http_err.response.json()}")
            except ValueError:
                print(f"API-Antwort (Text): {http_err.response.text}")
            return False, data.get("app_item_id")
        except requests.RequestException as req_err:
            print(f"Netzwerk- oder Verbindungsfehler: {req_err}")
            return False, data.get("app_item_id")
        except Exception as e:
            print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
            return False, data.get("app_item_id")

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
        ser = None
        while True:
            port = self.settings_data.get("Arduino Port")
            if not port or port == "Keiner":
                time.sleep(1)
                continue
            try:
                print(f"Versuche, Verbindung zu Arduino an Port {port} herzustellen...")
                ser = serial.Serial(port, 9600, timeout=1)
                time.sleep(2)
                ser.flushInput()
                print(f"Erfolgreich mit Arduino an {port} verbunden.")
                while True:
                    if self.settings_data.get("Arduino Port") != port:
                        print("Arduino-Port hat sich geändert. Starte Verbindung neu.")
                        break
                    if ser.in_waiting > 0:
                        line = ""
                        try:
                            line = ser.readline().decode('utf-8').strip()
                            if line:
                                if line == ",,,,_": continue
                                line = line.split(",")[0]
                                run_time = float(line)
                                print(f"Arduino Zeitmessung empfangen: {run_time}")
                                with self.data_lock:
                                    if not self.tree: continue
                                    children = self.tree.get_children("")
                                    target_item_id = None
                                    for item_id_check in reversed(children):
                                        if item_id_check in self.data_items:
                                            item_details = self.data_items[item_id_check]
                                            if item_details.get("data", {}).get("renn_zeit") is None:
                                                target_item_id = item_id_check
                                                break
                                    if target_item_id:
                                        current_item_data = self.data_items[target_item_id].get("data", {})
                                        update_payload = {"renn_zeit": run_time,
                                                          "timestamp_messung": datetime.datetime.now().isoformat()}
                                        self.after(0, self.update_tree_item, target_item_id, update_payload)
                                        print(
                                            f"Arduino: Rennzeit {run_time} für Item {target_item_id} (Startnr: {current_item_data.get('start_nummer', 'N/A')}) gesetzt.")
                        except (ValueError, UnicodeDecodeError) as e:
                            print(f"Fehler beim Verarbeiten der Arduino-Daten: '{line}'. Fehler: {e}")
                        except Exception as e:
                            print(f"Unerwarteter Fehler im Arduino-Lesevorgang: {e}")
                    time.sleep(0.05)
            except serial.SerialException as e:
                print(f"Arduino Verbindungsfehler an Port {port}: {e}. Versuche in 5 Sekunden erneut...")
                time.sleep(5)
            except Exception as e:
                print(f"Allgemeiner Fehler in arduino_connection: {e}")
                time.sleep(5)
            finally:
                if ser and ser.is_open:
                    ser.close()
                    print(f"Arduino-Verbindung zu {port} geschlossen.")

    def on_closing(self):
        print("MainApp wird geschlossen...")
        self._apply_and_save_settings()
        with self.client_management_lock:
            for client_q in list(self.clients.values()):
                try:
                    client_q.put(None)
                except Exception as e:
                    print(f"Error sending sentinel to client queue on closing: {e}")
        time.sleep(0.2)
        self.destroy()

    def add_client_queue(self, addr: Any, client_q: queue.Queue[Optional[str]]):
        with self.client_management_lock: self.clients[addr] = client_q
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
        renn_zeit_str = f"{renn_zeit_raw:.3f}" if isinstance(renn_zeit_raw, (float, int)) else str(
            renn_zeit_raw if renn_zeit_raw is not None else "")
        ts_to_send_raw = data.get("timestamp_messung")
        timestamp_display_str = ""
        if ts_to_send_raw:
            try:
                if isinstance(ts_to_send_raw, str):
                    dt_obj = datetime.datetime.fromisoformat(ts_to_send_raw.replace(" ", "T"))
                elif isinstance(ts_to_send_raw, datetime.datetime):
                    dt_obj = ts_to_send_raw
                else:
                    raise ValueError("Unsupported timestamp type")
                timestamp_display_str = dt_obj.strftime("%H:%M:%S (%d.%m.%Y)")
            except ValueError:
                timestamp_display_str = str(ts_to_send_raw)
        return f"{item_id}$#{start_nummer_str}$#{racer_name_str}$#{round_number_str}$#{renn_zeit_str}$#{timestamp_display_str}"

    def _get_all_data_for_clients_payload(self) -> str:
        all_items_formatted_strings = []
        with self.data_lock:
            for item_id, details in self.data_items.items():
                if details.get("status") == STATUS_DELETED: continue
                formatted_item = self._format_item_for_client(item_id, details)
                if formatted_item: all_items_formatted_strings.append(formatted_item)
        if not all_items_formatted_strings: return "ALL_DATA_EMPTY"
        return "ALL_DATA:" + "|".join(all_items_formatted_strings)

    def send_all_data_to_client(self, client_q: queue.Queue[Optional[str]]):
        payload = self._get_all_data_for_clients_payload()
        try:
            client_q.put(payload)
        except Exception as e:
            print(f"Error putting all_data (race runs) payload to client queue: {e}")

    def _get_racer_data_payload(self) -> str:
        if not self.racer_names_by_start_number: return "RACER_DATA_EMPTY"
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
        if payload is None: return
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
                        return
                else:
                    payload = f"DELETE_DATA:{item_id_updated}"
        else:
            payload = self._get_all_data_for_clients_payload()
        if payload is None: return
        with self.client_management_lock:
            for addr, client_q in self.clients.items():
                try:
                    client_q.put(payload)
                except Exception as e:
                    print(f"Error putting race run message to client queue for {addr}: {e}")

    def setup_data_view(self, parent_frame: ctk.CTkFrame):
        data_view_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        data_view_container.pack(fill="both", expand=True)

        action_bar = ctk.CTkFrame(data_view_container)
        action_bar.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(action_bar, text="Manueller Eintrag", command=lambda: self.open_manual_entry_dialog()).pack(
            side="left", padx=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_treeview_display_fully())
        search_entry = ctk.CTkEntry(action_bar, textvariable=self.search_var, placeholder_text="Suchen...")
        search_entry.pack(side="left", fill="x", expand=True)

        tree_container = ctk.CTkFrame(data_view_container)
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree_columns = ("status_indicator", "timestamp_combined", "start_number", "racer_name", "round_number",
                             "time_required", "scan_id_col")
        self.tree = ttk.Treeview(tree_container, columns=self.tree_columns, show="headings")
        vsb = ctk.CTkScrollbar(tree_container, command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ctk.CTkScrollbar(tree_container, command=self.tree.xview, orientation="horizontal")
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side="left", fill="both", expand=True)

        for col_id in self.tree_columns:
            if col_id in ["timestamp_combined", "start_number", "racer_name", "time_required"]:
                self.tree.heading(col_id, command=lambda c=col_id: self._sort_by_column(c))

        self.tree.heading("status_indicator", text="S", anchor=tk.W)
        self.tree.heading("timestamp_combined", text="Zeitstempel ▼", anchor=tk.W)
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

    def _get_available_ports(self) -> List[str]:
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        return ["Keiner"] + port_list

    def setup_settings_view(self, parent_frame: ctk.CTkFrame):
        settings_scroll_frame = ctk.CTkScrollableFrame(parent_frame, label_text="App Einstellungen")
        settings_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.setting_widgets.clear()

        for key, value in self.settings_data.items():
            setting_frame = ctk.CTkFrame(settings_scroll_frame)
            setting_frame.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(setting_frame, text=f"{key}:", width=220, anchor="w").pack(side="left", padx=(0, 10))
            widget: Optional[ctk.CTkBaseClass] = None
            if key == "Arduino Port":
                port_frame = ctk.CTkFrame(setting_frame, fg_color="transparent")
                port_frame.pack(side="left", fill="x", expand=True, padx=5)
                widget = ctk.CTkComboBox(port_frame, values=self._get_available_ports())
                widget.pack(side="left", fill="x", expand=True)
                refresh_button = ctk.CTkButton(port_frame, text="🔄", width=30,
                                               command=lambda: self.setup_settings_view(parent_frame))
                refresh_button.pack(side="left", padx=(5, 0))
            elif key == "Runde":
                widget = ctk.CTkComboBox(setting_frame, values=ROUND_NAMES)
            elif key == "Server Adresse (für API)":
                options = ["localhost", "127.0.0.1", str(self.settings_data.get(key, "localhost"))]
                unique_options = sorted(list(set(filter(None, options))))
                widget = ctk.CTkComboBox(setting_frame, values=unique_options)
            else:
                widget = ctk.CTkEntry(setting_frame)

            if widget:
                widget.pack(side="left", fill="x", expand=True, padx=5)
                self.setting_widgets[key] = widget
                if isinstance(widget, ctk.CTkComboBox):
                    widget.set(str(value))
                elif isinstance(widget, ctk.CTkEntry):
                    widget.insert(0, str(value))

        save_button = ctk.CTkButton(settings_scroll_frame, text="Einstellungen Speichern",
                                    command=self._apply_and_save_settings)
        save_button.pack(pady=(20, 5), padx=5)

    def _apply_and_save_settings(self):
        print("Speichere Einstellungen via Button-Klick...")
        for key, widget in self.setting_widgets.items():
            new_value = None
            if isinstance(widget, (ctk.CTkEntry, ctk.CTkComboBox)):
                new_value = widget.get()

            if new_value is not None and self.settings_data.get(key) != new_value:
                current_setting_value = self.settings_data.get(key)
                try:
                    if isinstance(current_setting_value, int):
                        new_value = int(new_value)
                    elif isinstance(current_setting_value, float):
                        new_value = float(new_value)
                except (ValueError, TypeError):
                    pass

                self.settings_data[key] = new_value
                print(f"Einstellung '{key}' geändert zu: {new_value}")

        self.save_settings()

    def _get_status_indicator(self, status: Optional[str]) -> str:
        return {STATUS_NEW: "➕", STATUS_MODIFIED: "✏️", STATUS_DELETED: "🗑️", STATUS_SYNCED: "✔️",
                STATUS_SYNCED_LOCAL: "💾", STATUS_COMPLETE: "🏁"}.get(status or "", "?")

    def _create_tree_item_values(self, item_id: str, item_details: Dict[str, Any]) -> tuple:
        data = item_details.get("data", {})
        status_ind = self._get_status_indicator(item_details.get("status"))

        ts_for_display_raw = data.get("timestamp_messung")
        ts_combined_display = "-"
        if ts_for_display_raw:
            try:
                if isinstance(ts_for_display_raw, str):
                    dt_obj = datetime.datetime.fromisoformat(ts_for_display_raw.replace(" ", "T"))
                elif isinstance(ts_for_display_raw, datetime.datetime):
                    dt_obj = ts_for_display_raw
                else:
                    dt_obj = None
                if dt_obj:
                    ts_combined_display = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    ts_combined_display = str(ts_for_display_raw)[:19]
            except ValueError:
                ts_combined_display = str(ts_for_display_raw)[:19]

        renn_zeit_val = data.get("renn_zeit")
        renn_zeit_display = f"{renn_zeit_val:.3f}s" if isinstance(renn_zeit_val, (float, int)) else "-"
        scan_id_val = data.get("zugeordneter_scan_id") or data.get("scan_id")
        scan_id_display = (str(scan_id_val)[:8] + "...") if scan_id_val and len(str(scan_id_val)) > 8 else str(
            scan_id_val or "-")
        start_nummer_val = str(data.get("start_nummer", ""))
        racer_name_display = self.racer_names_by_start_number.get(start_nummer_val, "Startnummer unbekannt!")
        return (status_ind, ts_combined_display, start_nummer_val if start_nummer_val else "-", racer_name_display,
                str(data.get("round_number", "-")), renn_zeit_display, scan_id_display)

    def add_item_to_tree(self, current_data_dict: Dict[str, Any], item_id: Optional[str] = None) -> str:
        new_item_id = item_id or str(uuid.uuid4())
        with self.data_lock:
            current_data_dict.setdefault("timestamp_messung", datetime.datetime.now().isoformat())
            current_data_dict["updated_at"] = datetime.datetime.now().isoformat()
            if "scan_id" in current_data_dict and "zugeordneter_scan_id" not in current_data_dict:
                current_data_dict["zugeordneter_scan_id"] = current_data_dict["scan_id"]
            self.data_items[new_item_id] = {"data": current_data_dict, "status": STATUS_NEW,
                                            "original_data_snapshot": None, "data_before_delete": None}
            self.after(0, self.refresh_treeview_display_fully)
        self.broadcast_data_update(new_item_id)
        return new_item_id

    def update_tree_item(self, item_id: str, new_data_dict: Dict[str, Any]):
        with self.data_lock:
            if item_id not in self.data_items or self.data_items[item_id]["status"] == STATUS_DELETED: return
            details = self.data_items[item_id]
            if details["status"] in [STATUS_SYNCED, STATUS_SYNCED_LOCAL] and details.get("original_data_snapshot") is None:
                details["original_data_snapshot"] = copy.deepcopy(details["data"])
            details["data"]["updated_at"] = datetime.datetime.now().isoformat()
            if "timestamp_messung" in new_data_dict and isinstance(new_data_dict["timestamp_messung"],
                                                                   datetime.datetime):
                new_data_dict["timestamp_messung"] = new_data_dict["timestamp_messung"].isoformat()

            details["data"].update(new_data_dict)
            if details["status"] != STATUS_NEW: details["status"] = STATUS_MODIFIED
            if (details["data"].get("start_nummer") and details["data"].get("renn_zeit") is not None and details[
                "status"] not in [STATUS_NEW, STATUS_SYNCED, STATUS_DELETED, STATUS_COMPLETE]):
                details["status"] = STATUS_COMPLETE
            self.after(0, self.refresh_treeview_display_fully)
        self.broadcast_data_update(item_id)

    def open_manual_entry_dialog(self, item_id_to_edit: Optional[str] = None):
        is_edit = item_id_to_edit is not None
        initial_data = {}
        if is_edit and item_id_to_edit:
            with self.data_lock:
                if item_id_to_edit not in self.data_items or self.data_items[item_id_to_edit].get(
                        "status") == STATUS_DELETED:
                    messagebox.showinfo("Info", "Eintrag nicht bearbeitbar.", parent=self)
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
            name_var.set(self.racer_names_by_start_number.get(e_sn.get().strip(), "Startnummer unbekannt!"))

        e_sn_var = tk.StringVar(value=str(initial_data.get("start_nummer", "")))
        e_sn.configure(textvariable=e_sn_var)
        e_sn_var.trace_add("write", _update_name_in_dialog_manual_entry)
        _update_name_in_dialog_manual_entry()

        ctk.CTkLabel(dialog, text="Runde:").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        combo_rd = ctk.CTkComboBox(dialog, values=ROUND_NAMES)
        combo_rd.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        combo_rd.set(str(initial_data.get("round_number", self.settings_data.get("Runde", "PR"))))

        row_idx += 1
        ctk.CTkLabel(dialog, text="Rennzeit (s):").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        e_rz = ctk.CTkEntry(dialog)
        e_rz.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        rz_val = initial_data.get('renn_zeit')
        e_rz.insert(0, f"{rz_val:.3f}" if isinstance(rz_val, (float, int)) else "")

        row_idx += 1
        ctk.CTkLabel(dialog, text="Zeitstempel (leer=auto):").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        e_mz = ctk.CTkEntry(dialog)
        e_mz.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
        ts_messung_val = initial_data.get("timestamp_messung", "")
        if ts_messung_val:
            try:
                dt_obj = datetime.datetime.fromisoformat(str(ts_messung_val).replace(" ", "T"))
                e_mz.insert(0, dt_obj.strftime("%Y-%m-%d %H:%M:%S"))
            except ValueError:
                e_mz.insert(0, str(ts_messung_val))

        def save():
            sn_str = e_sn.get().strip()
            rd_str = combo_rd.get().strip()
            rz_str = e_rz.get().strip().replace(",", ".")
            mz_str = e_mz.get().strip()
            if not sn_str:
                messagebox.showerror("Fehler", "Startnummer muss angegeben werden.", parent=dialog)
                return

            payload: Dict[str, Any] = {"start_nummer": sn_str}
            if rd_str:
                payload["round_number"] = rd_str
            elif not is_edit or "round_number" not in initial_data:
                payload["round_number"] = self.settings_data.get("Runde", "PR")
            if rz_str:
                try:
                    payload["renn_zeit"] = float(rz_str)
                except ValueError:
                    messagebox.showerror("Fehler", "Ungültige Rennzeit.", parent=dialog)
                    return
            if mz_str:
                try:
                    cleaned_mz_str = mz_str.strip().replace(" ", "T")
                    payload["timestamp_messung"] = datetime.datetime.fromisoformat(cleaned_mz_str).isoformat()
                except ValueError:
                    messagebox.showerror("Fehler", "Ungültiges Zeitstempel-Format. Erwartet: YYYY-MM-DD HH:MM:SS.",
                                         parent=dialog)
                    return
            elif not is_edit:
                payload["timestamp_messung"] = datetime.datetime.now().isoformat()

            if is_edit and item_id_to_edit:
                self.update_tree_item(item_id_to_edit, payload)
            else:
                self.add_item_to_tree(payload)
            dialog.destroy()

        row_idx += 1
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
        if self.tree_context_menu.index(tk.END) is not None: self.tree_context_menu.tk_popup(event.x_root, event.y_root)

    def on_tree_double_click(self, event: tk.Event):
        if not self.tree: return
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        can_edit = False
        with self.data_lock:
            if item_id in self.data_items and self.data_items[item_id].get("status") != STATUS_DELETED: can_edit = True
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
            if item_id in self.data_items and self.data_items[item_id].get("status") != STATUS_DELETED: can_edit = True
        if can_edit:
            self.open_manual_entry_dialog(item_id_to_edit=item_id)
        else:
            messagebox.showinfo("Info", "Element nicht bearbeitbar.", parent=self)
        self._context_menu_item_id = None

    def delete_selected_tree_item(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        with self.data_lock:
            if item_id not in self.data_items or self.data_items[item_id].get("status") == STATUS_DELETED:
                self._context_menu_item_id = None
                return

            details_to_delete = self.data_items[item_id]
            broadcast_delete_signal = False
            item_removed_from_data_items_and_tree = False

            if details_to_delete.get("status") == STATUS_NEW:
                del self.data_items[item_id]
                item_removed_from_data_items_and_tree = True
                broadcast_delete_signal = True
            else:
                if details_to_delete.get("data_before_delete") is None:
                    details_to_delete["data_before_delete"] = {"data": copy.deepcopy(details_to_delete.get("data", {})),
                                                               "original_status": details_to_delete.get("status"),
                                                               "original_snapshot_if_modified": copy.deepcopy(
                                                                   details_to_delete.get("original_data_snapshot"))}
                details_to_delete["status"] = STATUS_DELETED
                details_to_delete["original_data_snapshot"] = None
                self.after(0, self.refresh_treeview_display_fully)
                broadcast_delete_signal = True

        if item_removed_from_data_items_and_tree and self.tree and self.tree.exists(item_id): self.tree.delete(item_id)
        if broadcast_delete_signal: self.broadcast_data_update(item_id, is_delete=True)
        self._context_menu_item_id = None

    def revert_item_changes_dialog(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        with self.data_lock:
            if item_id not in self.data_items or self.data_items[item_id].get("status") != STATUS_MODIFIED or not \
            self.data_items[item_id].get("original_data_snapshot"):
                messagebox.showinfo("Info", "Keine Änderungen zum Verwerfen.", parent=self)
                self._context_menu_item_id = None
                return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Änderungen Verwerfen?")

        def confirm_revert():
            with self.data_lock:
                if item_id not in self.data_items: return
                item_to_revert = self.data_items[item_id]
                if item_to_revert.get("original_data_snapshot"):
                    item_to_revert["data"] = copy.deepcopy(item_to_revert["original_data_snapshot"])
                    item_to_revert["original_data_snapshot"] = None
                    item_to_revert["status"] = STATUS_SYNCED_LOCAL
                    self.after(0, self.refresh_treeview_display_fully)
                else:
                    messagebox.showinfo("Info", "Originaldaten für Revert nicht mehr vorhanden.", parent=dialog)
            self.broadcast_data_update(item_id)
            dialog.destroy()
            self._context_menu_item_id = None

    def restore_deleted_item(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        with self.data_lock:
            if item_id not in self.data_items or self.data_items[item_id].get("status") != STATUS_DELETED or not \
            self.data_items[item_id].get("data_before_delete"):
                messagebox.showinfo("Info", "Element nicht wiederherstellbar.", parent=self)
                self._context_menu_item_id = None
                return
            start_nr_display = str(
                self.data_items[item_id]["data_before_delete"].get("data", {}).get('start_nummer', item_id))

        if messagebox.askyesno("Wiederherstellen", f"Eintrag für Startnr. '{start_nr_display}' wiederherstellen?",
                               parent=self):
            with self.data_lock:
                if item_id not in self.data_items: return
                details_to_restore = self.data_items[item_id]
                if not (details_to_restore.get("status") == STATUS_DELETED and details_to_restore.get(
                    "data_before_delete")): return
                restore_info = details_to_restore["data_before_delete"]
                details_to_restore["data"] = copy.deepcopy(restore_info["data"])
                details_to_restore["status"] = restore_info.get("original_status", STATUS_MODIFIED)
                details_to_restore["original_data_snapshot"] = copy.deepcopy(
                    restore_info.get("original_snapshot_if_modified"))
                details_to_restore["data_before_delete"] = None
                self.after(0, self.refresh_treeview_display_fully)
            self.broadcast_data_update(item_id)
        self._context_menu_item_id = None

    def create_internal_snapshot(self, snapshot_type="internal_save", show_success_message=True) -> bool:
        with self.data_lock:
            items_to_include_in_version = []
            has_pending_actions = False
            for iid, dets in self.data_items.items():
                item_data_copy = copy.deepcopy(dets.get("data", {}))
                items_to_include_in_version.append({"_id_internal": iid, "_status_at_version": dets.get("status"),
                                                    "_synced_to_website_at_version": dets.get("_synced_to_website",
                                                                                              False),
                                                    **item_data_copy})
                if dets.get("status") in [STATUS_NEW, STATUS_MODIFIED, STATUS_COMPLETE, STATUS_DELETED]:
                    has_pending_actions = True

            if not has_pending_actions and snapshot_type == "internal_save":
                if show_success_message:
                    messagebox.showinfo("Snapshot Erstellen", "Keine ungesicherten Änderungen vorhanden.", parent=self)
                return False

            self.versions.append({"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  "data_snapshot": items_to_include_in_version, "type": snapshot_type})
            self.save_versions()
            version_number = len(self.versions)

            if snapshot_type == "internal_save":
                items_marked_synced_count = 0
                item_ids_to_process = list(self.data_items.keys())
                for item_id in item_ids_to_process:
                    if item_id in self.data_items:
                        details = self.data_items[item_id]
                        if details.get("status") in [STATUS_NEW, STATUS_MODIFIED, STATUS_COMPLETE]:
                            details["status"] = STATUS_SYNCED_LOCAL
                            details["original_data_snapshot"] = None
                            items_marked_synced_count += 1
                if show_success_message:
                    msg = f"Snapshot Version {version_number} erstellt und in '{VERSIONS_FILE}' gespeichert.\n"
                    if items_marked_synced_count > 0: msg += f"{items_marked_synced_count} Element(e) als 'Gesichert' markiert."
                    messagebox.showinfo("Snapshot Erstellt", msg, parent=self)
                self.refresh_treeview_display_fully()

            return True

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

                # Wenn das Element gelöscht werden soll
                if status == STATUS_DELETED:
                    if details.get("data_before_delete") or details.get("_synced_to_website"):
                        payload["_action"] = "delete"
                        data_for_website.append(payload)
                        items_to_delete_permanently_after_push.append(item_id)
                # Wenn das Element noch nie auf der Website war (oder das Flag fehlt)
                elif not details.get("_synced_to_website"):
                    payload["_action"] = "upsert"
                    data_for_website.append(payload)
                    items_to_mark_synced_after_push.append(item_id)
                # Wenn es bereits auf der Website war und lokal geändert wurde
                elif status in [STATUS_MODIFIED, STATUS_COMPLETE, STATUS_SYNCED_LOCAL]:
                    payload["_action"] = "changed"
                    data_for_website.append(payload)
                    items_to_mark_synced_after_push.append(item_id)

        return data_for_website, items_to_mark_synced_after_push, items_to_delete_permanently_after_push

    def initiate_push_to_website(self):
        self.create_internal_snapshot(snapshot_type="pre_push_backup", show_success_message=False)
        data_to_send, _, _ = self._collect_data_for_website_push()
        if not data_to_send:
            messagebox.showinfo("Push to Website",
                                "Keine neuen oder geänderten Daten für den Push zur Website vorhanden.", parent=self)
            return

        self.push_to_website_button.configure(state="disabled", text="Pushe...")
        self.force_push_button.configure(state="disabled")

        def _push_task():
            successful_upsert_ids, successful_delete_ids, had_errors = [], [], False
            for p_data in data_to_send:
                success, item_id = self.push_data_website(p_data)
                if success:
                    if p_data.get("_action") == "delete":
                        if item_id: successful_delete_ids.append(item_id)
                    else:
                        if item_id: successful_upsert_ids.append(item_id)
                else:
                    had_errors = True

            # Finalize and ask to pull in main thread
            self.after(0, self._finalize_website_push, not had_errors, successful_upsert_ids, successful_delete_ids)

        threading.Thread(target=_push_task, daemon=True).start()

    def _finalize_website_push(self, all_success: bool, ids_successfully_upserted_on_server: List[str],
                               ids_successfully_deleted_on_server: List[str]):
        updated_count, deleted_count = 0, 0
        with self.data_lock:
            for item_id in ids_successfully_upserted_on_server:
                if item_id in self.data_items:
                    details = self.data_items[item_id]
                    if details.get("status") != STATUS_DELETED:
                        details["status"] = STATUS_SYNCED
                        details["original_data_snapshot"] = None
                        details["_synced_to_website"] = True
                        updated_count += 1
            ids_to_remove_from_tree = []
            for item_id in ids_successfully_deleted_on_server:
                if item_id in self.data_items:
                    del self.data_items[item_id]
                    ids_to_remove_from_tree.append(item_id)
                    deleted_count += 1

        self.refresh_treeview_display_fully()
        self.broadcast_data_update()

        # After updating the view, ask the user if they want to pull
        self.after(100, self._ask_to_pull_after_push, all_success, updated_count, deleted_count)

    def _ask_to_pull_after_push(self, all_success, updated_count, deleted_count):
        msg = f"Push abgeschlossen.\n{updated_count} Einträge erfolgreich hochgeladen/aktualisiert.\n{deleted_count} Einträge erfolgreich gelöscht."
        pull_question = "\n\nMöchten Sie jetzt die Daten von der Website laden, um den Datenstand zu synchronisieren?"

        if not all_success:
            msg += "\n\nAchtung: Einige Einträge konnten nicht gepusht werden. Ein Abgleich wird dringend empfohlen."
            should_pull = messagebox.askyesno("Push Ergebnis mit Fehlern", msg + pull_question, icon=messagebox.WARNING,
                                              parent=self)
        else:
            should_pull = messagebox.askyesno("Push Ergebnis", msg + pull_question, icon=messagebox.QUESTION,
                                              parent=self)

        if should_pull:
            # Force merge if there were errors, otherwise just a normal pull (which overwrites)
            self.pull_race_runs_from_website(force_merge=(not all_success))

        self._reenable_push_buttons()

    def _force_push_task(self):
        # Schritt 1: Backup der aktuellen Website-Daten (bleibt als Sicherheitsmaßnahme erhalten)
        self.after(0, lambda: self.force_push_button.configure(text="Backup..."))
        api_endpoint = self.settings_data.get('API Endpoint Website', 'N/A')
        website_runs_url = api_endpoint + "raceruns/"

        print("--- Zwangspush: Starte Backup der Website-Daten ---")
        website_data_to_backup = self.get_data_website(website_runs_url)

        if website_data_to_backup is None:
            self.after(0, lambda: messagebox.showerror("Fehler",
                                                       "Konnte keine Daten von der Website für das Backup abrufen. Zwangspush abgebrochen.",
                                                       parent=self))
            self.after(0, self._reenable_push_buttons)
            return

        try:
            backup_filename = f"website_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(website_data_to_backup, f, indent=4)
            print(f"--- Zwangspush: Backup erfolgreich in '{backup_filename}' gespeichert. ---")
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler",
                                                       f"Konnte das Backup nicht speichern: {e}\nZwangspush abgebrochen.",
                                                       parent=self))
            self.after(0, self._reenable_push_buttons)
            return

        # Schritt 2: Alle Einträge auf der Website löschen
        self.after(0, lambda: self.force_push_button.configure(text="Lösche alle..."))
        server_item_ids = {str(item.get('id')) for item in website_data_to_backup if item.get('id')}

        print(f"--- Zwangspush: Lösche {len(server_item_ids)} Einträge auf der Website. ---")
        delete_errors = 0

        for item_id_to_delete in server_item_ids:
            delete_url = f"{api_endpoint}raceruns/{item_id_to_delete}/"
            try:
                response = requests.delete(delete_url, headers=self.headers)
                if response.status_code not in [204, 404]:  # 204 No Content (Success), 404 Not Found (auch ok)
                    response.raise_for_status()
            except Exception as e:
                print(f"Fehler beim Löschen von Item {item_id_to_delete} auf der Website: {e}")
                delete_errors += 1

        if delete_errors > 0:
            print(
                f"Warnung: {delete_errors} Fehler beim Löschen von Einträgen auf der Website. Fahre trotzdem mit dem Push fort.")

        # Schritt 3: Alle lokalen, nicht gelöschten Einträge als NEUE Einträge pushen
        self.after(0, lambda: self.force_push_button.configure(text="Pushe alle..."))

        with self.data_lock:
            items_to_push = []
            for item_id, details in self.data_items.items():
                if details.get("status") != STATUS_DELETED:
                    payload = copy.deepcopy(details.get("data", {}))
                    payload["app_item_id"] = item_id  # Lokale ID für Fehlersuche mitsenden
                    payload['_action'] = 'upsert'
                    items_to_push.append(payload)

        print(f"--- Zwangspush: Pushe {len(items_to_push)} lokale Einträge zur Website. ---")
        push_errors = 0
        total_pushed = len(items_to_push)
        for item_data in items_to_push:
            success, _ = self.push_data_website(item_data)
            if not success:
                push_errors += 1

        # Schritt 4: Finalisierung im Main-Thread
        self.after(0, self._finalize_force_push, total_pushed, push_errors, delete_errors)

    def _finalize_force_push(self, total_pushed, push_errors, delete_errors):
        # Erfolgsmeldung anzeigen
        msg = f"Zwangspush abgeschlossen.\n{total_pushed - push_errors} von {total_pushed} Einträgen erfolgreich zur Website hochgeladen."
        if push_errors > 0 or delete_errors > 0:
            msg += f"\n\nACHTUNG: Es gab Fehler!\n- {push_errors} Fehler beim Hochladen.\n- {delete_errors} Fehler beim Löschen."
            messagebox.showwarning("Zwangspush Ergebnis", msg, parent=self)
        else:
            messagebox.showinfo("Zwangspush Ergebnis", msg, parent=self)

        # WICHTIG: Nach dem Zwangspush die Daten von der Website neu laden
        # und dem Benutzer einen Merge anbieten, um die neuen Server-IDs abzugleichen.
        print("--- Zwangspush: Führe einen Merge-Pull aus, um die Daten neu zu synchronisieren. ---")
        self.pull_race_runs_from_website(force_merge=True)

        # Buttons werden nach dem Pull/Merge wieder aktiviert
        self.after(500, self._reenable_push_buttons)

    def initiate_force_push_to_website(self):
        self.push_to_website_button.configure(state="disabled")
        self.force_push_button.configure(state="disabled")

        threading.Thread(target=self._force_push_task, daemon=True).start()

    def _force_push_task(self):
        # Schritt 1: Lade aktuelle Daten von der Website und zähle sie.
        api_endpoint = self.settings_data.get('API Endpoint Website', 'N/A')
        website_runs_url = api_endpoint + "raceruns/"

        print("--- Zwangspush: Lade Website-Daten für Zählung und Backup ---")
        website_data_to_backup = self.get_data_website(website_runs_url)

        if website_data_to_backup is None:
            self.after(0, lambda: messagebox.showerror("Fehler",
                                                       "Konnte keine Daten von der Website abrufen. Zwangspush abgebrochen.",
                                                       parent=self))
            self.after(0, self._reenable_push_buttons)
            return

        server_item_count = len(website_data_to_backup)
        with self.data_lock:
            local_item_count = sum(1 for details in self.data_items.values() if details.get("status") != STATUS_DELETED)

        # Schritt 2: Zeige Bestätigungsdialog
        user_confirmed = queue.Queue()
        self.after(0,
                   lambda: self._ask_for_force_push_confirmation(server_item_count, local_item_count, user_confirmed))

        if not user_confirmed.get():
            print("--- Zwangspush: Vom Benutzer abgebrochen. ---")
            self.after(0, self._reenable_push_buttons)
            return

        # Wenn der Benutzer bestätigt hat, fahre fort.
        self.after(0, lambda: self.force_push_button.configure(text="Backup..."))

        # Schritt 3: Backup
        try:
            backup_filename = f"website_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(website_data_to_backup, f, indent=4)
            print(f"--- Zwangspush: Backup erfolgreich in '{backup_filename}' gespeichert. ---")
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler",
                                                       f"Konnte das Backup nicht speichern: {e}\nZwangspush abgebrochen.",
                                                       parent=self))
            self.after(0, self._reenable_push_buttons)
            return

        # Schritt 4: Alle Einträge auf der Website löschen
        self.after(0, lambda: self.force_push_button.configure(text="Lösche alle..."))
        server_item_ids = {str(item.get('id')) for item in website_data_to_backup if item.get('id')}

        print(f"--- Zwangspush: Lösche {len(server_item_ids)} Einträge auf der Website. ---")
        delete_errors = 0
        for item_id_to_delete in server_item_ids:
            delete_url = f"{api_endpoint}raceruns/{item_id_to_delete}/"
            try:
                response = requests.delete(delete_url, headers=self.headers)
                if response.status_code not in [204, 404]:
                    response.raise_for_status()
            except Exception as e:
                print(f"Fehler beim Löschen von Item {item_id_to_delete} auf der Website: {e}")
                delete_errors += 1

        # Schritt 5: Alle lokalen, nicht gelöschten Einträge als NEUE Einträge pushen
        self.after(0, lambda: self.force_push_button.configure(text="Pushe alle..."))
        with self.data_lock:
            items_to_push = [copy.deepcopy(details.get("data", {})) for details in self.data_items.values() if
                             details.get("status") != STATUS_DELETED]
            for item in items_to_push:
                item['_action'] = 'upsert'

        print(f"--- Zwangspush: Pushe {len(items_to_push)} lokale Einträge zur Website. ---")
        push_errors = 0
        for item_data in items_to_push:
            success, _ = self.push_data_website(item_data)
            if not success:
                push_errors += 1

        # Schritt 6: Finalisierung und Merge-Dialog im Main-Thread aufrufen
        self.after(0, self._finalize_force_push, len(items_to_push), push_errors, delete_errors)

    def _ask_for_force_push_confirmation(self, server_count, local_count, result_queue):
        confirmed = messagebox.askyesno("Zwangspush Bestätigung",
                                        f"ACHTUNG: Dies wird die Website vollständig mit den lokalen Daten überschreiben.\n\n"
                                        f"- Es werden {server_count} Einträge auf der Website gelöscht.\n"
                                        f"- Danach werden {local_count} lokale Einträge neu hochgeladen.\n\n"
                                        f"Dieser Vorgang kann nicht rückgängig gemacht werden.\n\n"
                                        "Möchten Sie wirklich fortfahren?",
                                        icon=messagebox.WARNING, parent=self)
        result_queue.put(confirmed)

    def _finalize_force_push(self, total_pushed, push_errors, delete_errors):
        msg = f"Zwangspush Phase 1 abgeschlossen.\n{total_pushed - push_errors} von {total_pushed} Einträgen erfolgreich zur Website hochgeladen."
        if push_errors > 0 or delete_errors > 0:
            msg += f"\n\nACHTUNG: Es gab Fehler!\n- {push_errors} Fehler beim Hochladen.\n- {delete_errors} Fehler beim Löschen."
            messagebox.showwarning("Zwangspush Ergebnis", msg, parent=self)
        else:
            messagebox.showinfo("Zwangspush Ergebnis", msg, parent=self)

        print("--- Zwangspush: Phase 2 - Führe Merge aus, um die Daten neu zu synchronisieren. ---")
        # Nach dem Überschreiben der Website MÜSSEN wir einen Merge machen,
        # um die neuen Server-IDs mit unseren lokalen Daten abzugleichen.
        self.pull_race_runs_from_website(force_merge=True)

        self._reenable_push_buttons()

    def _reenable_push_buttons(self):
        is_connected = self.connect_to_website_button.cget("state") == "disabled"
        if is_connected:
            self.push_to_website_button.configure(state="normal", text="Push to Website")
            self.force_push_button.configure(state="normal", text="Zwangspush")

    def open_pull_selection_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Pull von Website - Auswahl")
        dialog.geometry("350x250")
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Was soll von der Website geladen werden?").pack(pady=10)

        pull_racers_var = tk.BooleanVar(value=True)
        pull_runs_var = tk.BooleanVar(value=True)
        merge_var = tk.BooleanVar(value=False)

        ctk.CTkCheckBox(dialog, text="Rennfahrer-Liste", variable=pull_racers_var).pack(pady=5, anchor="w", padx=20)
        ctk.CTkCheckBox(dialog, text="Renndurchläufe", variable=pull_runs_var).pack(pady=5, anchor="w", padx=20)
        ctk.CTkCheckBox(dialog, text="Daten bei Konflikt mischen (Merge)", variable=merge_var).pack(pady=5, anchor="w",
                                                                                                    padx=20)

        def start_pull():
            pull_racers, pull_runs, do_merge = pull_racers_var.get(), pull_runs_var.get(), merge_var.get()
            dialog.destroy()
            if not pull_racers and not pull_runs: return

            self.create_internal_snapshot(snapshot_type="pre_pull_backup", show_success_message=False)

            if pull_racers: self.pull_racers_from_website()
            if pull_runs: self.pull_race_runs_from_website(force_merge=do_merge)

        ctk.CTkButton(dialog, text="Pull Starten", command=start_pull).pack(pady=10)
        ctk.CTkButton(dialog, text="Abbrechen", command=dialog.destroy, fg_color="gray50").pack(pady=5)

    def pull_racers_from_website(self):
        api_endpoint = self.settings_data.get('API Endpoint Website', 'N/A')
        print(f"--- Pull von Racer-Daten von ({api_endpoint}) ---")

        def _do_racer_pull():
            racers_payload = self.get_data_website(api_endpoint + "racers/")
            if racers_payload is None:
                self.after(0, lambda: messagebox.showerror("Pull Fehler", "Konnte keine Racer-Daten abrufen.",
                                                           parent=self))
                return
            self.after(0, self._update_racer_data_store, racers_payload, True)

        threading.Thread(target=_do_racer_pull, daemon=True).start()

    def pull_race_runs_from_website(self, force_merge: bool = False):
        api_endpoint = self.settings_data.get('API Endpoint Website', 'N/A')
        print(f"--- Pull von Renndurchläufen von ({api_endpoint}) ---")

        def _do_race_run_pull():
            website_data_payload = self.get_data_website(api_endpoint + "raceruns/")
            if website_data_payload is None:
                self.after(0, lambda: messagebox.showerror("Pull Fehler",
                                                           "Konnte keine Renndaten von der Website abrufen.",
                                                           parent=self))
                self.after(0, self._reenable_push_buttons)
                return

            if not force_merge:
                # Normal pull just overwrites local data
                self.after(0, self._process_pulled_website_data, website_data_payload)
            else:
                # A "Merge Pull" requires intelligent matching
                self.after(0, self._initiate_merge_with_website_data, website_data_payload)

        threading.Thread(target=_do_race_run_pull, daemon=True).start()

    def _initiate_merge_with_website_data(self, website_data_list: List[Dict[str, Any]]):
        """Prepares data for MergeView by using a logical composite key for matching."""
        with self.data_lock:
            local_data_copy = copy.deepcopy(self.data_items)

        # --- Intelligent Matching Logic ---
        # 1. Prepare local data with a composite key: "start_number-round_number"
        local_data_for_merge = {}
        self.merge_local_map = {}  # Store mapping from composite key to original local ID
        for item_id, details in local_data_copy.items():
            data = details.get("data", {})
            sn = data.get("start_nummer")
            rn = data.get("round_number")
            if sn and rn:
                composite_key = f"{sn}-{rn}"
                local_data_for_merge[composite_key] = details
                self.merge_local_map[composite_key] = item_id

        # 2. Prepare remote data with the same composite key
        remote_data_for_merge = {}
        self.merge_remote_map = {}  # Store mapping from composite key to new server ID
        for web_item in website_data_list:
            sn = web_item.get("racer_start_number")
            rn = web_item.get("run_type")
            server_id = str(web_item.get("id"))
            if not (sn and rn and server_id):
                continue

            composite_key = f"{sn}-{rn}"

            renn_zeit_val = float(web_item.get("time_in_seconds")) if web_item.get(
                "time_in_seconds") is not None else None
            remote_data_format = {
                "data": {
                    "start_nummer": sn,
                    "round_number": rn,
                    "renn_zeit": renn_zeit_val,
                    "timestamp_messung": web_item.get("recorded_at"),
                    "disqualified": web_item.get("disqualified"),
                    "notes": web_item.get("notes"),
                    "updated_at": web_item.get("updated_at") or datetime.datetime.now().isoformat(),
                },
                "status": STATUS_SYNCED,
                "_synced_to_website": True
            }
            remote_data_for_merge[composite_key] = remote_data_format
            self.merge_remote_map[composite_key] = server_id

        # 3. Open MergeView with the consistently keyed data
        MergeView(self, local_data=local_data_for_merge, remote_data=remote_data_for_merge, source_name="Website",
                  callback_on_finish=self._finalize_merge)

    def open_merge_view_for_pull(self, website_data_list: List[Dict[str, Any]]):
        with self.data_lock:
            local_data_copy = copy.deepcopy(self.data_items)

        remote_data_dict = {}
        for web_item in website_data_list:
            # Nach einem Zwangspush sind die IDs auf dem Server neu,
            # daher können wir uns nicht auf die ID als Schlüssel verlassen.
            # Wir versuchen einen Match über Startnummer und Runde zu finden.
            # Für diesen Anwendungsfall nehmen wir die Server-ID als neuen Schlüssel.
            item_id = str(web_item.get("id"))
            if not item_id: continue

            renn_zeit_val = float(web_item.get("time_in_seconds")) if web_item.get(
                "time_in_seconds") is not None else None
            remote_data_format = {
                "data": {
                    "start_nummer": web_item.get("racer_start_number"),
                    "round_number": web_item.get("run_type"),
                    "renn_zeit": renn_zeit_val,
                    "timestamp_messung": web_item.get("recorded_at"),
                    "disqualified": web_item.get("disqualified"),
                    "notes": web_item.get("notes"),
                    "updated_at": web_item.get("updated_at") or datetime.datetime.now().isoformat(),
                },
                "status": STATUS_SYNCED,
                "_synced_to_website": True
            }
            remote_data_dict[item_id] = remote_data_format

        MergeView(self, local_data=local_data_copy, remote_data=remote_data_dict, source_name="Website",
                  callback_on_finish=self._finalize_merge)

    def _process_pulled_website_data(self, website_data_list: List[Dict[str, Any]]):
        if not isinstance(website_data_list, list):
            messagebox.showinfo("Pull Renndaten", "Keine oder ungültige Renndaten von der Website empfangen.",
                                parent=self)
            return
        with self.data_lock:
            self.data_items.clear()
            for web_item_payload in website_data_list:
                item_id_from_web = web_item_payload.get("id")
                if not item_id_from_web: continue
                item_id_from_web = str(item_id_from_web)
                try:
                    renn_zeit_val = float(web_item_payload.get("time_in_seconds")) if web_item_payload.get(
                        "time_in_seconds") is not None else None
                except (ValueError, TypeError):
                    renn_zeit_val = None
                local_data_format = {"start_nummer": web_item_payload.get("racer_start_number"),
                                     "round_number": web_item_payload.get("run_type"), "renn_zeit": renn_zeit_val,
                                     "disqualified": web_item_payload.get("disqualified"),
                                     "notes": web_item_payload.get("notes"),
                                     "updated_at": datetime.datetime.now().isoformat()}
                recorded_at_str = web_item_payload.get("recorded_at")
                if recorded_at_str:
                    try:
                        local_data_format["timestamp_messung"] = datetime.datetime.fromisoformat(
                            str(recorded_at_str).replace("Z", "+00:00")).isoformat()
                    except (ValueError, TypeError):
                        pass
                local_data_format = {k: v for k, v in local_data_format.items() if v is not None}
                self.data_items[item_id_from_web] = {"data": local_data_format, "status": STATUS_SYNCED,
                                                     "_synced_to_website": True, "original_data_snapshot": None,
                                                     "data_before_delete": None}
        self.refresh_treeview_display_fully()
        self.broadcast_data_update()

    def _sort_by_column(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = True
        self.refresh_treeview_display_fully()

    def refresh_treeview_display_fully(self):
        if not self.tree or not self.winfo_exists(): return

        for col_id in self.tree_columns:
            text = self.tree.heading(col_id, "text").replace(" ▲", "").replace(" ▼", "")
            if col_id == self.sort_column:
                text += " ▲" if not self.sort_reverse else " ▼"
            self.tree.heading(col_id, text=text)

        selected_iids = self.tree.selection()
        focused_iid = self.tree.focus()
        for i in self.tree.get_children(""): self.tree.delete(i)

        with self.data_lock:
            search_term = self.search_var.get().lower()
            filtered_item_ids = []
            if search_term:
                for item_id, details in self.data_items.items():
                    values_tuple = self._create_tree_item_values(item_id, details)
                    values_str = ' '.join(map(str, values_tuple)).lower()
                    if search_term in values_str:
                        filtered_item_ids.append(item_id)
            else:
                filtered_item_ids = list(self.data_items.keys())

            def make_naive(dt_val):
                if isinstance(dt_val, datetime.datetime) and dt_val.tzinfo:
                    return dt_val.replace(tzinfo=None)
                return dt_val

            def get_sort_key(item_id_key: str):
                if item_id_key not in self.data_items: return datetime.datetime.min
                data = self.data_items[item_id_key].get('data', {})

                if self.sort_column == "timestamp_combined":
                    ts_str = data.get('timestamp_messung') or data.get('updated_at')
                    if ts_str:
                        try:
                            return make_naive(datetime.datetime.fromisoformat(str(ts_str).replace("Z", "+00:00")))
                        except (TypeError, ValueError):
                            return datetime.datetime.min
                    return datetime.datetime.min
                elif self.sort_column == "start_number":
                    try:
                        return int(data.get('start_nummer', 0))
                    except (ValueError, TypeError):
                        return 0
                elif self.sort_column == "racer_name":
                    sn = str(data.get("start_nummer", ""))
                    return self.racer_names_by_start_number.get(sn, "zzzz")
                elif self.sort_column == "time_required":
                    return float(data.get('renn_zeit', 99999.0) or 99999.0)
                return datetime.datetime.min

            sorted_item_ids = sorted(filtered_item_ids, key=get_sort_key, reverse=self.sort_reverse)

            for item_id in sorted_item_ids:
                item_details = self.data_items[item_id]
                values = self._create_tree_item_values(item_id, item_details)
                tag = item_details.get("status", "")
                self.tree.insert("", "end", iid=item_id, values=values, tags=(tag,))

        if selected_iids:
            valid_selection = [sid for sid in selected_iids if self.tree.exists(sid)]
            if valid_selection: self.tree.selection_set(valid_selection)
        if focused_iid and self.tree.exists(focused_iid): self.tree.focus(focused_iid)

    def show_previous_versions(self):
        if not self.versions:
            messagebox.showinfo("Info", "Keine Snapshots vorhanden.", parent=self)
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Gesicherte Snapshots")
        dialog.geometry("800x600")
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes("-topmost", True)

        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="Gespeicherte Snapshots", font=ctk.CTkFont(size=14, weight="bold")).pack(
            pady=(0, 10))

        listbox_frame = ctk.CTkScrollableFrame(main_frame, height=300)
        listbox_frame.pack(pady=5, padx=5, fill="both", expand=True)

        vlb = tk.Listbox(listbox_frame, selectmode="single", exportselection=False, font=ctk.CTkFont(size=12),
                         relief="sunken", borderwidth=1, bg=self._get_theme_color("CTkFrame", "fg_color"),
                         fg=self._get_theme_color("CTkLabel", "text_color"),
                         selectbackground=self._get_theme_color("CTkButton", "fg_color"),
                         selectforeground=self._get_theme_color("CTkButton", "text_color"), highlightthickness=0,
                         activestyle="none")
        vlb.pack(fill="both", expand=True)

        for i, version_info in enumerate(reversed(self.versions)):
            version_num_display = len(self.versions) - i
            timestamp = version_info.get('timestamp', 'N/A')
            num_entries = len(version_info.get('data_snapshot', []))
            version_type_raw = version_info.get('type', 'unbekannt')
            type_display_map = {"internal_save": "Manueller Snapshot", "pre_pull_backup": "Backup (Vor Website-Pull)",
                                "pre_push_backup": "Backup (Vor Website-Push)"}
            type_display = type_display_map.get(version_type_raw, version_type_raw.replace("_", " ").title())
            vlb.insert(tk.END,
                       f"Version {version_num_display} ({timestamp}) - {num_entries} Einträge - Typ: {type_display}")

        if vlb.size() > 0: vlb.selection_set(0)

        def get_selected_version_index():
            selection_indices = vlb.curselection()
            if not selection_indices:
                messagebox.showwarning("Auswahl Erforderlich", "Bitte Version auswählen.", parent=dialog)
                return None
            return len(self.versions) - 1 - selection_indices[0]

        def on_revert():
            idx = get_selected_version_index()
            if idx is None: return
            details = self.versions[idx]
            if messagebox.askyesno("Version Wiederherstellen",
                                   f"Version {len(self.versions) - idx} ({details['timestamp']}) komplett laden?\n\nAlle aktuellen, nicht gespeicherten Änderungen gehen verloren.",
                                   parent=dialog, icon=messagebox.WARNING):
                self.revert_to_version(idx)
                dialog.destroy()

        def on_merge():
            idx = get_selected_version_index()
            if idx is None: return
            self.open_merge_view_for_version(idx)
            dialog.destroy()

        button_bar = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_bar.pack(pady=(10, 5), padx=5, fill="x", expand=True)
        revert_button = ctk.CTkButton(button_bar, text="Ausgewählte Version Laden (Überschreiben)", command=on_revert)
        revert_button.pack(side="left", padx=5, expand=True)
        merge_button = ctk.CTkButton(button_bar, text="Mit Aktuellen Daten Mischen", command=on_merge,
                                     fg_color="darkorange")
        merge_button.pack(side="left", padx=5, expand=True)
        cancel_button = ctk.CTkButton(button_bar, text="Abbrechen", command=dialog.destroy, fg_color="gray50")
        cancel_button.pack(side="left", padx=5, expand=True)

    def open_merge_view_for_version(self, version_index: int):
        version_to_load = self.versions[version_index]
        with self.data_lock:
            local_data_copy = copy.deepcopy(self.data_items)

        remote_data_dict = {}
        for item_snapshot in version_to_load.get("data_snapshot", []):
            item_id = item_snapshot.get("_id_internal")
            if not item_id: continue

            data_content = {k: v for k, v in item_snapshot.items() if not k.startswith('_')}
            remote_data_dict[item_id] = {
                "data": data_content,
                "status": item_snapshot.get("_status_at_version"),
                "_synced_to_website": item_snapshot.get("_synced_to_website_at_version", False)
            }

        version_num = version_index + 1
        MergeView(self, local_data=local_data_copy, remote_data=remote_data_dict, source_name=f"Snapshot {version_num}",
                  callback_on_finish=self._finalize_merge)

    def _finalize_merge(self, resolved_data: Dict[str, Dict]):
        """
        Takes the merge result (keyed by composite key) and rebuilds the
        main data_items dictionary with the correct final IDs.
        """
        final_data_items = {}

        # 'resolved_data' is keyed by "start_number-round_number" or a technical ID
        for key, details in resolved_data.items():
            final_id = None

            # Check if we used composite keys (indicated by the presence of the maps)
            if hasattr(self, 'merge_remote_map') and hasattr(self, 'merge_local_map'):
                # Prioritize the remote ID (from server or snapshot)
                final_id = self.merge_remote_map.get(key)

                if not final_id:
                    # If no remote ID, it was a local-only item. Use its original ID.
                    final_id = self.merge_local_map.get(key)

                if not final_id:
                    print(f"WARNUNG: Konnte keine finale ID für den Schlüssel '{key}' finden. Erzeuge neue UUID.")
                    final_id = str(uuid.uuid4())
            else:
                # Fallback for old merge logic that used technical IDs directly
                final_id = key

            final_data_items[final_id] = details

        with self.data_lock:
            self.data_items = final_data_items

        # Clean up the temporary maps if they exist
        if hasattr(self, 'merge_local_map'):
            del self.merge_local_map
        if hasattr(self, 'merge_remote_map'):
            del self.merge_remote_map

        self.refresh_treeview_display_fully()
        self.broadcast_data_update()
        messagebox.showinfo("Merge Abgeschlossen",
                            "Die Daten wurden erfolgreich zusammengeführt.\n\n"
                            "Wenn die Quelle die Website war, wird ein 'Push' empfohlen, um die Änderungen zu synchronisieren.",
                            parent=self)

    def revert_to_version(self, version_index: int):
        if not (0 <= version_index < len(self.versions)):
            messagebox.showerror("Fehler", f"Ungültiger Index ({version_index}).", parent=self)
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
    if not os.path.exists("common"): os.makedirs("common")
    if not os.path.exists("common/__init__.py"): open("common/__init__.py", "w").close()
    if not os.path.exists("common/constants.py"):
        with open("common/constants.py", "w", encoding='utf-8') as f:
            f.write("""
STATUS_NEW = 'new'
STATUS_MODIFIED = 'modified'
STATUS_DELETED = 'deleted'
STATUS_SYNCED = 'synced'
STATUS_COMPLETE = 'complete'
STATUS_SYNCED_LOCAL = 'saved internally'
COLOR_STATUS_NEW_BG = '#c8e6c9'
COLOR_STATUS_MODIFIED_BG = '#fff9c4'
COLOR_STATUS_DELETED_FG = '#e57373'
COLOR_STATUS_COMPLETE_BG = '#bbdefb'
COLOR_STATUS_SYNCED_LOCAL_BG = '#cfd8dc'
ROUND_NAMES = ["PR", "H1", "H2"]
""")
    if not os.path.exists("common/data_models.py"):
        with open("common/data_models.py", "w", encoding='utf-8') as f:
            f.write("""
import datetime
import uuid
from typing import Optional, Any, Dict

class ScanLogEntry:
    pass

class MainDataEntry(dict):
    pass

class DisplayableMainData(dict):
    pass
""")
    app = MainApp()
    app.mainloop()