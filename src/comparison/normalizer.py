import re


def normalize_text(value):

    if value is None:
        return None

    return str(value).strip().lower()


def normalize_percentage(value):

    if value is None:
        return None

    text = str(value).strip().lower()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        text
    )

    if match:
        return float(match.group(1))

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*percent",
        text
    )

    if match:
        return float(match.group(1))

    return value


def normalize_currency(value):

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()

    # Check for Indian crore / cr notation (1 crore = 10,000,000)
    crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crores?|cr)\b", text)
    if crore_match:
        try:
            return float(crore_match.group(1)) * 10000000.0
        except ValueError:
            pass

    # Check for Indian lakh / lac notation (1 lakh = 100,000)
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|lac)\b", text)
    if lakh_match:
        try:
            return float(lakh_match.group(1)) * 100000.0
        except ValueError:
            pass

    text = re.sub(
        r"(?i)(inr|rs\.?|₹|\$|€|£)",
        "",
        text
    )

    text = text.replace(",", "").replace("/-", "").strip()

    try:
        return float(text)

    except ValueError:
        return value


def normalize_duration(value):

    if value is None:
        return None

    text = str(value).strip().lower()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:\([a-zA-Z]+\))?\s*"
        r"(days?|weeks?|months?|years?)",
        text
    )

    if match:

        return {
            "value": float(
                match.group(1)
            ),
            "unit": match.group(2)
        }

    return value


def normalize_field(field, value):

    if value is None:
        return None

    # -----------------------------------------
    # Extract actual value from field dictionary
    # -----------------------------------------

    if isinstance(value, dict):

        # Special handling for liquidated damages
        if field == "liquidated_damages":

            rate = value.get("rate")
            maximum = value.get("maximum")

            return {
                "rate":
                    normalize_percentage(rate),

                "maximum":
                    normalize_percentage(maximum)
            }

        value = value.get("value")

        if value is None:
            return None

    # -----------------------------------------
    # Field-specific normalization
    # -----------------------------------------

    field_lower = field.lower()

    if (
        "%" in str(value)
        or any(
            word in field_lower
            for word in [
                "percentage",
                "percent",
                "performance_security"
            ]
        )
    ):

        normalized = normalize_percentage(
            value
        )

        if normalized != value:
            return normalized

    if any(
        word in field_lower
        for word in [
            "emd",
            "amount",
            "cost"
        ]
    ):

        normalized = normalize_currency(
            value
        )

        if normalized != value:
            return normalized

    if any(
        word in field_lower
        for word in [
            "period",
            "duration",
            "validity",
            "completion"
        ]
    ):

        normalized = normalize_duration(
            value
        )

        if normalized != value:
            return normalized

    if isinstance(value, str):

        return normalize_text(value)

    return value