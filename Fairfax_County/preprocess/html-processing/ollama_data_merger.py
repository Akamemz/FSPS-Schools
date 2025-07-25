import pandas as pd
import requests
import json
import re
import os
from difflib import SequenceMatcher

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"


def query_ollama(prompt):
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })
    return response.json()['response']


def extract_json_dict(text):
    start = text.find('{')
    if start == -1:
        raise ValueError("No opening brace found.")
    brace_count, in_str, escape = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if c == '"' and not escape:
            in_str = not in_str
        elif c == '\\' and not escape:
            escape = True
            continue
        elif not in_str:
            if c == '{':
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = text[start:i + 1]
                    json.loads(json_str)  # check if valid
                    return json_str
        escape = False
    raise ValueError("No valid JSON found.")


def normalize_school_name(name):
    """Enhanced normalization to handle common school name variations"""
    if pd.isna(name):
        return ""

    name = str(name).lower().strip()

    # Handle common abbreviations and variations
    replacements = {
        # School type abbreviations
        " elementary school": " es",
        " middle school": " ms",
        " high school": " hs",
        " secondary school": " ss",
        " elementary": " es",
        " middle": " ms",
        " high": " hs",
        " secondary": " ss",
        " school": "",

        # Common word variations
        " center": " ctr",
        " centre": " ctr",
        " academy": " acad",
        " alternative": " alt",
        " international": " intl",
        " magnet": " mag",
        " charter": " chtr",

        # Remove common suffixes that might cause mismatches
        " campus": "",
        " facility": "",
        " program": "",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # Remove extra whitespace and special characters
    name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
    name = re.sub(r'\s+', ' ', name)  # Normalize whitespace

    return name.strip()


def fuzzy_match_schools(csv_names, excel_names, threshold=0.8):
    """First attempt fuzzy matching before using Ollama"""
    matches = {}

    for csv_name in csv_names:
        best_match = None
        best_score = 0

        for excel_name in excel_names:
            score = SequenceMatcher(None, csv_name, excel_name).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = excel_name

        if best_match:
            matches[csv_name] = best_match
            print(f"Fuzzy matched: '{csv_name}' -> '{best_match}' (score: {best_score:.2f})")

    return matches


def get_name_mapping(known_names, csv_names, batch_size=15):
    """Get name mapping from Ollama with improved prompting"""
    mapping = {}

    for i in range(0, len(csv_names), batch_size):
        chunk = csv_names[i:i + batch_size]

        # Create a more structured prompt with examples
        prompt = f"""
You are helping match school names. Here are the official school names:
{json.dumps(known_names)}

Match each dataset name to the closest official name. Consider:
- "Elementary" = "ES", "Middle" = "MS", "High" = "HS"
- Ignore minor spelling differences
- Focus on the core school name

Dataset names to match:
{json.dumps(chunk)}

Return ONLY valid JSON (use double quotes):
{{
    "dataset_name_1": "official_name_1",
    "dataset_name_2": "official_name_2"
}}

Examples:
- "aldrin elementary" should match "aldrin es"
- "washington middle school" should match "washington ms"
"""

        print(f"Querying Ollama for batch {i // batch_size + 1}...")
        response = query_ollama(prompt)

        try:
            dict_str = extract_json_dict(response)
            chunk_mapping = json.loads(dict_str)
            mapping.update(chunk_mapping)
            print(f"Successfully mapped {len(chunk_mapping)} schools in this batch")
        except Exception as e:
            print(f"\n[WARNING] Failed to extract/parse dictionary for batch {i // batch_size + 1}")
            print("Raw response:\n", response)
            print("Skipping this batch.\n")
            continue

    return mapping


def process_dataset(dataset_name, csv_path, excel_path, output_path, cached_mapping=None):
    """Process a single dataset (breakfast or lunch)"""
    print(f"\n{'=' * 50}")
    print(f"Processing {dataset_name.upper()} dataset")
    print(f"{'=' * 50}")

    # Load data
    print("Loading datasets...")
    csv_df = pd.read_csv(csv_path)
    excel_df = pd.read_excel(excel_path)

    # Filter out dummy/test schools
    test_schools = ["Test Site Elementary School", "Test Site Elementary", "test site elementary school"]
    initial_count = len(csv_df)
    csv_df = csv_df[~csv_df['School_Name'].isin(test_schools)]
    filtered_count = initial_count - len(csv_df)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} test/dummy school records")

    print(f"CSV dataset: {len(csv_df)} rows")
    print(f"Excel dataset: {len(excel_df)} rows")

    # Store original names
    csv_df['Original_School_Name'] = csv_df['School_Name'].str.strip()
    excel_df['Original_School_Name'] = excel_df['School Name'].str.strip()

    # Normalize names
    print("Normalizing school names...")
    csv_df['Normalized_School_Name'] = csv_df['Original_School_Name'].apply(normalize_school_name)
    excel_df['Normalized_School_Name'] = excel_df['Original_School_Name'].apply(normalize_school_name)

    # Get unique normalized names
    csv_names = sorted(csv_df['Normalized_School_Name'].unique())
    excel_names = sorted(excel_df['Normalized_School_Name'].unique())

    print(f"Unique CSV school names: {len(csv_names)}")
    print(f"Unique Excel school names: {len(excel_names)}")

    # Use cached mapping if available
    if cached_mapping:
        print("Using cached mapping from previous dataset...")
        cached_matches = {name: cached_mapping[name] for name in csv_names if name in cached_mapping}
        print(f"Found {len(cached_matches)} schools in cache")
    else:
        cached_matches = {}

    # Find names that still need mapping
    unmatched_names = [name for name in csv_names if name not in cached_matches]

    # First try fuzzy matching for unmatched names
    print(f"\nAttempting fuzzy matching for {len(unmatched_names)} schools...")
    fuzzy_matches = fuzzy_match_schools(unmatched_names, excel_names)

    # Find names that still need Ollama mapping
    still_unmatched = [name for name in unmatched_names if name not in fuzzy_matches]
    print(f"Fuzzy matched: {len(fuzzy_matches)} schools")
    print(f"Still need mapping: {len(still_unmatched)} schools")

    # Use Ollama for remaining unmatched names
    ollama_mapping = {}
    if still_unmatched:
        print("\nUsing Ollama for remaining schools...")
        ollama_mapping = get_name_mapping(excel_names, still_unmatched)

    # Combine all mappings
    final_mapping = {**cached_matches, **fuzzy_matches, **ollama_mapping}

    # Apply mapping to CSV data
    csv_df['Mapped_Normalized_Name'] = csv_df['Normalized_School_Name'].map(final_mapping)
    csv_df['Mapped_Normalized_Name'] = csv_df['Mapped_Normalized_Name'].fillna(csv_df['Normalized_School_Name'])

    # Merge datasets
    print("\nMerging datasets...")
    merged = csv_df.merge(
        excel_df,
        how='left',
        left_on='Mapped_Normalized_Name',
        right_on='Normalized_School_Name',
        suffixes=('_csv', '_excel')
    )

    # Save results
    merged.to_csv(output_path, index=False)
    print(f"Merged file saved as '{output_path}'")

    # Check results
    unmapped = merged[merged['School Name'].isna()]
    print(f"\nMapping results:")
    print(f"Total rows: {len(merged)}")
    print(f"Successfully mapped: {len(merged) - len(unmapped)}")
    print(f"Unmapped: {len(unmapped)}")

    if len(unmapped) > 0:
        print("\nUnmapped schools:")
        for school in unmapped['Original_School_Name_csv'].unique():
            print(f"  - {school}")

    return merged, final_mapping


