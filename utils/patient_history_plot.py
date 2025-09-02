import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

def plot_lab_id_timeline(df, lab_id):
    sub = df[df['REDCAP ID'] == lab_id].copy()
    if sub.empty:
        print(f"No records found for REDCAP ID: {lab_id}")
        return

    # Identify date columns
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    seen = set()
    events = []

    for col in date_cols:
        for val in sub[col].dropna().unique():
            # Convert val to datetime (if not already)
            val_dt = pd.to_datetime(val, errors='coerce')
            if pd.isna(val_dt):
                continue  # skip invalid dates
            key = (col, val_dt)
            if key not in seen:
                seen.add(key)
                events.append(key)

    if not events:
        print("No valid date entries found for this REDCAP ID.")
        return

    events_df = pd.DataFrame(events, columns=["Event", "Date"]).drop_duplicates()
    events_df.sort_values("Date", inplace=True)
    events_df.reset_index(drop=True, inplace=True)

    # Compress timeline if gaps > 2 years (730 days)
    compressed_dates = [events_df.loc[0, "Date"]]
    total_compression = timedelta(0)
    for i in range(1, len(events_df)):
        prev_date = events_df.loc[i - 1, "Date"]
        curr_date = events_df.loc[i, "Date"]
        gap = curr_date - prev_date

        if gap.days > 730:  # Gap > 2 years
            compress_to = timedelta(days=30)
            compression = gap - compress_to
            total_compression += compression
            adjusted_date = curr_date - total_compression
        else:
            adjusted_date = curr_date - total_compression

        compressed_dates.append(adjusted_date)

    events_df["CompressedDate"] = compressed_dates

    # Plot
    plt.figure(figsize=(10, max(2, 0.4 * len(events_df['Event'].unique()))))
    plt.scatter(events_df["CompressedDate"], events_df["Event"], marker='o', color='royalblue')
    for _, row in events_df.iterrows():
        plt.text(row["CompressedDate"], row["Event"], row["Date"].strftime("%d-%b-%Y"),
                 fontsize=8, ha='left', va='center')

    plt.title(f"Event Timeline for REDCAP ID: {lab_id}")
    plt.xlabel("Date (compressed when >2-year gaps)")
    plt.tight_layout()
    plt.grid(True, axis='x', linestyle='--', alpha=0.5)
    plt.show()