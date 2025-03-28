import json
import pandas as pd
import numpy as np

# ======================= CONFIGURATION ===========================
INPUT_JSON_PATH = "results\\10_vs_Boulware_domain00_20250328-203546\\all_summaries.json"
OUTPUT_CSV_PATH = "utility stats/utility_stats_summary_10_VS_Boulware_DOMAIN00.csv"
TARGET_AGENT_NAME = "TemplateAgent"
# ================================================================

def extract_template_utilities_and_agreements(json_data, agent_name):
    utilities = []
    agreements = 0
    for entry in json_data:
        if entry.get("result") == "agreement":
            agreements += 1
        for key in entry:
            if key.startswith("agent_") and entry[key] == agent_name:
                index = key.split("_")[1]
                util_key = f"utility_{index}"
                if util_key in entry:
                    utilities.append(entry[util_key])
                break
    return utilities, agreements, len(json_data)

def analyze_utilities(utilities, agreement_count, total_runs):
    series = pd.Series(utilities)
    stats = {
        "count": series.count(),
        "min": series.min(),
        "max": series.max(),
        "mean": series.mean(),
        "median": series.median(),
        "std_dev": series.std(),
        "variance": series.var(),
        "25th_percentile": series.quantile(0.25),
        "75th_percentile": series.quantile(0.75),
        "agreement_rate (%)": (agreement_count / total_runs) * 100
    }
    return stats

def save_stats_to_csv(stats, output_path):
    df = pd.DataFrame([stats])
    df.to_csv(output_path, index=False)
    print(f"✅ Stats saved to '{output_path}'")

def main():
    with open(INPUT_JSON_PATH, "r") as file:
        data = json.load(file)

    utilities, agreement_count, total_runs = extract_template_utilities_and_agreements(data, TARGET_AGENT_NAME)

    if not utilities:
        print("⚠️ No utilities found for agent:", TARGET_AGENT_NAME)
        return

    stats = analyze_utilities(utilities, agreement_count, total_runs)
    save_stats_to_csv(stats, OUTPUT_CSV_PATH)

if __name__ == "__main__":
    main()