def main():
    """Main function to process both breakfast and lunch datasets"""

    # Define dataset configurations
    datasets = {
        "breakfast": {
            "csv_path": "../../preprocess/html-processing/preprocessed-data/Breakfast production/breakfast_combined.csv",
            "output_path": "../../preprocess/html-processing/preprocessed-data/Breakfast production/Breakfast_cost.csv"
        },
        "lunch": {
            "csv_path": "../../preprocess/html-processing/preprocessed-data/Lunch production/lunch_combined.csv",
            "output_path": "../../preprocess/html-processing/preprocessed-data/Lunch production/Lunch_cost.csv"
        }
    }

    # Common Excel file path
    excel_path = "../../Data/FairfaxCounty/FCPS Schools list.xlsx"

    # Process datasets
    all_mappings = {}
    cached_mapping = None

    for dataset_name, config in datasets.items():
        # Check if CSV file exists
        if not os.path.exists(config["csv_path"]):
            print(f"Warning: {config['csv_path']} not found. Skipping {dataset_name} dataset.")
            continue

        try:
            merged_df, mapping = process_dataset(
                dataset_name=dataset_name,
                csv_path=config["csv_path"],
                excel_path=excel_path,
                output_path=config["output_path"],
                cached_mapping=cached_mapping
            )

            # Store mapping for next dataset
            all_mappings[dataset_name] = mapping
            cached_mapping = mapping  # Use this mapping as cache for next dataset

            print(f"\n{dataset_name.capitalize()} dataset processed successfully!")

        except Exception as e:
            print(f"\nError processing {dataset_name} dataset: {str(e)}")
            continue

    # Save combined mapping
    if all_mappings:
        combined_mapping_path = "combined_name_mapping.json"
        with open(combined_mapping_path, "w") as f:
            json.dump(all_mappings, f, indent=2)
        print(f"\nCombined mapping saved to '{combined_mapping_path}'")

    print(f"\n{'=' * 50}")
    print("Processing complete!")
    print(f"{'=' * 50}")

    return all_mappings


