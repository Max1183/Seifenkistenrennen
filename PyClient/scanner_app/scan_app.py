import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import uuid
import datetime
import threading
from typing import Dict, Any, Optional, List
import socket
import queue
import time

HOST = '127.0.0.1'  # Default host, could be made configurable 192.168.2.105
PORT = 65432
message_to_server_queue = queue.Queue()
received_message_queue = queue.Queue()  # For messages from server to this app's main thread


def send_message_to_server_func(values: List[Any]):
    """Queues a message to be sent to the server."""
    message_to_server_queue.put(values)


def receive_message_from_server_func(s: socket.socket):
    """Dedicated function to receive messages from the server socket."""
    buffer = ""
    s.settimeout(1.0)  # Set a timeout for recv
    while True:
        try:
            data_chunk = s.recv(8192)  # Slightly larger buffer
            if not data_chunk:
                print("Server hat die Verbindung geschlossen (recv).")
                received_message_queue.put(None)  # Signal connection loss
                return

            buffer += data_chunk.decode('utf-8')

            # Process messages based on a simple heuristic: known prefixes.
            # This is not perfectly robust for very large messages split across TCP packets
            # if the prefix itself is split. A more robust protocol (e.g., length prefixing)
            # would be better for production.

            # Continuously process buffer as long as known message prefixes are found
            processed_something = True
            while processed_something:
                processed_something = False
                # Check for known message types and try to extract them
                if buffer.startswith("ALL_DATA:"):
                    # Try to find the end of this message if multiple are concatenated
                    # This simplified logic might grab too much if messages are concatenated without clear separation
                    # beyond the prefix. A delimiter like \n\n or length prefixing is better.
                    # Let's assume for now server sends distinct prefixed messages or client handles splits.
                    end_of_all_data_marker = buffer.find("UPDATE_DATA:")  # Simplistic split logic
                    if end_of_all_data_marker == -1: end_of_all_data_marker = buffer.find("DELETE_DATA:")
                    if end_of_all_data_marker == -1: end_of_all_data_marker = buffer.find("RACER_DATA_UPDATE:")

                    if end_of_all_data_marker != -1:
                        msg = buffer[:end_of_all_data_marker]
                        buffer = buffer[end_of_all_data_marker:]
                    else:
                        msg = buffer
                        buffer = ""
                    received_message_queue.put(msg)
                    processed_something = True
                elif buffer.startswith("ALL_DATA_EMPTY"):
                    received_message_queue.put("ALL_DATA_EMPTY")
                    buffer = buffer[len("ALL_DATA_EMPTY"):]  # Consume
                    processed_something = True
                elif buffer.startswith("UPDATE_DATA:"):
                    # Similar logic as ALL_DATA for splitting if concatenated
                    # Find next potential message start to delimit current one.
                    next_msg_start = -1
                    for prefix in ["ALL_DATA:", "DELETE_DATA:", "RACER_DATA_UPDATE:"]:
                        pos = buffer.find(prefix, len("UPDATE_DATA:"))
                        if pos != -1 and (next_msg_start == -1 or pos < next_msg_start):
                            next_msg_start = pos

                    if next_msg_start != -1:
                        msg = buffer[:next_msg_start]
                        buffer = buffer[next_msg_start:]
                    else:
                        msg = buffer
                        buffer = ""
                    received_message_queue.put(msg)
                    processed_something = True
                elif buffer.startswith("DELETE_DATA:"):
                    # Find next potential message start
                    next_msg_start = -1
                    for prefix in ["ALL_DATA:", "UPDATE_DATA:", "RACER_DATA_UPDATE:"]:
                        pos = buffer.find(prefix, len("DELETE_DATA:"))
                        if pos != -1 and (next_msg_start == -1 or pos < next_msg_start):
                            next_msg_start = pos

                    if next_msg_start != -1:
                        msg = buffer[:next_msg_start]
                        buffer = buffer[next_msg_start:]
                    else:
                        msg = buffer
                        buffer = ""
                    received_message_queue.put(msg)
                    processed_something = True
                elif buffer.startswith("RACER_DATA_UPDATE:") or buffer.startswith("RACER_DATA_EMPTY"):
                    # Similar logic for racer data
                    prefix_to_check = "RACER_DATA_UPDATE:" if buffer.startswith(
                        "RACER_DATA_UPDATE:") else "RACER_DATA_EMPTY"
                    next_msg_start = -1
                    for prefix in ["ALL_DATA:", "UPDATE_DATA:", "DELETE_DATA:"]:
                        pos = buffer.find(prefix, len(prefix_to_check))
                        if pos != -1 and (next_msg_start == -1 or pos < next_msg_start):
                            next_msg_start = pos

                    if next_msg_start != -1:
                        msg = buffer[:next_msg_start]
                        buffer = buffer[next_msg_start:]
                    else:
                        msg = buffer
                        buffer = ""
                    received_message_queue.put(msg)
                    processed_something = True

                if not processed_something and len(buffer) > 16384:  # Safety for very large unparsed buffer
                    print(f"Warning: Receive buffer growing large ({len(buffer)}) without recognized prefix. Clearing.")
                    buffer = ""  # Clear to prevent infinite loop if data is malformed

        except socket.timeout:
            # Timeout is normal if no data. If buffer has partial data, it remains for next recv.
            continue
        except ConnectionResetError:
            print("Server Verbindung zurückgesetzt (recv).")
            received_message_queue.put(None);
            return
        except Exception as e:
            print(f"Fehler im receive_message_from_server_func: {e}")
            received_message_queue.put(None);
            return


