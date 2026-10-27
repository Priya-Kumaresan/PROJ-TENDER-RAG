import ollama


class TenderLLM:

    def __init__(
        self,
        model_name="llama3.2:3b"
    ):
        self.model_name = model_name


    def generate_answer(
        self,
        question,
        context
    ):
        """
        Generate a grounded answer using
        only the retrieved tender context.
        """

        prompt = f"""
You are an assistant for analysing construction tender documents.

Answer the user's question using ONLY the tender evidence provided below.

Rules:
1. Do not use outside knowledge.
2. Do not invent tender requirements.
3. If the answer is not supported by the evidence, say:
   "The information was not found in the retrieved tender evidence."
4. Keep numerical values exactly as stated in the evidence.
5. Include the relevant section number, section title, and page number.
6. Give a concise and clear answer.

TENDER EVIDENCE:
{context}

USER QUESTION:
{question}

ANSWER:
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