if __name__ == "__main__":
    mappings = main()


# import pandas as pd
# import requests
# import json
# import re
#
# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL = "llama3.2"
#
#
# def query_ollama(prompt):
#     """Send prompt to Ollama and return the full response"""
#     response = requests.post(OLLAMA_URL, json={
#         "model": MODEL,
#         "prompt": prompt,
#         "stream": False
#     })
#     return response.json()['response']
#
#
# def extract_json_dict(text):
#     """Extract the first valid JSON dictionary block from LLaMA output"""
#     match = re.search(r"\{[\s\S]*?}", text)
#     if not match:
#         raise ValueError("No dictionary found in response.")
#     return match.group(0)
#
#
# def get_name_mapping(known_names, csv_names, batch_size=25):
#     """Break CSV names into chunks and query Ollama to match to known names"""
#     mapping = {}
#     for i in range(0, len(csv_names), batch_size):
#         chunk = csv_names[i:i+batch_size]
#         prompt = f"""
# You are a Python developer. I have a list of official school names:
# {json.dumps(known_names)}
#
# Now I have a list of school names from a dataset:
# {json.dumps(chunk)}
#
# Please match each dataset name to the closest official name. Return ONLY a valid JSON dictionary (use double quotes) in the format:
# {{
#   "dataset_name_1": "official_name_1",
#   "dataset_name_2": "official_name_2"
# }}
#
# Do not include explanations, imports, or function definitions. Just output a dictionary.
# """
#
#         print(f"Querying Ollama for batch {i // batch_size + 1}...")
#         response = query_ollama(prompt)
#
#         try:
#             dict_str = extract_json_dict(response)
#             chunk_mapping = json.loads(dict_str)
#             mapping.update(chunk_mapping)
#         except Exception as e:
#             print("Failed to extract/parse dictionary from response:")
#             print(response)
#             raise e
#
#     return mapping
#
#
# # # ===========
# # # Breakfast
# # # ===========
# #
# # # Load datasets
# # csv_df = pd.read_csv("../../preprocess/html-processing/preprocessed-data/Breakfast production/breakfast_combined.csv")
# # excel_df = pd.read_excel("../../Data/FairfaxCounty/FCPS Schools list.xlsx")
# #
# # # Strip whitespace
# # csv_df['School_Name'] = csv_df['School_Name'].str.strip()
# # excel_df['School Name'] = excel_df['School Name'].str.strip()
# #
# # # Get unique names
# # csv_names = sorted(csv_df['School_Name'].unique().tolist())
# # excel_names = sorted(excel_df['School Name'].unique().tolist())
# #
# # # Generate name mapping using Ollama
# # name_mapping = get_name_mapping(excel_names, csv_names)
# #
# # # Apply mapping
# # csv_df['School_Name_Mapped'] = csv_df['School_Name'].replace(name_mapping)
# #
# # # Merge on mapped name
# # merged = csv_df.merge(excel_df, how='left', left_on='School_Name_Mapped', right_on='School Name')
# #
# # # Save result
# # merged.to_csv("../../preprocess/html-processing/preprocessed-data/Breakfast production/Breakfast_cost.csv", index=False)
# # print("Merged file saved as 'Breakfast_cost.csv'")
#
#
# # ------------------------------------------------------------------------------------------------
#
# # ===========
# # Lunch
# # ===========
#
# # # Load datasets
# # csv_df = pd.read_csv("../../preprocess/html-processing/preprocessed-data/Lunch production/lunch_combined.csv", dtype=str)
# # excel_df = pd.read_excel("../../Data/FairfaxCounty/FCPS Schools list.xlsx")
# #
# # # Strip whitespace
# # csv_df['School_Name'] = csv_df['School_Name'].str.strip()
# # excel_df['School Name'] = excel_df['School Name'].str.strip()
# #
# # # Get unique names
# # csv_names = sorted(csv_df['School_Name'].unique().tolist())
# # excel_names = sorted(excel_df['School Name'].unique().tolist())
# #
# # # Generate name mapping using Ollama
# # name_mapping = get_name_mapping(excel_names, csv_names)
# #
# # # Apply mapping
# # csv_df['School_Name_Mapped'] = csv_df['School_Name'].replace(name_mapping)
# #
# # # Merge on mapped name
# # merged = csv_df.merge(excel_df, how='left', left_on='School_Name_Mapped', right_on='School Name')
# #
# # # Save result
# # merged.to_csv("../../preprocess/html-processing/preprocessed-data/Lunch production/Lunch_cost.csv", index=False)
# # print("Merged file saved as 'Lunch_cost.csv'")
