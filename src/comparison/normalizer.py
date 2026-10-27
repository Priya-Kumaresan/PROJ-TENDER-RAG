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

    text = str(value).strip()

    text = re.sub(
        r"(?i)(inr|rs\.?|₹)",
        "",
        text
    )

    text = text.replace(",", "").strip()

    try:
        return float(text)

    except ValueError:
        return value


def normalize_duration(value):

    if value is None:
        return None

    text = str(value).strip().lower()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
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