def client_communication_thread_func():
    """Manages connection and bi-directional communication with the server."""
    while True:  # Outer loop for retrying connection
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                print(f"Versuche Verbindung zu Server {HOST}:{PORT}...")
                s.connect((HOST, PORT))
                print(f"Verbunden mit Server {HOST}:{PORT}")

                receiver_thread = threading.Thread(target=receive_message_from_server_func, args=(s,), daemon=True)
                receiver_thread.start()

                # Send loop
                while True:
                    if not receiver_thread.is_alive() and received_message_queue.empty():
                        print("Receiver thread gestorben. Client-Loop wird beendet.")
                        break

                    try:
                        msg_to_send_list = message_to_server_queue.get(timeout=0.1)  # Non-blocking with timeout
                        if msg_to_send_list:
                            text_to_server = "$#".join(map(str, msg_to_send_list)) + "$#"
                            s.sendall(text_to_server.encode('utf-8'))
                            message_to_server_queue.task_done()
                    except queue.Empty:
                        if s.fileno() == -1:  # Socket closed
                            print("Socket im Send-Loop geschlossen. Breche inneren Loop.")
                            break
                        time.sleep(0.01)  # Brief pause if queue is empty
                    except socket.error as se:
                        print(f"Socket-Fehler im Send-Loop: {se}. Breche inneren Loop.")
                        break  # Break from send loop, will lead to connection retry
                    except Exception as e:
                        print(f"Unerwarteter Fehler im Client Send-Loop: {e}")
                        time.sleep(0.1)

                if receiver_thread.is_alive():
                    try:
                        s.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    receiver_thread.join(timeout=1.0)

        except ConnectionRefusedError:
            print(f"Verbindung zu {HOST}:{PORT} fehlgeschlagen. Server nicht erreichbar? Warte 5s...")
        except socket.timeout:
            print(f"Timeout bei Verbindungsaufbau zu {HOST}:{PORT}. Warte 5s...")
        except Exception as e:
            print(f"Allgemeiner Client-Fehler im äußeren Loop: {e}. Warte 5s...")

        time.sleep(5)


client_comm_thread = threading.Thread(target=client_communication_thread_func, daemon=True)
client_comm_thread.start()


def process_server_messages_func(app_instance: 'ScannerApp'):
    """Processes messages received from the server via received_message_queue."""
    while True:
        try:
            server_msg_block = received_message_queue.get(timeout=1.0)
            if server_msg_block is None:
                print("Server-Nachrichten-Prozessor: Sentinel (Verbindungsproblem) empfangen.")
                time.sleep(1)
                continue

            if server_msg_block:
                if server_msg_block.startswith("ALL_DATA:"):
                    data_part = server_msg_block[len("ALL_DATA:"):]
                    app_instance.after(0, app_instance.process_all_data_from_server, data_part)
                elif server_msg_block == "ALL_DATA_EMPTY":
                    app_instance.after(0, app_instance.process_all_data_from_server, "")
                elif server_msg_block.startswith("UPDATE_DATA:"):
                    data_part = server_msg_block[len("UPDATE_DATA:"):]
                    app_instance.after(0, app_instance.process_update_data_from_server, data_part)
                elif server_msg_block.startswith("DELETE_DATA:"):
                    item_id_to_delete = server_msg_block[len("DELETE_DATA:"):]
                    app_instance.after(0, app_instance.process_delete_data_from_server, item_id_to_delete)
                elif server_msg_block.startswith("RACER_DATA_UPDATE:"):
                    data_part = server_msg_block[len("RACER_DATA_UPDATE:"):]
                    app_instance.after(0, app_instance.process_racer_data_from_server, data_part)
                elif server_msg_block == "RACER_DATA_EMPTY":
                    app_instance.after(0, app_instance.process_racer_data_from_server, "")
                else:
                    print(f"Unbekannte oder unvollständige Nachricht vom Server: {server_msg_block[:100]}")

            if hasattr(received_message_queue, 'task_done'):
                received_message_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Fehler in process_server_messages_func: {e}")
            time.sleep(0.1)


