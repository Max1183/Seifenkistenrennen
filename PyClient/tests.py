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