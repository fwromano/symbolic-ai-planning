import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the dataset
# df = pd.read_csv("road_metrics.csv").sort_values("segments")
df = pd.read_csv("exploration_metrics.csv").sort_values("segments")

# 1. Plan length & nodes (LOG X only for intuitive size scaling)
plt.figure()
plt.plot(df.segments, df.plan_length, marker="o", label="Plan Length")
plt.plot(df.segments, df.nodes_expanded, marker="s", label="Nodes Expanded")
plt.xscale("log", base=2)
plt.xlabel("Segments (log scale)")
plt.ylabel("Count")
plt.title("Plan Length & Nodes Expanded vs Problem Size")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("graphs/graph_plan_vs_nodes.png")

# 2. Runtime (LINEAR X to show actual runtime curvature)
plt.figure()
plt.plot(df.segments, df.runtime_s, marker="o")
plt.xlabel("Segments")
plt.ylabel("Runtime (s)")
plt.title("Runtime vs Problem Size (Linear Scale)")
plt.grid(True)
plt.tight_layout()
plt.savefig("graphs/graph_runtime_linear.png")

# 3. Runtime (LOG X, LINEAR Y)
plt.figure()
plt.plot(df.segments, df.runtime_s, marker="o")
plt.xscale("log", base=2)
plt.xlabel("Segments (log scale)")
plt.ylabel("Runtime (s)")
plt.title("Runtime vs Problem Size (Log X)")
plt.grid(True)
plt.tight_layout()
plt.savefig("graphs/graph_runtime_logx.png")

# 4. Runtime (LOG-LOG + fit)
log_n = np.log2(df.segments)
log_t = np.log2(df.runtime_s)
m, b = np.polyfit(log_n, log_t, 1)

plt.figure()
plt.scatter(log_n, log_t, label="Data")
plt.plot(log_n, m*log_n + b, label=f"Fit: slope = {m:.2f}")
plt.xlabel("log2(Segments)")
plt.ylabel("log2(Runtime)")
plt.title("Power-law Fit (Log-Log)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("graphs/graph_power_law_fit.png")