# ... (restlicher Code bis _sort_and_refresh_all_data_treeview bleibt gleich) ...
# Import common constants or define fallbacks
try:
    from common.constants import STATUS_SYNCED, STATUS_COMPLETE
    # These are from MainApp, ScannerApp might not use them directly for its own display logic
    # but good to have if ever needed for direct interpretation of MainApp status.
except ImportError:
    print("FEHLER: common.constants nicht gefunden (ScannerApp). Verwende Fallbacks.")
    STATUS_SYNCED, STATUS_COMPLETE = "Synced", "Complete"

# ScannerApp's own local status constants
SCAN_LOG_STATUS_PENDING = "Lokal Erfasst"
# SCAN_LOG_STATUS_SYNCED_TO_MAIN = "Synced" # Replaced by server ack, not used yet
SCAN_LOG_STATUS_ERROR = "Fehler (Lokal)"

# Data models (ScanLogEntry might be defined in common.data_models)
try:
    from common.data_models import ScanLogEntry
except ImportError:
    class ScanLogEntry:  # Fallback definition
        def __init__(self, start_nummer: str, status: str, scan_id: Optional[str] = None,
                     timestamp_scan_lokal: Optional[datetime.datetime] = None, error_message: Optional[str] = None):
            self.scan_id = scan_id or str(uuid.uuid4())
            self.timestamp_scan_lokal = timestamp_scan_lokal or datetime.datetime.now()
            self.start_nummer = start_nummer
            self.status = status
            self.error_message = error_message

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scanner-App (Standalone)")
        self.geometry("950x700")  # Increased width slightly for new "Name" column

        self.scan_log_entries: List[ScanLogEntry] = []
        self._scan_log_lock = threading.Lock()

        self.all_race_data_dict: Dict[str, Dict[str, Any]] = {}  # Stores data from MainApp's ALL_DATA/UPDATE_DATA
        self._all_race_data_lock = threading.Lock()

        # ***** NEU: Store for racer names from MainApp *****
        self.racer_names_by_start_number: Dict[str, str] = {}
        self._racer_names_lock = threading.Lock()  # If accessed by multiple threads, though UI updates are main thread

        self.settings_data = {
            "Scanner Name": f"Scanner_{uuid.uuid4().hex[:4]}",
            # "MainApp Host": HOST, # Could make HOST/PORT configurable here too
            # "MainApp Port": PORT,
        }
        self.setting_widgets: Dict[str, ctk.CTkBaseClass] = {}
        self._settings_ui_built = False

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_view = ctk.CTkTabview(self.main_container)
        self.tab_view.pack(fill="both", expand=True)
        self.scan_log_tab = self.tab_view.add("Scan-Protokoll")
        self.all_data_tab = self.tab_view.add("Alle Renndaten")
        self.settings_tab = self.tab_view.add("Einstellungen")

        self.scan_log_tree: Optional[ttk.Treeview] = None
        self.all_data_tree: Optional[ttk.Treeview] = None
        self._setup_scan_log_tab()
        self._setup_all_data_tab()
        self._setup_settings_tab()
        self.tab_view.set("Scan-Protokoll")  # Default tab

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start the thread that processes messages from the server queue
        self.server_message_processor_thread = threading.Thread(
            target=process_server_messages_func, args=(self,), daemon=True
        )
        self.server_message_processor_thread.start()

    def on_closing(self):
        print("ScannerApp schließt...")
        # Potentially send a "disconnecting" message to server if protocol supports it
        # Client_comm_thread is daemon, will exit with main. Message queues might need cleanup.
        self.destroy()

    def _get_theme_color(self, widget_name: str, color_type: str,
                         default_light: str = "#FFFFFF", default_dark: str = "#000000") -> str:
        try:
            color_value = ctk.ThemeManager.theme[widget_name][color_type]
            is_dark_mode = ctk.get_appearance_mode().lower() == "dark"
            return str(color_value[1] if is_dark_mode else color_value[0]) if isinstance(color_value,
                                                                                         (list, tuple)) else str(
                color_value)
        except Exception:  # Fallback if color not found or error
            is_dark_mode_fallback = ctk.get_appearance_mode().lower() == "dark"
            return default_dark if is_dark_mode_fallback else default_light

    def _setup_scan_log_tab(self):
        input_frame = ctk.CTkFrame(self.scan_log_tab, height=80)
        input_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(input_frame, text="Startnummer:", font=ctk.CTkFont(size=14)).pack(side="left", padx=5, pady=10)
        self.scan_input_entry = ctk.CTkEntry(input_frame, placeholder_text="Startnummer scannen/eingeben",
                                             font=ctk.CTkFont(size=14), width=200)
        self.scan_input_entry.pack(side="left", padx=5, pady=10, fill="x", expand=True)
        self.scan_input_entry.bind("<Return>", self._on_scan_input_enter)
        self.manual_scan_button = ctk.CTkButton(input_frame, text="Erfassen", command=self._simulate_scan_from_input)
        self.manual_scan_button.pack(side="left", padx=10, pady=10)

        tree_container = ctk.CTkFrame(self.scan_log_tab);
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        # ***** MODIFIZIERT: "racer_name_scan_log" Spalte hinzugefügt *****
        self.scan_log_tree_columns = ("timestamp", "start_nummer", "racer_name_scan_log", "scan_id_short",
                                      "status_scan")
        self.scan_log_tree = ttk.Treeview(tree_container, columns=self.scan_log_tree_columns, show="headings")

        vsb = ctk.CTkScrollbar(tree_container, command=self.scan_log_tree.yview);
        vsb.pack(side="right", fill="y")
        hsb = ctk.CTkScrollbar(tree_container, command=self.scan_log_tree.xview, orientation="horizontal");
        hsb.pack(side="bottom", fill="x")
        self.scan_log_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.scan_log_tree.pack(side="left", fill="both", expand=True)

        self.scan_log_tree.heading("timestamp", text="Scan-Zeit", anchor=tk.W)
        self.scan_log_tree.heading("start_nummer", text="Startnr.", anchor=tk.W)
        # ***** NEU: Überschrift für Name im Scan-Log *****
        self.scan_log_tree.heading("racer_name_scan_log", text="Name", anchor=tk.W)
        self.scan_log_tree.heading("scan_id_short", text="Scan ID", anchor=tk.W)
        self.scan_log_tree.heading("status_scan", text="Status Scan", anchor=tk.W)

        self.scan_log_tree.column("timestamp", width=180, minwidth=150, stretch=tk.NO)
        self.scan_log_tree.column("start_nummer", width=100, minwidth=80)
        # ***** NEU: Spaltenkonfiguration für Name im Scan-Log *****
        self.scan_log_tree.column("racer_name_scan_log", width=180, minwidth=120, stretch=tk.YES)
        self.scan_log_tree.column("scan_id_short", width=100, minwidth=80, stretch=tk.NO)
        self.scan_log_tree.column("status_scan", width=120, minwidth=100, stretch=tk.NO)  # Wider for "Lokal Erfasst"

        self._apply_scan_log_tree_styling()

    def _apply_scan_log_tree_styling(self):
        style = ttk.Style(self)
        theme_fg = self._get_theme_color("CTkFrame", "fg_color", default_light="#ECECEC", default_dark="#2B2B2B")
        theme_text = self._get_theme_color("CTkLabel", "text_color", default_light="#000000", default_dark="#DCE4EE")
        theme_sel_bg = self._get_theme_color("CTkButton", "fg_color", default_light="#3A7EBF", default_dark="#1F538D")
        theme_head_bg = self._get_theme_color("CTkButton", "hover_color", default_light="#325882",
                                              default_dark="#14375E")

        style.theme_use("default")
        style.configure("Treeview", background=theme_fg, foreground=theme_text, fieldbackground=theme_fg, rowheight=28,
                        font=ctk.CTkFont(size=12))
        style.map("Treeview", background=[('selected', theme_sel_bg)])
        style.configure("Treeview.Heading", background=theme_head_bg, foreground=theme_text,
                        font=ctk.CTkFont(size=13, weight="bold"))

        # Style specific tags for scan log status
        style.configure(f"{SCAN_LOG_STATUS_PENDING}.Treeview", foreground="blue")  # Example: blue for pending
        style.configure(f"{SCAN_LOG_STATUS_ERROR}.Treeview", foreground="red")  # Example: red for error
        # Add more styles if SCAN_LOG_STATUS_SYNCED_TO_MAIN is used for display

    def _setup_all_data_tab(self):
        ctk.CTkLabel(self.all_data_tab, text="Alle Renndaten (von MainApp)", anchor="w").pack(fill="x", padx=10,
                                                                                              pady=(10, 5))
        tree_container = ctk.CTkFrame(self.all_data_tab);
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ***** MODIFIZIERT: "racer_name_all_data" Spalte hinzugefügt *****
        self.all_data_tree_columns = ("start_nummer", "racer_name_all_data", "round_number_main", "renn_zeit",
                                      "mess_zeit_combined")
        self.all_data_tree = ttk.Treeview(tree_container, columns=self.all_data_tree_columns, show="headings")

        vsb = ctk.CTkScrollbar(tree_container, command=self.all_data_tree.yview);
        vsb.pack(side="right", fill="y")
        hsb = ctk.CTkScrollbar(tree_container, command=self.all_data_tree.xview, orientation="horizontal");
        hsb.pack(side="bottom", fill="x")
        self.all_data_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.all_data_tree.pack(side="left", fill="both", expand=True)

        self.all_data_tree.heading("start_nummer", text="Startnr.", anchor=tk.W)
        # ***** NEU: Überschrift für Name in Alle Renndaten *****
        self.all_data_tree.heading("racer_name_all_data", text="Name", anchor=tk.W)
        self.all_data_tree.heading("round_number_main", text="Runde", anchor=tk.CENTER)
        self.all_data_tree.heading("renn_zeit", text="Rennzeit(s)", anchor=tk.E)
        self.all_data_tree.heading("mess_zeit_combined", text="Messzeit (MainApp)", anchor=tk.W)

        self.all_data_tree.column("start_nummer", width=100, minwidth=80)
        # ***** NEU: Spaltenkonfiguration für Name in Alle Renndaten *****
        self.all_data_tree.column("racer_name_all_data", width=180, minwidth=120, stretch=tk.YES)
        self.all_data_tree.column("round_number_main", width=80, minwidth=60, anchor=tk.CENTER)
        self.all_data_tree.column("renn_zeit", width=100, minwidth=80, anchor=tk.E)
        self.all_data_tree.column("mess_zeit_combined", width=200, minwidth=180, stretch=tk.YES)

        self._apply_all_data_tree_styling()  # Uses same base styling as scan_log_tree

    def _apply_all_data_tree_styling(self):
        # For now, "Alle Renndaten" uses the same base Treeview styling as Scan-Log.
        # If specific status styling (like MainApp's status colors) were to be applied here,
        # MainApp would need to send that status, and tags would be added here.
        # The current payload does not include MainApp's internal item status.
        pass  # No additional specific styling for this tree for now.

    def _setup_settings_tab(self):
        if self._settings_ui_built:  # Just update values if UI already exists
            for key, value in self.settings_data.items():
                # Skip settings that might not be simple entries or are managed differently
                if key in ["MainApp Host", "MainApp Port", "Auto-Connect"]: continue
                widget = self.setting_widgets.get(key)
                if widget:
                    if isinstance(widget, ctk.CTkEntry): widget.delete(0, tk.END); widget.insert(0, str(value))
            return

        sf = ctk.CTkScrollableFrame(self.settings_tab, label_text="Scanner Einstellungen");
        sf.pack(fill="both", expand=True, padx=10, pady=10)
        self.setting_widgets.clear()  # Clear old widget references

        for key, value in self.settings_data.items():
            if key in ["MainApp Host", "MainApp Port", "Auto-Connect"]: continue  # Skip these

            entry_frame = ctk.CTkFrame(sf);
            entry_frame.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(entry_frame, text=f"{key}:", width=150, anchor="w").pack(side="left", padx=(0, 10))

            widget_to_add: Optional[ctk.CTkBaseClass] = None
            if isinstance(value, (int, float, str)):  # Assuming all current settings are string-like
                entry_widget = ctk.CTkEntry(entry_frame);
                entry_widget.insert(0, str(value))
                entry_widget.bind("<Return>", lambda e, k=key, wid=entry_widget: self._on_setting_changed(k, wid))
                entry_widget.bind("<FocusOut>", lambda e, k=key, wid=entry_widget: self._on_setting_changed(k, wid))
                widget_to_add = entry_widget

            if widget_to_add:
                widget_to_add.pack(side="left", fill="x", expand=True, padx=5)
                self.setting_widgets[key] = widget_to_add

        self._settings_ui_built = True

    def _on_setting_changed(self, key: str, widget_or_var_val: Any):
        if key in ["MainApp Host", "MainApp Port", "Auto-Connect"]: return

        current_value = self.settings_data[key]
        new_value_str = ""
        new_typed_value: Any = None  # To hold value cast to original type

        if isinstance(widget_or_var_val, ctk.CTkEntry):  # If called from Entry widget event
            new_value_str = widget_or_var_val.get()
        else:  # If called with direct value (e.g. from CheckBox or ComboBox command)
            new_value_str = str(widget_or_var_val)
            # For CheckBox, widget_or_var_val would be the BooleanVar, so .get() needed
            # This simple example assumes Entry or direct string value.
            # For boolean settings, handle BooleanVar.get()

        try:
            # Attempt to cast to original type if it's not string
            if isinstance(current_value, int):
                new_typed_value = int(new_value_str)
            elif isinstance(current_value, float):
                new_typed_value = float(new_value_str)
            # Add elif for bool if you have boolean settings
            else:
                new_typed_value = new_value_str  # Default to string

            if self.settings_data[key] != new_typed_value:
                self.settings_data[key] = new_typed_value
                print(f"Scanner Setting '{key}' changed to: {new_typed_value}")

        except ValueError:
            messagebox.showerror("Error",
                                 f"Ungültiger Wert für {key}: '{new_value_str}'. Erwartet: {type(current_value).__name__}.",
                                 parent=self)
            # Reset entry to old value if it's an Entry widget
            if isinstance(widget_or_var_val, ctk.CTkEntry):
                widget_or_var_val.delete(0, tk.END)
                widget_or_var_val.insert(0, str(current_value))

    def _on_scan_input_enter(self, event: Optional[tk.Event] = None):  # event can be None if called directly
        self._simulate_scan_from_input()

    def _real_scan_thread_target(self):  # Placeholder for actual scanner hardware integration
        # This would run in a loop, trying to read from a scanner device
        # For now, it does nothing.
        while True:
            # scanned_data = read_from_actual_scanner_device() # Hypothetical function
            # if scanned_data:
            #    self._add_scan_to_log_locally(scanned_data) # Process in main thread via self.after
            time.sleep(0.1)  # Check periodically

    def _simulate_scan_from_input(self):
        start_nummer = self.scan_input_entry.get().strip()
        if not start_nummer:
            messagebox.showwarning("Eingabe fehlt", "Bitte Startnummer eingeben oder scannen.", parent=self)
            return

        self._add_scan_to_log_locally(start_nummer)
        self.scan_input_entry.delete(0, tk.END)
        self.scan_input_entry.focus()  # Keep focus on input for next scan

    def _add_scan_to_log_locally(self, start_nummer: str):
        """Adds scan to local log and queues it for sending to MainApp."""
        # Disable button briefly to prevent rapid multi-clicks if processing takes time
        self.manual_scan_button.configure(state="disabled")

        # Worker to do the actual logic, then re-enable button in main thread
        # This is slight overkill for current synchronous logic but good practice if sending was slow
        threading.Thread(target=self._add_scan_to_log_worker, args=(start_nummer,), daemon=True).start()

    def _add_scan_to_log_worker(self, start_nummer: str):
        """Worker part of adding scan log. Runs in a separate thread."""
        new_entry = ScanLogEntry(start_nummer=start_nummer, status=SCAN_LOG_STATUS_PENDING)

        with self._scan_log_lock:
            self.scan_log_entries.insert(0, new_entry)  # Add to top of internal list

        # Prepare values to send to MainApp: timestamp, start_nr, scan_id
        # MainApp expects specific format for timestamp from scanner
        values_to_send = [
            new_entry.timestamp_scan_lokal.strftime("%H:%M:%S (%d.%m)"),  # Format: HH:MM:SS (DD.MM)
            new_entry.start_nummer,
            new_entry.scan_id  # MainApp will associate this scan_id with the created/updated entry
        ]
        send_message_to_server_func(values_to_send)  # Queue for sending

        # Schedule UI updates on the main thread
        self.after(0, self._refresh_scan_log_treeview)
        self.after(100,
                   lambda: self.manual_scan_button.configure(state="normal"))  # Re-enable button after a short delay

    ##### MODIFIZIERT: Sortierfunktion, die das Zeitformat von MainApp korrekt parst #####
    def _sort_and_refresh_all_data_treeview(self, highlight_item_id: Optional[str] = None):
        if not self.all_data_tree or not self.all_data_tree.winfo_exists(): return

        current_selection = self.all_data_tree.selection()
        for i in self.all_data_tree.get_children(): self.all_data_tree.delete(i)

        with self._all_race_data_lock:
            # Sortierfunktion, die das von der MainApp gesendete Format "HH:MM:SS (DD.MM.YYYY)" parst
            def get_sort_key_all_data(item_id_key: str) -> datetime.datetime:
                item_data = self.all_race_data_dict.get(item_id_key, {})
                time_str = item_data.get("mess_zeit_combined", "")
                if time_str and time_str != "-":
                    try:
                        # Format: "HH:MM:SS (DD.MM.YYYY)"
                        return datetime.datetime.strptime(time_str, "%H:%M:%S (%d.%m.%Y)")
                    except (ValueError, TypeError) as e:
                        # Fallback for other potential formats or errors
                        print(f"Warning: Could not parse timestamp '{time_str}' in all_data_tree. Error: {e}")
                        return datetime.datetime.min
                return datetime.datetime.min

            sorted_ids = sorted(list(self.all_race_data_dict.keys()), key=get_sort_key_all_data, reverse=True)

            for item_id in sorted_ids:
                item_data = self.all_race_data_dict[item_id]
                values = (
                    item_data.get("start_nummer", "-"),
                    item_data.get("racer_name", "-"),
                    item_data.get("round_number_main", "-"),
                    item_data.get("renn_zeit", "-"),
                    item_data.get("mess_zeit_combined", "-")
                )
                try:
                    # Insert at '0' to ensure newest appears at the top
                    self.all_data_tree.insert("", 0, iid=item_id, values=values, tags=())
                except tk.TclError as e:
                    print(f"Error inserting item into all_data_tree: {item_id}, Error: {e}")

        if highlight_item_id and self.all_data_tree.exists(highlight_item_id):
            self.all_data_tree.selection_set(highlight_item_id)
            self.all_data_tree.focus(highlight_item_id)
            self.all_data_tree.see(highlight_item_id)
        elif current_selection and self.all_data_tree.exists(current_selection[0]):
            try:
                self.all_data_tree.selection_set(current_selection)
            except tk.TclError:
                pass

    # ... (restlicher Code bleibt unverändert) ...
    def _refresh_scan_log_treeview(self):
        if not self.scan_log_tree or not self.scan_log_tree.winfo_exists(): return

        selected_item_tuple = self.scan_log_tree.selection()
        selected_id = selected_item_tuple[0] if selected_item_tuple else None

        self.scan_log_tree.delete(*self.scan_log_tree.get_children())  # Clear tree

        with self._scan_log_lock, self._racer_names_lock:  # Lock both for consistent data
            # self.scan_log_entries is newest first. To display newest on top with insert("",0,...), iterate reversed.
            for entry in reversed(self.scan_log_entries):  # Iterate oldest to newest
                # ***** NEU: Racer-Name für Scan-Log holen *****
                racer_name = self.racer_names_by_start_number.get(entry.start_nummer, "-")

                values = (
                    entry.timestamp_scan_lokal.strftime("%H:%M:%S (%d.%m)"),  # Local scan time
                    entry.start_nummer,
                    racer_name,  # Display name
                    entry.scan_id[:8] + "...",  # Shortened Scan ID
                    entry.status  # Local status of the scan
                )
                # Insert at index 0, so the last item processed (newest from original list) is at top
                self.scan_log_tree.insert("", 0, iid=entry.scan_id, values=values, tags=(entry.status,))

        if selected_id and self.scan_log_tree.exists(selected_id):
            try:
                self.scan_log_tree.selection_set(selected_id)
            except tk.TclError:
                pass  # Item might no longer exist if list changed drastically

    def process_all_data_from_server(self, data_payload: str):
        """Processes the full list of race data items from the MainApp."""
        new_data_dict = {}
        if not data_payload:  # ALL_DATA_EMPTY case
            print("ScannerApp: Server sendet leere Datensammlung für Alle Renndaten.")
        else:
            items_str = data_payload.split('|')
            for item_str in items_str:
                if not item_str.strip(): continue
                parts = item_str.split('$#')
                # Expected: item_id$#start_nr$#racer_name$#round_nr$#renn_zeit$#mess_zeit_combined (6 fields)
                if len(parts) == 6:
                    item_id = parts[0]
                    new_data_dict[item_id] = {
                        "start_nummer": parts[1],
                        "racer_name": parts[2],  # ***** NEU: Name vom Server *****
                        "round_number_main": parts[3],
                        "renn_zeit": parts[4],
                        "mess_zeit_combined": parts[5]
                    }
                else:
                    print(
                        f"ScannerApp: Fehlerhaftes Datenformat für Item in ALL_DATA: '{item_str}' (Teile: {len(parts)})")

        with self._all_race_data_lock:
            self.all_race_data_dict = new_data_dict
        self._sort_and_refresh_all_data_treeview()

    def process_update_data_from_server(self, item_payload: str):
        """Processes a single updated race data item from the MainApp."""
        if not item_payload.strip(): return
        parts = item_payload.split('$#')
        # Expected: item_id$#start_nr$#racer_name$#round_nr$#renn_zeit$#mess_zeit_combined (6 fields)
        if len(parts) == 6:
            item_id = parts[0]
            updated_item_data = {
                "start_nummer": parts[1],
                "racer_name": parts[2],  # ***** NEU: Name vom Server *****
                "round_number_main": parts[3],
                "renn_zeit": parts[4],
                "mess_zeit_combined": parts[5]
            }
            with self._all_race_data_lock:
                self.all_race_data_dict[item_id] = updated_item_data  # Add or update
            self._sort_and_refresh_all_data_treeview(highlight_item_id=item_id)
        else:
            print(
                f"ScannerApp: Fehlerhaftes Datenformat für Item in UPDATE_DATA: '{item_payload}' (Teile: {len(parts)})")

    def process_delete_data_from_server(self, item_id_to_delete: str):
        """Processes a delete command for a race data item from the MainApp."""
        if not item_id_to_delete.strip(): return
        with self._all_race_data_lock:
            if item_id_to_delete in self.all_race_data_dict:
                del self.all_race_data_dict[item_id_to_delete]
        self._sort_and_refresh_all_data_treeview()

    def process_racer_data_from_server(self, racer_data_payload: str):
        """Processes racer name data from MainApp."""
        new_racer_names = {}
        if not racer_data_payload:  # RACER_DATA_EMPTY case
            print("ScannerApp: Server sendet leere Racer-Daten.")
        else:
            pairs = racer_data_payload.split('|')
            for pair_str in pairs:
                if not pair_str.strip(): continue
                try:
                    start_nr, name = pair_str.split(':', 1)
                    new_racer_names[start_nr] = name
                except ValueError:
                    print(f"ScannerApp: Fehlerhaftes Format für Racer-Daten-Paar: '{pair_str}'")

        with self._racer_names_lock:
            self.racer_names_by_start_number = new_racer_names

        print(f"ScannerApp: Racer-Namen aktualisiert ({len(new_racer_names)} Einträge).")
        # Refresh both trees as they might display names
        self._refresh_scan_log_treeview()
        self._sort_and_refresh_all_data_treeview()


