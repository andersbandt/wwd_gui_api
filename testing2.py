
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

data_dir = "data/data"  # Replace with your actual path
filter_board = ["10", "11", "12"]
pattern = re.compile(r"AREC_b(\d+)_([-\d]+)_.*\.csv")


# Collect temperatures for normalization
temps = []
files = []
for filename in os.listdir(data_dir):
    if filename.endswith(".csv"):
        match = pattern.match(filename)
        if match:
            board_num = match.group(1)
            temp = float(match.group(2))
            filepath = os.path.join(data_dir, filename)
            temps.append(temp)
            files.append((filepath, board_num, temp))

# Normalize temps for colormap
norm = mcolors.Normalize(vmin=min(temps), vmax=max(temps))
cmap = plt.get_cmap('viridis')  # ✅ Updated for Matplotlib 3.7+

fig, ax = plt.subplots(figsize=(10, 6))


for filepath, board_num, temp in files:
    if board_num not in filter_board:
        continue

    df = pd.read_csv(filepath)
    color = cmap(norm(temp))  # Assign color based on temp
    ax.plot(df['V_set'], df['P_out'] * 10**3, label=f"Board {board_num}, Temp {temp}°C", color=color)

# Add colorbar
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax)  # ✅ Explicitly attach to Axes
cbar.set_label('Temperature (°C)')

ax.set_xlabel("Thermopile (V)")
ax.set_ylabel("Sync power out (mW)")
ax.set_title("Sync-boost performance across temperature")
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.show()
