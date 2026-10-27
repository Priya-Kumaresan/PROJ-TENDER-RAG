from src.comparison.normalizer import normalize_field
from src.comparison.comparison_analyzer import (
    analyze_comparison_differences
)

class TenderComparator:
    def compare_tenders(
        self,
        tender_a,
        tender_b
    ):
        """
        Run the complete tender comparison.
        """

        comparison = self.compare_fields(
            tender_a,
            tender_b
        )

        summary = self.create_summary(
            comparison
        )

        differences = self.get_differences(
            comparison
        )

        analyzed_differences = (
            analyze_comparison_differences(
                differences
            )
        )

        return {
            "comparison": comparison,
            "summary": summary,
            "differences": differences,
            "analyzed_differences":
                analyzed_differences
        }
    def create_summary(
        self,
        comparison
    ):
      

        total_fields = len(comparison)

        same_fields = sum(
            1
            for item in comparison
            if item["status"] == "SAME"
        )

        different_fields = sum(
            1
            for item in comparison
            if item["status"] == "DIFFERENT"
        )

        return {
            "total_fields": total_fields,
            "same_fields": same_fields,
            "different_fields": different_fields
        }

    def get_differences(
        self,
        comparison
    ):
        """
        Return only fields that differ
        between the two tenders.
        """

        differences = []

        for item in comparison:

            if item["status"] == "DIFFERENT":

                differences.append(item)

        return differences
    def compare_fields(
        self,
        tender_a,
        tender_b
    ):
        """
        Compare structured tender fields
        after normalization.
        """

        comparison = []

        field_names = sorted(
            set(tender_a.keys())
            | set(tender_b.keys())
        )

        for field in field_names:

            value_a = tender_a.get(field)
            value_b = tender_b.get(field)

            normalized_a = normalize_field(
                field,
                value_a
            )

            normalized_b = normalize_field(
                field,
                value_b
            )

            if normalized_a == normalized_b:

                status = "SAME"

            else:

                status = "DIFFERENT"

            comparison.append({
                "field": field,
                "tender_a": value_a,
                "tender_b": value_b,
                "normalized_a": normalized_a,
                "normalized_b": normalized_b,
                "status": status
            })

        return comparison