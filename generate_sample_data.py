"""
Generate synthetic CCSP/DepMap-like sample data for the MCP server demo.
Produces CSV files that mimic PRISM drug sensitivity screening results.
"""

import csv
import random
import os
from pathlib import Path

random.seed(42)

# Realistic compound names (mix of approved drugs and research compounds)
COMPOUNDS = [
    "Erlotinib", "Sorafenib", "Lapatinib", "Crizotinib", "Olaparib",
    "Venetoclax", "Palbociclib", "Trametinib", "Dabrafenib", "Osimertinib",
    "LY-3009120", "LY-2874455", "LY-3214996", "LY-2835219", "LY-3023414"
]

# Cancer lineages
LINEAGES = [
    "Lung", "Breast", "Colorectal", "Pancreatic", "Ovarian",
    "Kidney", "Liver", "Melanoma", "Leukemia", "Lymphoma",
    "Gastric", "Bladder", "Prostate", "Brain_CNS", "Head_Neck"
]

# Cell lines per lineage (3-5 per lineage for demo)
CELL_LINES = {
    "Lung": ["A549", "NCI-H1299", "NCI-H460", "PC-9", "HCC827"],
    "Breast": ["MCF7", "MDA-MB-231", "T47D", "BT474", "SKBR3"],
    "Colorectal": ["HCT116", "SW480", "HT29", "LoVo", "DLD1"],
    "Pancreatic": ["PANC1", "MiaPaCa2", "AsPC1", "BxPC3", "Capan1"],
    "Ovarian": ["SKOV3", "A2780", "OVCAR3", "ES2", "CAOV3"],
    "Kidney": ["786O", "A498", "ACHN", "Caki1", "RCC10"],
    "Liver": ["HepG2", "Huh7", "SNU449", "PLC_PRF5", "SK_HEP1"],
    "Melanoma": ["A375", "SKMEL28", "WM266_4", "COLO829", "MEWO"],
    "Leukemia": ["K562", "HL60", "MOLM13", "MV411", "THP1"],
    "Lymphoma": ["Raji", "Daudi", "SUDHL4", "OCI_LY3", "Toledo"],
    "Gastric": ["AGS", "NCI_N87", "SNU16", "KATO_III", "MKN45"],
    "Bladder": ["T24", "RT4", "J82", "UMUC3", "HT1376"],
    "Prostate": ["PC3", "DU145", "LNCaP", "22Rv1", "VCaP"],
    "Brain_CNS": ["U87MG", "U251", "T98G", "LN229", "A172"],
    "Head_Neck": ["FaDu", "CAL27", "SCC25", "Detroit562", "SCC9"],
}

# Generate sensitivity profiles — some compounds work better on certain lineages
# This creates realistic-looking differential sensitivity
COMPOUND_LINEAGE_BIAS = {
    "Erlotinib": {"Lung": -0.4, "Head_Neck": -0.2},  # EGFR inhibitor
    "Sorafenib": {"Liver": -0.5, "Kidney": -0.3},     # multi-kinase
    "Lapatinib": {"Breast": -0.5},                      # HER2
    "Crizotinib": {"Lung": -0.4, "Lymphoma": -0.2},   # ALK/MET
    "Olaparib": {"Ovarian": -0.5, "Breast": -0.3},    # PARP
    "Venetoclax": {"Leukemia": -0.6, "Lymphoma": -0.5},  # BCL2
    "Palbociclib": {"Breast": -0.4, "Melanoma": -0.2},   # CDK4/6
    "Trametinib": {"Melanoma": -0.5, "Colorectal": -0.2},  # MEK
    "Dabrafenib": {"Melanoma": -0.6},                     # BRAF
    "Osimertinib": {"Lung": -0.5},                        # EGFR T790M
    "LY-3009120": {"Melanoma": -0.4, "Colorectal": -0.3},  # pan-RAF
    "LY-2874455": {"Gastric": -0.4, "Bladder": -0.3},       # FGFR
    "LY-3214996": {"Melanoma": -0.3, "Lung": -0.2},         # ERK
    "LY-2835219": {"Breast": -0.5, "Lung": -0.3},           # CDK4/6 (abemaciclib)
    "LY-3023414": {"Brain_CNS": -0.3, "Prostate": -0.2},    # PI3K/mTOR
}

