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
from dataclasses import asdict

HOST = '0.0.0.0'
PORT = 65432
SETTINGS_FILE = "app_settings.json"
VERSIONS_FILE = "main_app/versions.json"


# In main_app.py ersetzen

def handle_client(conn: socket.socket, addr: Any, app_instance: 'MainApp'):
    print(f"Verbunden mit {addr}")

    client_send_queue: queue.Queue[Optional[str]] = queue.Queue()
    app_instance.add_client_queue(addr, client_send_queue)

    # KEIN TIMEOUT HIER SETZEN!
    # conn.settimeout(1)

    send_thread = threading.Thread(target=send_to_client_from_queue, args=(conn, client_send_queue, addr), daemon=True)
    send_thread.start()

    buffer = ""
    try:
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    print(f"Verbindung mit {addr} geschlossen (Client hat geschlossen).")
                    break

                buffer += data.decode('utf-8')

                # Verarbeite alle vollständigen Nachrichten im Puffer
                while "$END$" in buffer:
                    message, buffer = buffer.split("$END$", 1)
                    if message:
                        # Die message_receive Funktion verarbeitet eine Scan-Nachricht
                        message_receive(message)

    except ConnectionResetError:
        print(f"Verbindung mit {addr} unerwartet geschlossen.")
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

            message_with_ender = message_to_client + "$END$"
            conn.sendall(message_with_ender.encode('utf-8'))

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
    from common.data_models import RaceRun, Racer
