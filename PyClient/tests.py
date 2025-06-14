import json
import os

run_time = ["1"]
print(run_time.append("1"))

if not os.path.exists("run_times.json"):
    with open("run_times.json", "w") as f:
        json.dump([run_time], f)
else:
    with open("run_times.json", "r") as f:
        run_times_saved = json.load(f)
        print(list(run_times_saved))
    with open("run_times.json", "w") as f:
        print(list(run_times_saved).append(run_time))
        json.dump(list(run_times_saved).append(run_time), f)
print(f"Arduino Zeitmessung empfangen: {run_time}")