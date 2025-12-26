# plot_reasoning_usage.py
# Visual dashboard for reasoning strategy usage over time (simulated data)

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Define strategies
strategies = [
    "chain_of_thought",
    "self_consistency",
    "tree_of_thought",
    "reflexion",
    "react",
    "retrieval_augmented_generation",
    "debate",
    "self_refine"
]

# Simulate usage logs for past 30 days
dates = [datetime.today() - timedelta(days=i) for i in range(29, -1, -1)]  # 30 days, oldest to newest
log_data = {
    "date": [],
    "strategy": [],
    "count": []
}

# Generate random usage counts
for strategy in strategies:
    daily_counts = np.abs(np.random.normal(loc=20, scale=5, size=30)).astype(int)
    for i, count in enumerate(daily_counts):
        log_data["date"].append(dates[i].strftime("%Y-%m-%d"))
        log_data["strategy"].append(strategy)
        log_data["count"].append(count)

# Convert to DataFrame and pivot
df = pd.DataFrame(log_data)
pivot_df = df.pivot(index="date", columns="strategy", values="count").fillna(0)

# Plot
plt.figure(figsize=(14, 6))
for strategy in strategies:
    plt.plot(pivot_df.index, pivot_df[strategy], label=strategy)

plt.title("Reasoning Strategy Usage Over Time (Last 30 Days)")
plt.xlabel("Date")
plt.ylabel("Invocation Count")
plt.xticks(rotation=45)
plt.legend(loc="upper left")
plt.tight_layout()
plt.grid(True)
plt.show()
