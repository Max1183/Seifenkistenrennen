# --- START OF FILE moderator_app.py ---

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import datetime
import threading
from typing import Dict, Any, Optional
import socket
import queue
import time

HOST = '127.0.0.1'
PORT = 65432
received_message_queue = queue.Queue()


# --- NEUER, STABILER NETZWERK-CODE ---
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

            # Moderator-App sendet nichts, wartet nur auf das Ende des Receivers
            receiver_thread.join()

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
        except Exception as e:
            print(f"Fehler in process_server_messages_func: {e}")


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ModeratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Moderator-Ansicht")
        self.geometry("1100x700")

        self.all_race_data_dict: Dict[str, Dict[str, Any]] = {}
        self._all_race_data_lock = threading.Lock()

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.top_bar = ctk.CTkFrame(self.main_container, height=40)
        self.top_bar.pack(fill="x", pady=(0, 5))
        self.status_label = ctk.CTkLabel(self.top_bar, text="Verbinde...", text_color="orange")
        self.status_label.pack(side="left", padx=10)

        self.tree: Optional[ttk.Treeview] = None
        self._setup_data_view()

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        threading.Thread(target=client_communication_thread_func, args=(self,), daemon=True).start()
        threading.Thread(target=process_server_messages_func, args=(self,), daemon=True).start()

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

    def _setup_data_view(self):
        tree_container = ctk.CTkFrame(self.main_container)
        tree_container.pack(fill="both", expand=True)

        self.tree_columns = ("start_nummer", "racer_name", "soapbox_class", "round_number", "renn_zeit", "mess_zeit")
        self.tree = ttk.Treeview(tree_container, columns=self.tree_columns, show="headings")
        vsb = ctk.CTkScrollbar(tree_container, command=self.tree.yview);
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)

        for col, name in [("start_nummer", "Startnr."), ("racer_name", "Name"), ("soapbox_class", "Kistenklasse"),
                          ("round_number", "Runde"), ("renn_zeit", "Rennzeit"), ("mess_zeit", "Messzeit")]:
            self.tree.heading(col, text=name)

        for col, w, stretch, anchor in [("start_nummer", 80, False, tk.W), ("racer_name", 180, True, tk.W),
                                        ("soapbox_class", 150, True, tk.W), ("round_number", 80, False, tk.CENTER),
                                        ("renn_zeit", 100, False, tk.E), ("mess_zeit", 180, False, tk.W)]:
            self.tree.column(col, width=w, stretch=stretch, anchor=anchor)

        self._apply_treeview_styling()

    def _apply_treeview_styling(self):
        style = ttk.Style(self)
        style.theme_use("default")
        bg_color = self._get_theme_color("CTkFrame", "fg_color")
        text_color = self._get_theme_color("CTkLabel", "text_color")
        selected_color = self._get_theme_color("CTkButton", "fg_color")
        style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, rowheight=28,
                        font=ctk.CTkFont(size=12))
        style.map("Treeview", background=[('selected', selected_color)])
        style.configure("Treeview.Heading", font=ctk.CTkFont(size=13, weight="bold"))

    def _sort_and_refresh_data_treeview(self, highlight_item_id: Optional[str] = None):
        if not self.tree or not self.tree.winfo_exists(): return
        self.tree.delete(*self.tree.get_children())
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
                self.tree.insert("", "end", iid=item_id, values=values)
        if highlight_item_id and self.tree.exists(highlight_item_id):
            self.tree.selection_set(highlight_item_id)
            self.tree.see(highlight_item_id)

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
        self._sort_and_refresh_data_treeview()

    def process_update_data_from_server(self, item_payload: str):
        if not item_payload: return
        parts = item_payload.split('$#')
        if len(parts) >= 7:
            item_id, start_nr, name, s_class, round_nr, run_time, ts = parts[:7]
            updated_data = {"start_nummer": start_nr, "racer_name": name, "soapbox_class": s_class,
                            "round_number_main": round_nr, "renn_zeit": run_time, "mess_zeit_combined": ts}
            with self._all_race_data_lock:
                self.all_race_data_dict[item_id] = updated_data
            self._sort_and_refresh_data_treeview(highlight_item_id=item_id)

    def process_delete_data_from_server(self, item_id_to_delete: str):
        item_id = item_id_to_delete.strip()
        if item_id:
            with self._all_race_data_lock:
                if item_id in self.all_race_data_dict: del self.all_race_data_dict[item_id]
            self._sort_and_refresh_data_treeview()


if __name__ == "__main__":
    app = ModeratorApp()
    app.mainloop()