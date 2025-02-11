import random
import threading
import time

from installation_ui import InstallationUI

# Instanzen definieren
instances = ["VM1", "VM2", "VM3"]
ui = InstallationUI(instances)

# Starte die UI in einem separaten Thread
ui.run_in_thread()


def simulate_installation(instance):
    steps = ["Downloading...", "Installing...", "Configuring...", "Finalizing..."]
    for step in steps:
        time.sleep(random.uniform(1, 3))  # Simuliere Zeitaufwand für den Schritt
        ui.update_status(instance, step, "In Progress")
    time.sleep(2)  # Simuliere einen kurzen Abschluss
    ui.update_status(instance, "Completed", "✔ Success" if random.random() > 0.2 else "✘ Error")


# Starte die Simulation für jede VM in separaten Threads
threads = [threading.Thread(target=simulate_installation, args=(vm,)) for vm in instances]

# Starte alle Threads
for thread in threads:
    thread.start()

# Warte, bis alle Threads fertig sind
for thread in threads:
    thread.join()

# Warte auf die UI, bevor das Hauptprogramm beendet wird
ui.ui_thread.join()
