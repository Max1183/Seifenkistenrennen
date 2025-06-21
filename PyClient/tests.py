import time
import queue
from pynput import keyboard


def get_scan():
    """
    Wartet auf einen einzelnen Scan von einem Barcode-Scanner und gibt das Ergebnis zurück.

    Diese Funktion unterscheidet zwischen schnellen Scannereingaben und langsamen,
    manuellen Tastatureingaben. Nur die schnellen Eingaben, die mit "Enter"
    abgeschlossen werden, werden als gültiger Scan betrachtet.

    :return: Den gescannten Code als String.
    """
    # --- Konfiguration ---
    # Zeit in Sekunden. Wenn die Zeit zwischen zwei Tastenanschlägen größer ist,
    # wird die Eingabe als "manuell" verworfen und der Puffer geleert.
    INPUT_TIMEOUT = 0.05  # 50 Millisekunden

    data_queue = queue.Queue()
    state = {'buffer': [], 'last_key_time': 0}
    listener_ref = [None]  # Referenz, um den Listener von innen stoppen zu können

    def on_press(key):
        """Wird bei jedem Tastenanschlag im Hintergrund aufgerufen."""
        current_time = time.time()

        # Timeout-Logik: Ist die Pause seit der letzten Taste zu lang?
        if current_time - state['last_key_time'] > INPUT_TIMEOUT:
            state['buffer'] = []  # Ja, also Puffer leeren (manuelle Eingabe)

        state['last_key_time'] = current_time

        try:
            # Füge das Zeichen dem Puffer hinzu
            if key.char:
                state['buffer'].append(key.char)
        except AttributeError:
            # Es ist eine Sondertaste (kein .char Attribut)
            if key == keyboard.Key.enter:
                # Enter beendet die Eingabe
                if state['buffer']:
                    scanned_data = "".join(state['buffer'])
                    data_queue.put(scanned_data)  # Ergebnis in die Queue legen
                    # Den Listener stoppen, da wir unseren Scan haben
                    if listener_ref[0]:
                        listener_ref[0].stop()

    # Listener erstellen und starten
    listener = keyboard.Listener(on_press=on_press)
    listener_ref[0] = listener  # Referenz speichern
    listener.start()

    print("Scanner ist bereit. Bitte scannen Sie jetzt...")

    # Warten, bis der Listener ein Ergebnis in die Queue gelegt hat.
    # .get() blockiert das Programm, bis ein Element verfügbar ist.
    result = data_queue.get()

    # Sicherstellen, dass der Listener-Thread sauber beendet wurde
    listener.join()

    return result


# --- BEISPIEL FÜR DIE ANWENDUNG ---
if __name__ == "__main__":
    print("Willkommen beim Inventur-Programm!")

    try:
        # Die Funktion aufrufen, um den ersten Scan zu erhalten
        artikel_code = get_scan()
        print(f"✅ Artikel erfasst: {artikel_code}")

        # Man kann sie einfach erneut aufrufen für den nächsten Scan
        lagerplatz = get_scan()
        print(f"✅ Lagerplatz erfasst: {lagerplatz}")

        print("\n--- Zusammenfassung ---")
        print(f"Buchung: Artikel '{artikel_code}' an Lagerplatz '{lagerplatz}'.")

    except KeyboardInterrupt:
        print("\nProgramm abgebrochen.")