output_dir = str(Path(__file__).parent / "sample_data")
os.makedirs(output_dir, exist_ok=True)


def generate_auc(compound, lineage):
    """Generate AUC value — lower means more sensitive. Range roughly 0.3–1.0"""
    base = 0.75 + random.gauss(0, 0.08)
    bias = COMPOUND_LINEAGE_BIAS.get(compound, {}).get(lineage, 0)
    value = base + bias + random.gauss(0, 0.05)
    return max(0.2, min(1.0, value))


def generate_ic50(compound, lineage):
    """Generate IC50 in µM — lower means more potent. Range roughly 0.01–50"""
    base_log = 0.5 + random.gauss(0, 0.4)  # log10(IC50)
    bias = COMPOUND_LINEAGE_BIAS.get(compound, {}).get(lineage, 0) * 2
    value = 10 ** (base_log + bias + random.gauss(0, 0.2))
    return max(0.005, min(100, value))


def generate_zc50(compound, lineage):
    """Generate ZC50 (Z-score normalized IC50). Range roughly -3 to 3"""
    bias = COMPOUND_LINEAGE_BIAS.get(compound, {}).get(lineage, 0) * 4
    return bias + random.gauss(0, 0.8)


# Generate the main dose-response matrix
print("Generating dose-response parameters...")
rows = []
for compound in COMPOUNDS:
    for lineage in LINEAGES:
        for cell_line in CELL_LINES[lineage]:
            rows.append({
                "compound": compound,
                "lineage": lineage,
                "cell_line": cell_line,
                "auc": round(generate_auc(compound, lineage), 4),
                "ic50_um": round(generate_ic50(compound, lineage), 4),
                "zc50": round(generate_zc50(compound, lineage), 4),
            })

filepath = os.path.join(output_dir, "dose_response_parameters.csv")
with open(filepath, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["compound", "lineage", "cell_line", "auc", "ic50_um", "zc50"])
    writer.writeheader()
    writer.writerows(rows)
print(f"  → {filepath} ({len(rows)} rows)")

# Generate cell line metadata
print("Generating cell line metadata...")
meta_rows = []
for lineage, lines in CELL_LINES.items():
    for cl in lines:
        meta_rows.append({
            "cell_line": cl,
            "lineage": lineage,
            "primary_disease": f"{lineage} Cancer",
            "subtype": random.choice(["Adenocarcinoma", "Squamous", "Other", "NOS"]),
            "source": random.choice(["ATCC", "ECACC", "DSMZ", "Lilly Internal"]),
        })

filepath = os.path.join(output_dir, "cell_line_metadata.csv")
with open(filepath, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["cell_line", "lineage", "primary_disease", "subtype", "source"])
    writer.writeheader()
    writer.writerows(meta_rows)
print(f"  → {filepath} ({len(meta_rows)} rows)")

# Generate compound metadata
print("Generating compound metadata...")
compound_meta = []
for compound in COMPOUNDS:
    moa = random.choice(["Kinase Inhibitor", "PARP Inhibitor", "BCL2 Inhibitor", "CDK Inhibitor", "Multi-Kinase Inhibitor"])
    if "LY-" in compound:
        phase = random.choice(["Phase I", "Phase II", "Preclinical"])
        source = "Lilly"
    else:
        phase = "Approved"
        source = "External"
    compound_meta.append({
        "compound": compound,
        "mechanism_of_action": moa,
        "target": random.choice(["EGFR", "BRAF", "MEK", "ALK", "PARP", "BCL2", "CDK4/6", "PI3K", "FGFR", "ERK"]),
        "phase": phase,
        "source": source,
    })

filepath = os.path.join(output_dir, "compound_metadata.csv")
with open(filepath, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["compound", "mechanism_of_action", "target", "phase", "source"])
    writer.writeheader()
    writer.writerows(compound_meta)
print(f"  → {filepath} ({len(compound_meta)} rows)")

print("\nDone! Sample data generated.")