except ImportError as e:
    print(f"FEHLER: common-Dateien nicht gefunden. {e}")
    STATUS_NEW, STATUS_MODIFIED, STATUS_DELETED, STATUS_SYNCED, STATUS_SYNCED_LOCAL, STATUS_COMPLETE = "new", "modified", "deleted", "synced", 'saved internally', "complete"
    COLOR_STATUS_NEW_BG, COLOR_STATUS_MODIFIED_BG, COLOR_STATUS_DELETED_FG, COLOR_STATUS_COMPLETE_BG, COLOR_STATUS_SYNCED_LOCAL_BG = "lightgreen", "lightyellow", "red", "lightblue", "lightgrey"
    ROUND_NAMES = ["PR", "H1", "H2"]


    class RaceRun:
        pass


    class Racer:
        pass

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class CustomTwoButtonDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, message: str, button_1_text: str, button_2_text: str):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._choice = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure((0, 1), weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        label = ctk.CTkLabel(main_frame, text=message, wraplength=340, justify="left", font=ctk.CTkFont(size=14),
                             text_color="red", fg_color="white")
        label.grid(row=0, column=0, columnspan=4, padx=20, pady=(20, 10), sticky="ew")
        button1 = ctk.CTkButton(main_frame, text=button_1_text,
                                command=lambda: self._set_choice_and_close(button_1_text))
        button1.grid(row=1, column=0, padx=(20, 10), pady=(10, 20), sticky="ew")
        button2 = ctk.CTkButton(main_frame, text=button_2_text,
                                command=lambda: self._set_choice_and_close(button_2_text))
        button2.grid(row=1, column=1, padx=(10, 20), pady=(10, 20), sticky="ew")
        self.after(100, self.lift)

    def _set_choice_and_close(self, choice: str):
        self._choice = choice
        self.destroy()

    def _on_closing(self):
        self._choice = None
        self.destroy()

    def get_choice(self) -> Optional[str]:
        return self._choice


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
        self.resolutions: Dict[str, str] = {}
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
        self._on_item_selected()

    def _prepare_merge_data(self):
        all_ids = set(self.local_data.keys()) | set(self.remote_data.keys())
        jump_over_ids = []
        for item_id in sorted(list(all_ids)):
            if item_id in jump_over_ids: continue
            is_local = item_id in self.local_data
            is_remote = item_id in self.remote_data
            entry = {'local': self.local_data.get(item_id), 'remote': self.remote_data.get(item_id)}
            if is_local and not is_remote:
                entry['status'] = 'local_only'
                self.resolutions[item_id] = 'local'
                for key, value in self.remote_data.items():
                    value = value['data']
                    if value.get('renn_zeit') == entry['local']['data'].get('renn_zeit') and value['start_nummer'] == \
                            entry['local']['data']['start_nummer'] and value['timestamp_messung'] == \
                            entry['local']['data']['timestamp_messung'] and value['round_number'] == \
                            entry['local']['data']['round_number']:
                        self.resolutions[item_id] = 'remote' if "Website" in self.source_name else 'local'
                        entry['status'] = 'identical'
                        entry["remote"] = self.remote_data.get(key)
                        jump_over_ids.append(key)
            elif not is_local and is_remote:
                entry['status'] = 'remote_only'
                self.resolutions[item_id] = 'remote'
                for key, value in self.local_data.items():
                    value = value['data']
                    if value.get('renn_zeit') == entry['remote']['data'].get('renn_zeit') and value['start_nummer'] == \
                            entry['remote']['data']['start_nummer'] and value['timestamp_messung'] == \
                            entry['remote']['data']['timestamp_messung'] and value['round_number'] == \
                            entry['remote']['data']['round_number']:
                        self.resolutions[item_id] = 'remote' if "Website" in self.source_name else 'local'
                        entry['status'] = 'identical'
                        entry["local"] = self.local_data.get(key)
                        jump_over_ids.append(key)
            else:
                local_data_for_compare = {k: v for k, v in entry['local']['data'].items() if
                                          k not in ['updated_at', 'timestamp_messung', 'disqualified', 'notes']}
                remote_data_for_compare = {k: v for k, v in entry['remote']['data'].items() if
                                           k not in ['updated_at', 'timestamp_messung', 'disqualified', 'notes']}
                if not remote_data_for_compare.get('renn_zeit'): remote_data_for_compare.pop('renn_zeit', None)
                if not local_data_for_compare.get('renn_zeit'): local_data_for_compare.pop('renn_zeit', None)
                if json.dumps(local_data_for_compare, sort_keys=True) == json.dumps(remote_data_for_compare,
                                                                                    sort_keys=True):
                    entry['status'] = 'identical'
                    self.resolutions[item_id] = 'remote' if "Website" in self.source_name else 'local'
                else:
                    entry['status'] = 'conflict'
            self.merge_items[item_id] = entry
        self._refresh_listbox()

    def _refresh_listbox(self):
        current_idx = self.item_listbox.curselection()
        self.item_listbox.delete(0, tk.END)
        status_map = {'conflict': ("[Konflikt]", "#FF8C00"), 'local_only': ("[Nur Lokal]", "#4682B4"),
                      'remote_only': ("[Nur Quelle]", "#32CD32"), 'identical': ("[Identisch]", "gray")}
        for item_id, details in self.merge_items.items():
            status_text, color = status_map.get(details['status'], ("[Unbekannt]", "white"))
            item_data = details['local'] or details['remote']
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
            self.item_listbox.itemconfig(tk.END, {'fg': 'gray50' if resolution == 'discard' else color})
        if current_idx: self.item_listbox.selection_set(current_idx[0])

    def _on_item_selected(self, event=None):
        sel_indices = self.item_listbox.curselection()
        if not sel_indices:
            for btn in [self.btn_keep_local, self.btn_keep_remote, self.btn_discard]: btn.configure(state="disabled")
            return
        item_id = list(self.merge_items.keys())[sel_indices[0]]
        item_details = self.merge_items[item_id]
        for w in self.local_details_frame.winfo_children(): w.destroy()
        for w in self.remote_details_frame.winfo_children(): w.destroy()
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
        for i, (key, val) in enumerate(data.items()):
            val_str = str(val if val is not None else "-")
            highlight_color = None
            if secondary_data and str(val) != str(secondary_data.get('data', {}).get(key)):
                highlight_color = ("#FFDDC1", "#5B3E2D")
            ctk.CTkLabel(parent_frame, text=f"{key}:", font=ctk.CTkFont(weight="bold")).grid(row=i, column=0,
                                                                                             sticky="w", padx=5, pady=2)
            ctk.CTkLabel(parent_frame, text=val_str, wraplength=250, fg_color=highlight_color).grid(row=i, column=1,
                                                                                                    sticky="w", padx=5,
                                                                                                    pady=2)

    def _resolve_conflict(self, choice: str):
        sel_indices = self.item_listbox.curselection()
        if sel_indices:
            self.resolutions[list(self.merge_items.keys())[sel_indices[0]]] = choice
            self._refresh_listbox()

    def _apply_merge(self):
        final_data = {}
        for item_id, details in self.merge_items.items():
            resolution = self.resolutions.get(item_id)
            if resolution == 'discard': continue
            chosen_details = copy.deepcopy(details.get(resolution))
            if chosen_details:
                if "Website" in self.source_name:
                    chosen_details['_synced_to_website'] = (resolution == 'remote')
                    chosen_details['status'] = STATUS_SYNCED if resolution == 'remote' else STATUS_MODIFIED
                else:
                    chosen_details['_synced_to_website'] = False
                    chosen_details['status'] = STATUS_SYNCED_LOCAL
                final_data[item_id] = chosen_details
        if self.callback_on_finish: self.callback_on_finish(final_data)
        self.destroy()


class MainApp(ctk.CTk):
    _instance: Optional['MainApp'] = None

    def __init__(self):
        super().__init__()
        MainApp._instance = self
        self.title("Main App")
        self.geometry("1450x800")

        self.data_items: Dict[str, RaceRun] = {}
        self.racers_by_start_number: Dict[str, Racer] = {}
        self.data_lock = threading.RLock()

        self.auto_sync_timer: Optional[str] = None
        self.auto_sync_paused_due_to_error: bool = False
        self.auto_sync_in_progress: bool = False

        self.settings_data: Dict[str, Any] = {
            "Runde": "PR", "Arduino Port": "Keiner", "Server Adresse (für API)": "localhost",
            "API Endpoint Website": "http://localhost:8000/api/", "username": "Josua", "password": "hallo1234",
            "Auto-Sync Aktiv": False
        }
        self.load_settings()
        self.auto_sync_enabled = self.settings_data.get("Auto-Sync Aktiv", False)

        self.setting_widgets: Dict[str, ctk.CTkBaseClass] = {}
        self.versions: List[Dict[str, Any]] = []
        self.load_versions()
        self.clients: Dict[Any, queue.Queue[Optional[str]]] = {}
        self.client_management_lock = threading.Lock()
        self.headers: Optional[Dict[str, str]] = None

        self.sort_column = "timestamp_combined"
        self.sort_reverse = True

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.top_button_frame = ctk.CTkFrame(self.main_container, height=60)
        self.top_button_frame.pack(fill="x", pady=(0, 10))

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
                                                          self.open_pull_selection_dialog), fg_color="red",
                                                      state="disabled")
        self.pull_from_website_button.pack(side="left", padx=5, pady=5)
        self.connect_to_website_button = ctk.CTkButton(self.top_button_frame, text="Connect to Website",
                                                       command=lambda: self.button_threads(self.start_connection),
                                                       fg_color="red")
        self.connect_to_website_button.pack(side="left", padx=5, pady=5)

        self.sync_status_label = ctk.CTkLabel(self.top_button_frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.sync_status_label.pack(side="right", padx=10, pady=5)
        self._update_sync_status_label()

        self.tab_view = ctk.CTkTabview(self.main_container, fg_color="transparent")
        self.tab_view.pack(fill="both", expand=True)
        self.data_tab = self.tab_view.add("Datenansicht")
        self.settings_tab = self.tab_view.add("Einstellungen")
        self.tree: Optional[ttk.Treeview] = None
        self.setup_data_view(self.data_tab)
        self.setup_settings_view(self.settings_tab)

        self.tree_context_menu = tk.Menu(self, tearoff=0, font=ctk.CTkFont(size=12))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        threading.Thread(target=connect, args=(self,), daemon=True).start()
        threading.Thread(target=self.arduino_connection, daemon=True).start()
        threading.Thread(target=self.start_connection, daemon=True).start()

    def button_threads(self, function):
        threading.Thread(target=function, daemon=True).start()

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.settings_data.update(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Fehler beim Laden der Einstellungsdatei: {e}")

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings_data, f, indent=4)
            messagebox.showinfo("Gespeichert", "Einstellungen wurden erfolgreich gespeichert.",
                                parent=self.settings_tab)
        except IOError as e:
            messagebox.showerror("Fehler beim Speichern",
                                 f"Die Einstellungen konnten nicht in {SETTINGS_FILE} gespeichert werden.")

    # ... (Methoden: load_versions, save_versions, connect_to_website, start_connection, etc. bleiben gleich)
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
        if not self.racers_by_start_number:
            current_racers = self.get_data_website(f"{self.settings_data['API Endpoint Website']}racers/")
            if current_racers:
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

    def push_data_website(self, data: Dict, run_identifier=1) -> tuple[bool, Optional[str]]:
        print("Pushing data:", data)
        try:
            base_url = f"{self.settings_data['API Endpoint Website']}raceruns/"
            response = None

            # GEÄNDERT: Payload-Erstellung ist konsistenter
            payload = {
                "racer_start_number": str(data.get("start_nummer")),
                "time_in_seconds": data.get("renn_zeit"),
                "run_identifier": run_identifier,
                "run_type": data.get("round_number"),
                "recorded_at": data.get('timestamp_messung'),
                "disqualified": data.get('disqualified', False),
                "notes": data.get('notes')
            }

            item_id = data.get('app_item_id')  # ID aus der App, nicht zwangsläufig Server-ID

            if data.get('_action') == "upsert":
                response = requests.post(base_url, json=payload, headers=self.headers)
            elif data.get('_action') == "delete":
                response = requests.delete(f"{base_url}{item_id}/", headers=self.headers)
            elif data.get('_action') == "changed":
                response = requests.patch(f"{base_url}{item_id}/", json=payload, headers=self.headers)
            else:
                print(f"Error: Unbekannte Aktion '{data.get('_action')}'")
                return False, item_id

            response.raise_for_status()
            print("Push erfolgreich!", response.status_code)
            return True, item_id

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

    # ... (Methoden: _update_racer_data_store, arduino_connection, on_closing, etc. bleiben gleich) ...
    def _update_racer_data_store(self, new_racers_list: List[Dict[str, Any]], from_website_pull: bool = True):
        self.racers_by_start_number.clear()
        for racer_data in new_racers_list:
            start_num = racer_data.get("start_number")
            if start_num:
                racer = Racer(
                    start_number=str(start_num),
                    full_name=racer_data.get("full_name", "Unbekannt"),
                    soapbox_class_display=racer_data.get("soapbox_class_display", "N/A")
                )
                self.racers_by_start_number[str(start_num)] = racer

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
                                try:
                                    with open("main_app/run_times.json", "r") as f:
                                        run_times = json.load(f)
                                        run_times.append(run_time)
                                    with open("main_app/run_times.json", "w") as f:
                                        json.dump(run_times, f)
                                except FileNotFoundError:
                                    with open("main_app/run_times.json", "w") as f:
                                        json.dump([], f)
                                with self.data_lock:
                                    if not self.tree: continue
                                    children = self.tree.get_children("")
                                    target_item_id = None
                                    for item_id_check in reversed(children):
                                        item = self.data_items.get(item_id_check)
                                        if item and item.renn_zeit is None:
                                            target_item_id = item_id_check
                                            break

                                    if target_item_id:
                                        item = self.data_items[target_item_id]
                                        update_payload = {"renn_zeit": run_time}
                                        self.after(0, self.update_tree_item, target_item_id, update_payload)
                                        print(
                                            f"Arduino: Rennzeit {run_time} für Item {target_item_id} (Startnr: {item.start_nummer}) gesetzt.")
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

    # ... (Methoden: _format_item_for_client, _get_all_data_for_clients_payload, etc. bleiben gleich) ...
    def _format_item_for_client(self, item: RaceRun) -> Optional[str]:
        racer = self.racers_by_start_number.get(item.start_nummer)
        racer_name_str = racer.full_name if racer else "-"
        racer_class_str = racer.soapbox_class_display if racer else "N/A"

        round_number_str = str(item.round_number)
        renn_zeit_raw = item.renn_zeit
        renn_zeit_str = f"{renn_zeit_raw:.3f}" if isinstance(renn_zeit_raw, (float, int)) else ""

        ts_to_send_raw = item.timestamp_messung
        timestamp_display_str = ""
        if ts_to_send_raw:
            try:
                dt_obj = datetime.datetime.fromisoformat(ts_to_send_raw.replace(" ", "T"))
                timestamp_display_str = dt_obj.strftime("%H:%M:%S (%d.%m.%Y)")
            except ValueError:
                timestamp_display_str = str(ts_to_send_raw)

        return f"{item.app_item_id}$#{item.start_nummer}$#{racer_name_str}$#{racer_class_str}$#{round_number_str}$#{renn_zeit_str}$#{timestamp_display_str}"

    def _get_all_data_for_clients_payload(self) -> str:
        all_items_formatted_strings = []
        with self.data_lock:
            for item in self.data_items.values():
                if item.status == STATUS_DELETED: continue
                formatted_item = self._format_item_for_client(item)
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
        if not self.racers_by_start_number: return "RACER_DATA_EMPTY"
        payload_parts = [f"{sn}:{racer.full_name}:{racer.soapbox_class_display}" for sn, racer in
                         self.racers_by_start_number.items()]
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
                item = self.data_items.get(item_id_updated)
                if item and item.status != STATUS_DELETED:
                    formatted_item = self._format_item_for_client(item)
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
        # unverändert
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

        # GEÄNDERT: Neue Spalte 'push_action'
        self.tree_columns = ("push_action", "status_indicator", "timestamp_combined", "start_number", "racer_name",
                             "soapbox_class", "round_number",
                             "time_required", "scan_id_col")
        self.tree = ttk.Treeview(tree_container, columns=self.tree_columns, show="headings")
        vsb = ctk.CTkScrollbar(tree_container, command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ctk.CTkScrollbar(tree_container, command=self.tree.xview, orientation="horizontal")
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side="left", fill="both", expand=True)

        for col_id in ["timestamp_combined", "start_number", "racer_name", "soapbox_class", "time_required"]:
            self.tree.heading(col_id, command=lambda c=col_id: self._sort_by_column(c))

        self.tree.heading("push_action", text="", anchor=tk.CENTER)
        self.tree.heading("status_indicator", text="S", anchor=tk.W)
        self.tree.heading("timestamp_combined", text="Zeitstempel ▼", anchor=tk.W)
        self.tree.heading("start_number", text="Startnr.", anchor=tk.W)
        self.tree.heading("racer_name", text="Name", anchor=tk.W)
        self.tree.heading("soapbox_class", text="Kistenklasse", anchor=tk.W)
        self.tree.heading("round_number", text="Runde", anchor=tk.CENTER)
        self.tree.heading("time_required", text="Rennzeit", anchor=tk.E)
        self.tree.heading("scan_id_col", text="Scan ID", anchor=tk.W)

        self.tree.column("push_action", width=30, minwidth=30, stretch=tk.NO, anchor=tk.CENTER)
        self.tree.column("status_indicator", width=30, minwidth=30, stretch=tk.NO, anchor=tk.CENTER)
        self.tree.column("timestamp_combined", width=160, minwidth=130, stretch=tk.YES)
        self.tree.column("start_number", width=80, minwidth=60, anchor=tk.W, stretch=tk.NO)
        self.tree.column("racer_name", width=180, minwidth=120, stretch=tk.YES)
        self.tree.column("soapbox_class", width=150, minwidth=100, stretch=tk.YES)
        self.tree.column("round_number", width=60, minwidth=50, anchor=tk.CENTER, stretch=tk.NO)
        self.tree.column("time_required", width=100, minwidth=80, anchor=tk.E, stretch=tk.NO)
        self.tree.column("scan_id_col", width=120, minwidth=100, stretch=tk.NO)

        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-1>", self.on_tree_left_click)
        self._apply_treeview_styling()

    def _apply_treeview_styling(self):
        style = ttk.Style(self)
        style.theme_use("default")
        frame_fg = self._get_theme_color("CTkFrame", "fg_color")
        label_text = self._get_theme_color("CTkLabel", "text_color")
        btn_fg = self._get_theme_color("CTkButton", "fg_color")
        btn_text_sel = self._get_theme_color("CTkButton", "text_color")
        btn_hover = self._get_theme_color("CTkButton", "hover_color")

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

        style.configure("pushable.Treeview", foreground="#0078D7")

    def _get_theme_color(self, widget_name: str, color_type: str, default_light: str = "#FFFFFF",
                         default_dark: str = "#000000") -> str:
        try:
            val = ctk.ThemeManager.theme[widget_name][color_type]
            is_dark = ctk.get_appearance_mode().lower() == "dark"
            return str(val[1] if is_dark else val[0]) if isinstance(val, (list, tuple)) else str(val)
        except Exception:
            return default_dark if ctk.get_appearance_mode().lower() == "dark" else default_light

    def _get_available_ports(self) -> List[str]:
        return ["Keiner"] + [port.device for port in serial.tools.list_ports.comports()]

    # GEÄNDERT: UI für Auto-Sync-Schalter hinzugefügt
    def setup_settings_view(self, parent_frame: ctk.CTkFrame):
        settings_scroll_frame = ctk.CTkScrollableFrame(parent_frame, label_text="App Einstellungen")
        settings_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.setting_widgets.clear()

        for key, value in self.settings_data.items():
            setting_frame = ctk.CTkFrame(settings_scroll_frame)
            setting_frame.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(setting_frame, text=f"{key}:", width=220, anchor="w").pack(side="left", padx=(0, 10))
            widget: Optional[ctk.CTkBaseClass] = None

            if key == "Auto-Sync Aktiv":
                widget = ctk.CTkSwitch(setting_frame, text="")
                if value:
                    widget.select()
            elif key == "Arduino Port":
                widget = ctk.CTkComboBox(setting_frame, values=self._get_available_ports())
                widget.set(str(value))
            elif key == "Runde":
                widget = ctk.CTkComboBox(setting_frame, values=ROUND_NAMES)
                widget.set(str(value))
            else:
                widget = ctk.CTkEntry(setting_frame)
                widget.insert(0, str(value))

            if widget:
                widget.pack(side="left", fill="x", expand=True, padx=5)
                self.setting_widgets[key] = widget

        save_button = ctk.CTkButton(settings_scroll_frame, text="Einstellungen Speichern",
                                    command=self._apply_and_save_settings)
        save_button.pack(pady=(20, 5), padx=5)

    # GEÄNDERT: Speichert und wendet Auto-Sync-Einstellung an
    def _apply_and_save_settings(self):
        print("Speichere Einstellungen...")
        for key, widget in self.setting_widgets.items():
            new_value = None
            if isinstance(widget, ctk.CTkSwitch):
                new_value = bool(widget.get())
            elif isinstance(widget, (ctk.CTkEntry, ctk.CTkComboBox)):
                new_value = widget.get()

            if new_value is not None:
                self.settings_data[key] = new_value

        # Auto-Sync-Zustand aktualisieren
        new_auto_sync_state = self.settings_data.get("Auto-Sync Aktiv", False)
        if self.auto_sync_enabled != new_auto_sync_state:
            self.auto_sync_enabled = new_auto_sync_state
            if self.auto_sync_enabled:
                # Beim Re-Aktivieren den Fehler-Pause-Zustand zurücksetzen
                self.auto_sync_paused_due_to_error = False
                print("Auto-Sync wurde aktiviert. Ausstehende Änderungen werden synchronisiert.")
                self._trigger_auto_sync()  # Versuch, sofort zu synchronisieren
            else:
                print("Auto-Sync wurde deaktiviert.")

        self._update_sync_status_label()
        self.save_settings()

    # ... (Methoden _get_status_indicator bis open_manual_entry_dialog bleiben gleich) ...
    def _get_status_indicator(self, status: Optional[str]) -> str:
        return {STATUS_NEW: "➕", STATUS_MODIFIED: "✏️", STATUS_DELETED: "🗑️", STATUS_SYNCED: "✔️",
                STATUS_SYNCED_LOCAL: "💾", STATUS_COMPLETE: "🏁"}.get(status or "", "?")

    # GEÄNDERT: Fügt Push-Symbol hinzu
    def _create_tree_item_values(self, item: RaceRun) -> tuple:
        # Push-Symbol nur anzeigen, wenn nicht synchronisiert
        push_symbol = "📤" if item.status not in [STATUS_SYNCED] else ""

        status_ind = self._get_status_indicator(item.status)
        try:
            dt_obj = datetime.datetime.fromisoformat(item.timestamp_messung.replace(" ", "T"))
            ts_combined_display = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            ts_combined_display = str(item.timestamp_messung)[:19]

        renn_zeit_display = f"{item.renn_zeit:.3f}s" if isinstance(item.renn_zeit, (float, int)) else "-"
        scan_id_val = item.zugeordneter_scan_id or item.scan_id
        scan_id_display = (str(scan_id_val)[:8] + "...") if scan_id_val and len(str(scan_id_val)) > 8 else str(
            scan_id_val or "-")

        racer = self.racers_by_start_number.get(item.start_nummer)
        racer_name_display = racer.full_name if racer else "Startnr. unbekannt!"
        soapbox_class_display = racer.soapbox_class_display if racer else "N/A"

        return (
            push_symbol,  # NEU
            status_ind,
            ts_combined_display,
            item.start_nummer or "-",
            racer_name_display,
            soapbox_class_display,
            item.round_number or "-",
            renn_zeit_display,
            scan_id_display
        )

    # GEÄNDERT: Ruft Auto-Sync auf
    def add_item_to_tree(self, current_data_dict: Dict[str, Any], item_id: Optional[str] = None) -> str:
        new_item_id = item_id or str(uuid.uuid4())
        with self.data_lock:
            new_run = RaceRun(
                app_item_id=new_item_id,
                start_nummer=str(current_data_dict.get("start_nummer", "")),
                round_number=current_data_dict.get("round_number", self.settings_data.get("Runde", "PR")),
                timestamp_messung=current_data_dict.get("timestamp_messung", datetime.datetime.now().isoformat()),
                status=STATUS_NEW,
                # ... andere Felder ...
            )
            self.data_items[new_item_id] = new_run

        self.after(0, self.refresh_treeview_display_fully)
        self.broadcast_data_update(new_item_id)
        self._trigger_auto_sync()  # NEU
        return new_item_id

    # GEÄNDERT: Ruft Auto-Sync auf
    def update_tree_item(self, item_id: str, new_data_dict: Dict[str, Any]):
        with self.data_lock:
            item = self.data_items.get(item_id)
            if not item or item.status == STATUS_DELETED: return

            # ... update logic ...
            if item.status in [STATUS_SYNCED, STATUS_SYNCED_LOCAL] and item.original_data_snapshot is None:
                item.original_data_snapshot = copy.deepcopy(item.to_data_dict())
            item.updated_at = datetime.datetime.now().isoformat()

            for key, value in new_data_dict.items():
                if hasattr(item, key): setattr(item, key, value)

            if item.status != STATUS_NEW: item.status = STATUS_MODIFIED
            if (item.start_nummer and item.renn_zeit is not None and item.status not in [STATUS_NEW, STATUS_SYNCED,
                                                                                         STATUS_DELETED,
                                                                                         STATUS_COMPLETE]):
                item.status = STATUS_COMPLETE

        self.after(0, self.refresh_treeview_display_fully)
        self.broadcast_data_update(item_id)
        self._trigger_auto_sync()  # NEU

    def open_manual_entry_dialog(self, item_id_to_edit: Optional[str] = None):
        # unverändert
        is_edit = item_id_to_edit is not None
        initial_data: Dict[str, Any] = {}

        if is_edit and item_id_to_edit:
            with self.data_lock:
                item_to_edit = self.data_items.get(item_id_to_edit)
                if not item_to_edit or item_to_edit.status == STATUS_DELETED:
                    messagebox.showinfo("Info", "Eintrag nicht bearbeitbar.", parent=self)
                    return
                initial_data = item_to_edit.to_data_dict()
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
        name_var = tk.StringVar(value="-")
        ctk.CTkLabel(dialog, text="Name:").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        l_name = ctk.CTkLabel(dialog, textvariable=name_var, anchor="w")
        l_name.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")

        row_idx += 1

        def _update_name_in_dialog_manual_entry(*args):
            sn = e_sn.get().strip()
            racer = self.racers_by_start_number.get(sn)
            if racer:
                name_var.set(f"{racer.full_name} ({racer.soapbox_class_display})")
            else:
                name_var.set("Startnummer unbekannt!")

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

            # Leere Rennzeit wird zu None
            if rz_str:
                try:
                    payload["renn_zeit"] = float(rz_str)
                except ValueError:
                    messagebox.showerror("Fehler", "Ungültige Rennzeit.", parent=dialog)
                    return
            else:
                payload["renn_zeit"] = None

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

    # ... (Methoden on_tree_left_click bis revert_item_changes_dialog bleiben gleich) ...
    def on_tree_left_click(self, event: tk.Event):
        if not self.tree: return

        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)

        # Prüfen, ob in die erste Spalte ('push_action') geklickt wurde
        if item_id and column_id == '#1':
            item_tags = self.tree.item(item_id, "tags")
            if "pushable" in item_tags:
                print(f"Push-Aktion für Item {item_id} ausgelöst.")
                self.push_single_item(item_id)

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
            item = self.data_items.get(item_id)
            if item:
                if item.status == STATUS_DELETED:
                    self.tree_context_menu.add_command(label="Wiederherstellen", command=self.restore_deleted_item)
                else:
                    self.tree_context_menu.add_command(label="Bearbeiten...", command=self.edit_selected_tree_item)

                # Option zum einzelnen Pushen im Kontextmenü beibehalten
                if item.status not in [STATUS_SYNCED]:
                    self.tree_context_menu.add_separator()
                    self.tree_context_menu.add_command(
                        label="Diesen Eintrag zur Website pushen",
                        command=lambda: self.push_single_item(self._get_id_for_context_action())
                    )

                if item.status != STATUS_DELETED:
                    self.tree_context_menu.add_separator()
                    self.tree_context_menu.add_command(label="Löschen", command=self.delete_selected_tree_item)

        if self.tree_context_menu.index(tk.END) is not None: self.tree_context_menu.tk_popup(event.x_root, event.y_root)

    def on_tree_double_click(self, event: tk.Event):
        if not self.tree: return
        item_id = self.tree.identify_row(event.y)
        if not item_id: return

        with self.data_lock:
            item = self.data_items.get(item_id)
            can_edit = item and item.status != STATUS_DELETED

        if can_edit:
            self.open_manual_entry_dialog(item_id_to_edit=item_id)

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

        with self.data_lock:
            item = self.data_items.get(item_id)
            can_edit = item and item.status != STATUS_DELETED

        if can_edit:
            self.open_manual_entry_dialog(item_id_to_edit=item_id)
        else:
            messagebox.showinfo("Info", "Element nicht bearbeitbar.", parent=self)
        self._context_menu_item_id = None

    # GEÄNDERT: Ruft Auto-Sync auf
    def delete_selected_tree_item(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return

        with self.data_lock:
            item_to_delete = self.data_items.get(item_id)
            if not item_to_delete or item_to_delete.status == STATUS_DELETED:
                return

            if item_to_delete.status == STATUS_NEW:
                del self.data_items[item_id]
            else:
                item_to_delete.data_before_delete = {"data": item_to_delete.to_data_dict(),
                                                     "original_status": item_to_delete.status}
                item_to_delete.status = STATUS_DELETED

        self.refresh_treeview_display_fully()
        self.broadcast_data_update(item_id, is_delete=True)
        self._trigger_auto_sync()  # NEU

    # GEÄNDERT: Ruft Auto-Sync auf
    def restore_deleted_item(self):
        item_id = self._get_id_for_context_action()
        if not item_id: return
        with self.data_lock:
            item = self.data_items.get(item_id)
            if not item or item.status != STATUS_DELETED or not item.data_before_delete:
                return

            restore_info = item.data_before_delete
            for key, value in restore_info.get("data", {}).items():
                if hasattr(item, key): setattr(item, key, value)
            item.status = restore_info.get("original_status", STATUS_MODIFIED)
            item.data_before_delete = None

        self.refresh_treeview_display_fully()
        self.broadcast_data_update(item_id)
        self._trigger_auto_sync()  # NEU

    # ... (Restliche Methoden bis zum Ende des Codes)
    def create_internal_snapshot(self, snapshot_type="internal_save", show_success_message=True) -> bool:
        with self.data_lock:
            items_to_include_in_version = []
            has_pending_actions = False
            for item in self.data_items.values():
                # Erstelle eine serialisierbare Kopie des Eintrags
                item_data_copy = item.to_data_dict()
                snapshot_entry = {
                    "_id_internal": item.app_item_id,
                    "_status_at_version": item.status,
                    "_synced_to_website_at_version": item._synced_to_website,
                    **item_data_copy
                }
                items_to_include_in_version.append(snapshot_entry)
                if item.status in [STATUS_NEW, STATUS_MODIFIED, STATUS_COMPLETE, STATUS_DELETED]:
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
                for item in self.data_items.values():
                    if item.status in [STATUS_NEW, STATUS_MODIFIED, STATUS_COMPLETE]:
                        item.status = STATUS_SYNCED_LOCAL
                        item.original_data_snapshot = None
                        items_marked_synced_count += 1
                if show_success_message:
                    msg = f"Snapshot Version {version_number} erstellt und in '{VERSIONS_FILE}' gespeichert.\n"
                    if items_marked_synced_count > 0: msg += f"{items_marked_synced_count} Element(e) als 'Gesichert' markiert."
                    messagebox.showinfo("Snapshot Erstellt", msg, parent=self)
                self.refresh_treeview_display_fully()

            return True

    def _check_for_double_data(self):
        seen = {}
        with self.data_lock:
            for item in self.data_items.values():
                if item.status == STATUS_DELETED:
                    continue
                key = (item.start_nummer, item.round_number)
                if key in seen:
                    dialog_message = (f"!!!DOPPELTER EINTRAG GEFUNDEN!!!\n"
                                      f"Startnummer: {item.start_nummer}\n"
                                      f"Runde: {item.round_number}\n"
                                      f"BEHEBE DIES UMGEHEND!")
                    dialog = CustomTwoButtonDialog(parent=self,
                                                   title="ACHTUNG: Doppelter Eintrag",
                                                   message=dialog_message,
                                                   button_1_text="Abbrechen",
                                                   button_2_text="Trotzdem Pushen")
                    self.wait_window(dialog)
                    return dialog.get_choice() == "Trotzdem Pushen"
                seen[key] = item.app_item_id
        return True

    def _collect_data_for_website_push(self) -> tuple[List[Dict[str, Any]], List[str], List[str]]:
        if not self._check_for_double_data():
            return [], [], []

        data_for_website = []
        items_to_mark_synced_after_push = []
        items_to_delete_permanently_after_push = []

        with self.data_lock:
            for item in self.data_items.values():
                payload = item.to_data_dict()
                payload["app_item_id"] = item.app_item_id

                if item.status == STATUS_DELETED:
                    if item.data_before_delete or item._synced_to_website:
                        payload["_action"] = "delete"
                        data_for_website.append(payload)
                        items_to_delete_permanently_after_push.append(item.app_item_id)
                elif not item._synced_to_website:
                    payload["_action"] = "upsert"
                    data_for_website.append(payload)
                    items_to_mark_synced_after_push.append(item.app_item_id)
                elif item.status in [STATUS_MODIFIED, STATUS_COMPLETE, STATUS_SYNCED_LOCAL]:
                    payload["_action"] = "changed"
                    data_for_website.append(payload)
                    items_to_mark_synced_after_push.append(item.app_item_id)

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

            self.after(0, self._finalize_website_push, not had_errors, successful_upsert_ids, successful_delete_ids)

        threading.Thread(target=_push_task, daemon=True).start()

    # GEÄNDERT: Reaktiviert Auto-Sync bei Erfolg
    def _finalize_website_push(self, all_success: bool, ids_successfully_upserted_on_server: List[str],
                               ids_successfully_deleted_on_server: List[str]):
        updated_count, deleted_count = 0, 0
        with self.data_lock:
            for item_id in ids_successfully_upserted_on_server:
                item = self.data_items.get(item_id)
                if item and item.status != STATUS_DELETED:
                    item.status = STATUS_SYNCED
                    item.original_data_snapshot = None
                    item._synced_to_website = True
                    updated_count += 1

            for item_id in ids_successfully_deleted_on_server:
                if item_id in self.data_items:
                    del self.data_items[item_id]
                    deleted_count += 1

        self.refresh_treeview_display_fully()
        self.broadcast_data_update()

        # NEU: Auto-Sync bei Erfolg reaktivieren
        if all_success and self.auto_sync_paused_due_to_error:
            print("Manueller Push erfolgreich. Auto-Sync wird wieder aktiviert.")
            self.auto_sync_paused_due_to_error = False
            self._update_sync_status_label()

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
            self.pull_race_runs_from_website(force_merge=(not all_success))

        self._reenable_push_buttons()

    # GEÄNDERT: Reaktiviert Auto-Sync bei Erfolg
    def _finalize_force_push(self, total_pushed, push_errors, delete_errors):
        msg = f"Zwangspush abgeschlossen.\n{total_pushed - push_errors} von {total_pushed} Einträgen erfolgreich zur Website hochgeladen."
        if push_errors > 0 or delete_errors > 0:
            msg += f"\n\nACHTUNG: Es gab Fehler!\n- {push_errors} Fehler beim Hochladen.\n- {delete_errors} Fehler beim Löschen."
            messagebox.showwarning("Zwangspush Ergebnis", msg, parent=self)
        else:
            messagebox.showinfo("Zwangspush Ergebnis", msg, parent=self)
            # NEU: Auto-Sync bei Erfolg reaktivieren
            if self.auto_sync_paused_due_to_error:
                print("Zwangspush erfolgreich. Auto-Sync wird wieder aktiviert.")
                self.auto_sync_paused_due_to_error = False
                self._update_sync_status_label()

        print("--- Zwangspush: Führe einen Merge-Pull aus, um die Daten neu zu synchronisieren. ---")
        self.pull_race_runs_from_website(force_merge=True)
        self.after(500, self._reenable_push_buttons)

    def initiate_force_push_to_website(self):
        self.push_to_website_button.configure(state="disabled")
        self.force_push_button.configure(state="disabled")

        threading.Thread(target=self._force_push_task, daemon=True).start()

    def _force_push_task(self):
        if self._check_for_double_data() == False:
            self.push_to_website_button.configure(state="enabled")
            self.force_push_button.configure(state="enabled")
            return
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
            items_to_delete = [key for key, value in self.data_items.items() if
                               value.get("status") == STATUS_DELETED]
            for item in items_to_push:
                item['_action'] = 'upsert'
            for item in items_to_delete:
                self.data_items.pop(item)

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

    def _reenable_push_buttons(self):
        is_connected = self.connect_to_website_button.cget("state") == "disabled"
        if is_connected:
            self.push_to_website_button.configure(state="normal", text="Push to Website")
            self.force_push_button.configure(state="normal", text="Zwangspush")

    # NEU: Alle Auto-Sync-Methoden
    def _update_sync_status_label(self):
        """Aktualisiert das Status-Label für den Auto-Sync."""
        if not self.auto_sync_enabled:
            self.sync_status_label.configure(text="Auto-Sync: Deaktiviert", text_color="gray")
        elif self.auto_sync_paused_due_to_error:
            self.sync_status_label.configure(text="Auto-Sync: FEHLER (Pausiert)", text_color="#E57373")
        elif self.auto_sync_in_progress:
            self.sync_status_label.configure(text="Synchronisiere...", text_color="#BBDEFB")
        else:
            self.sync_status_label.configure(text="Auto-Sync: Aktiv", text_color="#C8E6C9")

    def _trigger_auto_sync(self):
        """Startet oder setzt den Timer für die automatische Synchronisation zurück (Debouncing)."""
        if not self.auto_sync_enabled or self.auto_sync_paused_due_to_error:
            return

        if self.auto_sync_timer is not None:
            self.after_cancel(self.auto_sync_timer)

        self.auto_sync_timer = self.after(3000, self._start_auto_sync_thread)
        print("Auto-Sync in 3 Sekunden geplant...")

    def _start_auto_sync_thread(self):
        """Startet den eigentlichen Auto-Sync-Prozess in einem neuen Thread."""
        if self.auto_sync_in_progress: return

        self.auto_sync_in_progress = True
        self._update_sync_status_label()
        threading.Thread(target=self._execute_auto_sync, daemon=True).start()

    def _execute_auto_sync(self):
        """Sammelt alle ungesynchronisierten Daten und pusht sie zur Website."""
        print("--- Auto-Sync wird ausgeführt ---")
        data_to_send, _, _ = self._collect_data_for_website_push()

        if not data_to_send:
            print("Auto-Sync: Keine Änderungen zum Synchronisieren gefunden.")
            self.auto_sync_in_progress = False
            self.after(0, self._update_sync_status_label)
            return

        had_errors = False
        for data in data_to_send:
            success, item_id = self.push_data_website(data)
            if success:
                self.after(0, self._finalize_single_push_success, item_id, data.get("_action", ""))
            else:
                print(f"!!! Auto-Sync FEHLER beim Pushen von Item {item_id}. Synchronisierung wird pausiert. !!!")
                had_errors = True
                self.auto_sync_paused_due_to_error = True
                break

        if not had_errors:
            self.pull_race_runs_from_website()
        self.auto_sync_in_progress = False
        self.after(0, self._update_sync_status_label)
        print("--- Auto-Sync beendet ---")

    def push_single_item(self, item_id: Optional[str]):
        if not item_id: return
        with self.data_lock:
            item = self.data_items.get(item_id)
            if not item: return

            payload = item.to_data_dict()
            payload["app_item_id"] = item.app_item_id
            if item.status == STATUS_DELETED:
                payload["_action"] = "delete"
            elif not item._synced_to_website:
                payload["_action"] = "upsert"
            else:
                payload["_action"] = "changed"

        threading.Thread(target=lambda: self.after(0, self._finalize_single_push, *self.push_data_website(payload),
                                                   payload.get("_action")), daemon=True).start()

    # GEÄNDERT: Reaktiviert Auto-Sync bei Erfolg
    def _finalize_single_push(self, success: bool, item_id: Optional[str], action: str):
        """Finalisiert einen manuellen Einzel-Push und zeigt eine Nachricht."""
        if success:
            self._finalize_single_push_success(item_id, action)
            messagebox.showinfo("Erfolg", "Eintrag wurde erfolgreich gepusht.", parent=self)

            if self.auto_sync_paused_due_to_error:
                print("Manueller Einzel-Push erfolgreich. Auto-Sync wird wieder aktiviert.")
                self.auto_sync_paused_due_to_error = False
                self._update_sync_status_label()
                self._trigger_auto_sync()
        else:
            messagebox.showerror("Fehler", "Eintrag konnte nicht gepusht werden.", parent=self)

    def _finalize_single_push_success(self, item_id: Optional[str], action: str):
        """Aktualisiert den lokalen Zustand nach einem erfolgreichen Push (manuell oder auto)."""
        if not item_id: return
        with self.data_lock:
            if action == "delete":
                if item_id in self.data_items: del self.data_items[item_id]
            else:
                item = self.data_items.get(item_id)
                if item:
                    item.status = STATUS_SYNCED
                    item._synced_to_website = True

        self.refresh_treeview_display_fully()
        self.broadcast_data_update(item_id, is_delete=(action == "delete"))

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

    def pull_racers_from_website(self, show_success_message=True):
        api_endpoint = self.settings_data.get('API Endpoint Website', 'N/A')
        print(f"--- Pull von Racer-Daten von ({api_endpoint}) ---")

        def _do_racer_pull():
            racers_payload = self.get_data_website(api_endpoint + "racers/")
            if racers_payload is None:
                self.after(0, lambda: messagebox.showerror("Pull Fehler", "Konnte keine Racer-Daten abrufen.",
                                                           parent=self))
                return
            self.after(0, self._update_racer_data_store, racers_payload, show_success_message)

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
            # GEÄNDERT: Konvertiere RaceRun-Objekte in Dictionaries für MergeView
            local_data_for_merge = {item.app_item_id: asdict(item) for item in self.data_items.values()}

        remote_data_for_merge = {}
        for web_item in website_data_list:
            server_id = str(web_item.get("id"))
            if not server_id: continue

            renn_zeit_val = float(web_item.get("time_in_seconds")) if web_item.get(
                "time_in_seconds") is not None else None

            # Remote-Daten in das gleiche Dict-Format wie die lokalen bringen
            remote_data_format = {
                "app_item_id": server_id,
                "start_nummer": web_item.get("racer_start_number"),
                "round_number": web_item.get("run_type"),
                "renn_zeit": renn_zeit_val,
                "timestamp_messung": web_item.get("recorded_at"),
                "disqualified": web_item.get("disqualified", False),
                "notes": web_item.get("notes"),
                "updated_at": web_item.get("updated_at") or datetime.datetime.now().isoformat(),
                "status": STATUS_SYNCED,
                "_synced_to_website": True,
                # Felder, die nur lokal existieren, auf None setzen
                "scan_id": None,
                "zugeordneter_scan_id": None,
                "original_data_snapshot": None,
                "data_before_delete": None,
            }
            remote_data_for_merge[server_id] = remote_data_format

        # Konvertiere die dicts in das von MergeView erwartete Format {'data': {...}, 'status': '...'}
        def convert_for_merge_view(item_dict: Dict):
            return {
                'data': {k: v for k, v in item_dict.items() if
                         k not in ['status', '_synced_to_website', 'original_data_snapshot', 'data_before_delete',
                                   'app_item_id']},
                'status': item_dict.get('status'),
                '_synced_to_website': item_dict.get('_synced_to_website')
            }

        local_merge_input = {k: convert_for_merge_view(v) for k, v in local_data_for_merge.items()}
        remote_merge_input = {k: convert_for_merge_view(v) for k, v in remote_data_for_merge.items()}

        MergeView(self, local_data=local_merge_input, remote_data=remote_merge_input, source_name="Website",
                  callback_on_finish=self._finalize_merge)

    def open_merge_view_for_pull(self, website_data_list: List[Dict[str, Any]]):
        # Diese Methode ist jetzt quasi ein Alias für _initiate_merge_with_website_data
        self._initiate_merge_with_website_data(website_data_list)

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
                item_id_str = str(item_id_from_web)

                try:
                    renn_zeit_val = float(web_item_payload.get("time_in_seconds")) if web_item_payload.get(
                        "time_in_seconds") is not None else None
                except (ValueError, TypeError):
                    renn_zeit_val = None

                recorded_at_str = web_item_payload.get("recorded_at")
                timestamp = datetime.datetime.now().isoformat()
                if recorded_at_str:
                    try:
                        timestamp = datetime.datetime.fromisoformat(
                            str(recorded_at_str).replace("Z", "+00:00")).isoformat()
                    except (ValueError, TypeError):
                        pass

                new_run = RaceRun(
                    app_item_id=item_id_str,
                    start_nummer=str(web_item_payload.get("racer_start_number")),
                    round_number=web_item_payload.get("run_type"),
                    renn_zeit=renn_zeit_val,
                    timestamp_messung=timestamp,
                    disqualified=web_item_payload.get("disqualified", False),
                    notes=web_item_payload.get("notes"),
                    status=STATUS_SYNCED,
                    _synced_to_website=True
                )
                self.data_items[item_id_str] = new_run

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
        for i in self.tree.get_children(""): self.tree.delete(i)

        with self.data_lock:
            search_term = self.search_var.get().lower()

            # GEÄNDERT: Filter- und Sortierlogik arbeitet mit RaceRun-Objekten
            filtered_items: List[RaceRun]
            if search_term:
                filtered_items = []
                for item in self.data_items.values():
                    values_tuple = self._create_tree_item_values(item)
                    values_str = ' '.join(map(str, values_tuple)).lower()
                    if search_term in values_str:
                        filtered_items.append(item)
            else:
                filtered_items = list(self.data_items.values())

            # GEÄNDERT: Behebt den `TypeError` durch Normalisierung der Zeitstempel
            def get_sort_key(item: RaceRun):
                if self.sort_column == "timestamp_combined":
                    try:
                        dt = datetime.datetime.fromisoformat(item.timestamp_messung.replace("Z", "+00:00"))
                        return dt.replace(tzinfo=None)  # FIX: Macht den Zeitstempel "naive"
                    except (TypeError, ValueError):
                        return datetime.datetime.min
                elif self.sort_column == "start_number":
                    try:
                        return int(item.start_nummer)
                    except (ValueError, TypeError):
                        return 0
                elif self.sort_column == "racer_name":
                    racer = self.racers_by_start_number.get(item.start_nummer)
                    return racer.full_name if racer else "zzzz"
                elif self.sort_column == "soapbox_class":
                    racer = self.racers_by_start_number.get(item.start_nummer)
                    return racer.soapbox_class_display if racer else "zzzz"
                elif self.sort_column == "time_required":
                    return item.renn_zeit if item.renn_zeit is not None else 99999.0
                return datetime.datetime.min

            sorted_items = sorted(filtered_items, key=get_sort_key, reverse=self.sort_reverse)

            for item in sorted_items:
                values = self._create_tree_item_values(item)
                # NEU: Fügt das "pushable"-Tag hinzu, wenn das Symbol angezeigt wird
                tags = [item.status]
                if values[0] == "📤":  # Prüft, ob das Push-Symbol in der ersten Spalte ist
                    tags.append("pushable")
                self.tree.insert("", "end", iid=item.app_item_id, values=values, tags=tuple(tags))

        if selected_iids:
            valid_selection = [sid for sid in selected_iids if self.tree.exists(sid)]
            if valid_selection: self.tree.selection_set(valid_selection)

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
            # Konvertiere lokale RaceRun-Objekte in ein Dict-Format für MergeView
            local_data_dicts = {item.app_item_id: asdict(item) for item in self.data_items.values()}

        remote_data_dicts = {}
        for item_snapshot in version_to_load.get("data_snapshot", []):
            item_id = item_snapshot.get("_id_internal")
            if not item_id: continue

            # Erstelle ein Dict, das der Struktur eines asdict(RaceRun) entspricht
            remote_data_dicts[item_id] = {
                "app_item_id": item_id,
                **{k: v for k, v in item_snapshot.items() if not k.startswith('_')},
                "status": item_snapshot.get("_status_at_version", STATUS_SYNCED_LOCAL),
                "_synced_to_website": item_snapshot.get("_synced_to_website_at_version", False),
                "original_data_snapshot": None,
                "data_before_delete": None
            }

        # Hilfsfunktion, um die Dicts in das von MergeView erwartete Format zu bringen
        def convert_for_merge_view(item_dict: Dict):
            return {
                'data': {k: v for k, v in item_dict.items() if
                         k not in ['status', '_synced_to_website', 'original_data_snapshot', 'data_before_delete',
                                   'app_item_id']},
                'status': item_dict.get('status'),
                '_synced_to_website': item_dict.get('_synced_to_website')
            }

        local_merge_input = {k: convert_for_merge_view(v) for k, v in local_data_dicts.items()}
        remote_merge_input = {k: convert_for_merge_view(v) for k, v in remote_data_dicts.items()}

        version_num = version_index + 1
        MergeView(self, local_data=local_merge_input, remote_data=remote_merge_input,
                  source_name=f"Snapshot {version_num}",
                  callback_on_finish=self._finalize_merge)

    def _finalize_merge(self, resolved_data: Dict[str, Dict]):
        final_data_items: Dict[str, RaceRun] = {}

        for item_id, details in resolved_data.items():
            data_dict = details.get('data', {})
            run_obj = RaceRun(
                app_item_id=item_id,
                start_nummer=data_dict.get("start_nummer"),
                round_number=data_dict.get("round_number"),
                renn_zeit=data_dict.get("renn_zeit"),
                timestamp_messung=data_dict.get("timestamp_messung"),
                status=details.get('status', STATUS_MODIFIED),
                _synced_to_website=details.get('_synced_to_website', False),
                # ... andere Felder
            )
            final_data_items[item_id] = run_obj

        with self.data_lock:
            self.data_items = final_data_items

        self.refresh_treeview_display_fully()
        self.broadcast_data_update()
        messagebox.showinfo("Merge Abgeschlossen", "Die Daten wurden erfolgreich zusammengeführt.", parent=self)
        self._trigger_auto_sync()  # NEU

    def revert_to_version(self, version_index: int):
        if not (0 <= version_index < len(self.versions)): return

        version_to_load = self.versions[version_index]
        with self.data_lock:
            self.data_items.clear()
            for item_snapshot in version_to_load.get("data_snapshot", []):
                item_id = item_snapshot.get("_id_internal") or str(uuid.uuid4())
                data_content = {k: v for k, v in item_snapshot.items() if not k.startswith('_')}
                self.data_items[item_id] = RaceRun(
                    app_item_id=item_id,
                    status=item_snapshot.get("_status_at_version", STATUS_SYNCED_LOCAL),
                    _synced_to_website=item_snapshot.get("_synced_to_website_at_version", False),
                    **data_content
                )
        self.refresh_treeview_display_fully()
        self.broadcast_data_update()
        self._trigger_auto_sync()  # NEU


if __name__ == "__main__":
    if not os.path.exists("main_app/common"): os.makedirs("main_app/common")
    if not os.path.exists("main_app/common/__init__.py"): open("main_app/common/__init__.py", "w").close()
    if not os.path.exists("main_app/common/constants.py"):
        with open("main_app/common/constants.py", "w", encoding='utf-8') as f:
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
    if not os.path.exists("main_app/common/data_models.py"):
        with open("main_app/common/data_models.py", "w", encoding='utf-8') as f:
            f.write("""from dataclasses import dataclass, field
from typing import Optional, Any, Dict
import datetime

@dataclass
class Racer:
    start_number: str
    full_name: str
    soapbox_class_display: str = "N/A"

@dataclass
class RaceRun:
    app_item_id: str
    start_nummer: str
    round_number: str
    timestamp_messung: str
    renn_zeit: Optional[float] = None
    scan_id: Optional[str] = None
    zugeordneter_scan_id: Optional[str] = None
    disqualified: bool = False
    notes: Optional[str] = None
    status: str = 'new'
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    _synced_to_website: bool = False
    original_data_snapshot: Optional[Dict[str, Any]] = None
    data_before_delete: Optional[Dict[str, Any]] = None

    def to_data_dict(self) -> Dict[str, Any]:
        return {"start_nummer": self.start_nummer, "round_number": self.round_number, "renn_zeit": self.renn_zeit, "timestamp_messung": self.timestamp_messung, "scan_id": self.scan_id, "zugeordneter_scan_id": self.zugeordneter_scan_id, "disqualified": self.disqualified, "notes": self.notes, "updated_at": self.updated_at}
""")

    app = MainApp()
    app.mainloop()