if __name__ == "__main__":
    import os

    # Ensure common directory and files exist for standalone execution (basic setup)
    if not os.path.exists("common"): os.makedirs("common")
    if not os.path.exists("common/__init__.py"): open("common/__init__.py", "w").close()
    if not os.path.exists("common/constants.py"):
        with open("common/constants.py", "w") as f:
            f.write("STATUS_NEW = 'new'\nSTATUS_MODIFIED = 'modified'\nSTATUS_DELETED = 'deleted'\n"
                    "STATUS_SYNCED = 'synced'\nSTATUS_COMPLETE = 'complete'\n"
                    "COLOR_STATUS_NEW_BG = '#c8e6c9'\nCOLOR_STATUS_MODIFIED_BG = '#fff9c4'\n"
                    "COLOR_STATUS_DELETED_FG = '#e57373'\nCOLOR_STATUS_COMPLETE_BG = '#bbdefb'\n")
    if not os.path.exists("common/data_models.py"):
        with open("common/data_models.py", "w") as f:
            f.write("import datetime\nimport uuid\nfrom typing import Optional\n\n"
                    "class ScanLogEntry:\n"
                    "    def __init__(self, start_nummer: str, status: str, scan_id: Optional[str] = None, timestamp_scan_lokal: Optional[datetime.datetime] = None, error_message: Optional[str] = None):\n"
                    "        self.scan_id = scan_id or str(uuid.uuid4())\n"
                    "        self.timestamp_scan_lokal = timestamp_scan_lokal or datetime.datetime.now()\n"
                    "        self.start_nummer = start_nummer\n"
                    "        self.status = status\n"
                    "        self.error_message = error_message\n\n"
                    "class MainDataEntry(dict): pass\nclass DisplayableMainData(dict): pass\n")

    app = ScannerApp()
    app.mainloop()
