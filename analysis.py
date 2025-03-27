import json
import pandas as pd
import numpy as np

def extract_template_utilities_and_agreements(json_data):
    utilities = []
    agreements = 0
    for entry in json_data:
        if entry.get("result") == "agreement":
            agreements += 1
        for key in entry:
            if key.startswith("agent_") and entry[key] == "TemplateAgent":
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

def save_stats_to_csv(stats, output_path="utility stats/utility_stats_summary_10_VS_Dreamteam109_DOMAIN01.csv"):
    df = pd.DataFrame([stats])
    df.to_csv(output_path, index=False)
    print(f"✅ Stats saved to '{output_path}'")

def main(json_path):
    with open(json_path, "r") as file:
        data = json.load(file)

    utilities, agreement_count, total_runs = extract_template_utilities_and_agreements(data)

    if not utilities:
        print("⚠️ No TemplateAgent utilities found.")
        return

    stats = analyze_utilities(utilities, agreement_count, total_runs)
    save_stats_to_csv(stats)

if __name__ == "__main__":
    main("results\\10_vs_Dreamteam109_domain01_20250327-230152\\all_summaries.json")
