import ollama


class RiskExplainer:

    def __init__(
        self,
        model_name="llama3.2:3b"
    ):
        self.model_name = model_name


    def explain(self, risk):
        """
        Use the local LLM to explain a risk
        already detected by deterministic rules.
        """

        prompt = f"""
You are an evidence-grounded construction tender risk analyst.

A deterministic rule-based system has already detected a risk.

RISK TITLE:
{risk['title']}

CATEGORY:
{risk['category']}

SEVERITY:
{risk['severity']}

EXACT TENDER EVIDENCE:
{risk['evidence']}

Explain the risk strictly from the evidence above.

STRICT RULES:

1. Use ONLY information explicitly stated in the evidence.
2. Do not introduce parties, obligations, amounts,
   deadlines or consequences that are not stated.
3. Do not guess who receives a payment unless the
   evidence explicitly states it.
4. Do not change the category or severity.
5. Preserve all numerical values exactly.
6. Clearly distinguish the stated requirement from
   possible practical impact.
7. Possible impacts must be cautious and must not be
   presented as tender facts.
8. Do not provide legal advice.
9. If the evidence is insufficient to explain something,
   state that the evidence does not specify it.
10. Keep the response concise.

Return exactly:

Risk Explanation:
<explain what the evidence explicitly requires>

Potential Impact:
<brief cautious practical implication based only on the evidence>
"""

        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0
            }
        )

        return response[
            "message"
        ][
            "content"
        ]