import json

from src.comparison.bid_comparator import (
    compare_bids
)


# ============================================================
# LOAD PROCESSED DATA
# ============================================================

with open(
    "data/processed/tender_001/tender.json",
    "r",
    encoding="utf-8"
) as file:

    tender_data = json.load(
        file
    )


with open(
    "data/processed/tender_001/bidder_A.json",
    "r",
    encoding="utf-8"
) as file:

    bidder_a_data = json.load(
        file
    )


with open(
    "data/processed/tender_001/bidder_B.json",
    "r",
    encoding="utf-8"
) as file:

    bidder_b_data = json.load(
        file
    )


# ============================================================
# COMPARE
# ============================================================

result = compare_bids(

    tender_data[
        "tender_fields"
    ],

    bidder_a_data[
        "bidder_fields"
    ],

    bidder_b_data[
        "bidder_fields"
    ],

    bidder_a_data[
        "bidder_name"
    ],

    bidder_b_data[
        "bidder_name"
    ]
)


# ============================================================
# DISPLAY
# ============================================================

print(
    "\nBIDDER COMPARISON"
)

print(
    "=" * 70
)


summary = result[
    "summary"
]


print(
    "Fields Compared:",
    summary[
        "fields_compared"
    ]
)


print(
    "Bidder A Compliant:",
    summary[
        "bidder_a_compliant"
    ]
)


print(
    "Bidder B Compliant:",
    summary[
        "bidder_b_compliant"
    ]
)


print(
    "\nREQUIREMENT COMPARISON"
)

print(
    "=" * 70
)


for item in result[
    "field_comparisons"
]:

    print(
        f"\nField: {item['field']}"
    )


    print(
        "Tender:",
        item["tender_requirement"]
    )


    print(
        "Bidder A:",
        item["bidder_a_value"],
        "|",
        item["bidder_a_status"]
    )


    print(
        "Bidder B:",
        item["bidder_b_value"],
        "|",
        item["bidder_b_status"]
    )


print(
    "\nIMPORTANT DIFFERENCES"
)

print(
    "=" * 70
)


for item in result[
    "differences"
]:

    print(
        "\nField:",
        item["field"]
    )

    print(
        "Impact:",
        item["impact"]
    )

    print(
        "Analysis:",
        item["message"]
    )