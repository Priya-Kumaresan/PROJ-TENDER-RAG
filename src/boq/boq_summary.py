import math


def is_missing(value):

    if value is None:
        return True

    if (
        isinstance(value, float)
        and math.isnan(value)
    ):
        return True

    return False


def calculate_boq_summary(items):

    quoted_subtotal = 0
    corrected_subtotal = 0

    incomplete_items = 0

    gst_rates = []


    for item in items:

        quantity = item.get("quantity")
        rate = item.get("rate")
        quoted_amount = item.get(
            "quoted_amount"
        )

        # -----------------------------
        # Quoted subtotal
        # -----------------------------

        if not is_missing(
            quoted_amount
        ):

            quoted_subtotal += (
                quoted_amount
            )


        # -----------------------------
        # Corrected subtotal
        # -----------------------------

        if (
            not is_missing(quantity)
            and not is_missing(rate)
        ):

            corrected_subtotal += (
                quantity * rate
            )

        else:

            incomplete_items += 1


        # -----------------------------
        # GST rates
        # -----------------------------

        gst = item.get("gst")

        if not is_missing(gst):

            gst_rates.append(gst)


    # Determine common GST rate

    unique_gst_rates = sorted(
        set(gst_rates)
    )

    gst_rate = None

    if len(unique_gst_rates) == 1:

        gst_rate = (
            unique_gst_rates[0]
        )


    # GST calculation

    corrected_gst = None
    corrected_total = None

    if gst_rate is not None:

        corrected_gst = (
            corrected_subtotal
            * gst_rate
            / 100
        )

        corrected_total = (
            corrected_subtotal
            + corrected_gst
        )


    return {
        "quoted_subtotal":
            quoted_subtotal,

        "corrected_subtotal":
            corrected_subtotal,

        "subtotal_difference":
            corrected_subtotal
            - quoted_subtotal,

        "gst_rate":
            gst_rate,

        "corrected_gst":
            corrected_gst,

        "corrected_total":
            corrected_total,

        "incomplete_items":
            incomplete_items,

        "gst_rates_found":
            unique_gst_rates
    }