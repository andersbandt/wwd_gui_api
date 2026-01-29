
import os
import re
import glob
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


# TODO: finish extracting the rest of this stuff as a file


data_dir = "data/data"  # Replace with your actual path
#pattern = re.compile(r"AREC_b(\d+)_([-\d]+)_.*\.csv")
pattern = re.compile(r"^AREC_b(\d+)_(\d+)_(\d+uH)_(\d+)(?:\.csv)?$")


###########################################
### USER HAS TO FILLOUT THIS SECTION ######
# ---- Generic mapping of regex groups → variable names and converters ----
# Index is 1-based to match re.group(n)
group_schema = {
    1: ("var1", str),   # e.g., board number as string
    2: ("var2", float), # e.g., temperature as float
}


x_var = "Duty"
y_var = "P_out"
y_scale = 10**3
label_var = "PWM"
title = "Duty cycle vs Output power at various switching frequencies"

x_label = "Duty cycle (%)"
y_label = "Power out (mW)"
file_graph_label = ""

# Name to filter on (choose one of the names you placed in group_schema)
filter_by = "var1"
filter_value = None
####        END OF USER FILL OUIT       ####
############################################


files = []  # list of (filepath, vars_dict)
for filename in os.listdir(data_dir):
    if not filename.endswith(".csv"):
        continue
    m = pattern.match(filename)
    if not m:
        continue

    # Build a vars dict from the regex match dynamically
    vars_dict = {}
    for idx, (name, caster) in group_schema.items():
        try:
            vars_dict[name] = caster(m.group(idx))
        except (IndexError, ValueError) as ex:
            # If a group is missing or cast fails, skip this file
            # (You can log/print ex if desired)
            vars_dict = None
            break

    filepath = os.path.join(data_dir, filename)
    df = pd.read_csv(filepath)
    files.append((filepath, vars_dict, df))


# extract labeling (ONLY USE IF LABEL IS NOT EMBEDDED IN FILENAME, otherwise use vars_dict)
# --- Build a color map for the label_var across all files ---
# Collect unique label values (e.g., PWM) from all CSVs
label_values = []
for _, _, df in files:
    if label_var not in df.columns:
        raise KeyError(f"Column '{label_var}' not found in one of the CSV files.")
    label_values.extend(df[label_var].dropna().unique())

# Unique + sorted (for consistent coloring)
unique_labels = sorted(set(label_values))

# Simple numeric normalization (works if labels are numeric or can be cast to float)
# If labels are strings, we'll just index them
try:
    # Attempt numeric normalization (e.g., PWM values like 0, 25, 50, 75, 100)
    import numpy as np
    lbl_arr = np.array(unique_labels, dtype=float)
    vmin, vmax = lbl_arr.min(), lbl_arr.max()
    norm_lbl = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap_lbl = plt.get_cmap('tab10')  # or 'viridis', 'plasma' etc.
    color_for_label = {val: cmap_lbl(norm_lbl(float(val))) for val in unique_labels}
except Exception:
    # Fallback: categorical colors (e.g., strings)
    cmap_lbl = plt.get_cmap('tab10')
    color_for_label = {val: cmap_lbl(i % 10) for i, val in enumerate(unique_labels)}

# Track which labels have already been added to the legend
legend_added = set()



# set up plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.set_xlabel(x_label)
ax.set_ylabel(y_label)
ax.set_title(title)
ax.grid(True)
plt.tight_layout()


for filepath, vars_dict, df in files:
    if filter_value is not None:
        if vars_dict[filter_by] != filter_value:
            continue

    for label_val in sorted(df[label_var].dropna().unique()):
        df_pwm = df[df[label_var] == label_val]

        color = color_for_label[label_val]

        # Only add one legend entry per PWM value
        label = f"{label_var}={label_val}" if label_val not in legend_added else None
        if label is not None:
            legend_added.add(label_val)

        ax.plot(df_pwm[x_var], df_pwm[y_var] * y_scale, label=label, color=color)


# show plot
ax.legend()
plt.show()

