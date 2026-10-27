"""
LLM Generator Module for RAG Assistant
Interacts with local Ollama service (llama3.2:3b) to generate evidence-grounded answers.
Includes a fail-safe deterministic extraction fallback if Ollama service is unavailable.
"""

import re
from typing import Optional

try:
    import ollama
except ImportError:
    ollama = None


class TenderLLM:
    """
    Interface to local Ollama LLM for grounded question answering on tender documents.
    """

    def __init__(self, model_name: str = "llama3.2:3b"):
        self.model_name = model_name

    def _fallback_extractive_answer(self, question: str, context: str) -> str:
        """
        Deterministic evidence extraction fallback used when Ollama is offline or unreachable.
        Extracts key sentences matching question terms.
        """
        if not context or not context.strip():
            return "The information was not found in the retrieved tender evidence."

        q_low = question.lower()

        # Direct clause extraction for standard tender queries
        if any(k in q_low for k in ["completion", "time allowed", "schedule", "period"]):
            m = re.search(r"([^\n]*?(?:time allowed|completed within|completion period)[^\n]*?(?<!Rs)(?<!No)\.\s)", context + " ", re.IGNORECASE)
            if m:
                return (
                    f"**Tender Completion Schedule:**\n\n{m.group(1).strip()}\n\n"
                    f"*(Source: BSNL Notice Inviting Tender)*"
                )

        if any(k in q_low for k in ["emd", "earnest money", "deposit"]):
            m = re.search(r"([^\n]*?Earnest Money[^\n]*?(?<!Rs)(?<!No)\.\s)", context + " ", re.IGNORECASE)
            if m:
                return (
                    f"**Earnest Money Deposit (EMD) Requirement:**\n\n{m.group(1).strip()}\n\n"
                    f"*(Source: BSNL Notice Inviting Tender)*"
                )

        if any(k in q_low for k in ["performance security", "performance guarantee", "security deposit"]):
            m = re.search(r"([^\n]*?Performance Guarantee[^\n]*?(?<!Rs)(?<!No)\.\s)", context + " ", re.IGNORECASE)
            if m:
                return (
                    f"**Performance Guarantee Requirement:**\n\n{m.group(1).strip()}\n\n"
                    f"*(Source: BSNL Notice Inviting Tender)*"
                )

        # Extract sentences from context
        clean_context = re.sub(r"\[Section [^\]]+\]", "", context)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_context) if len(s.strip()) > 10]

        q_terms = [t.lower() for t in re.findall(r"\b\w{3,}\b", question) if t.lower() not in ("what", "which", "where", "when", "does", "tender")]

        scored_sentences = []
        for s in sentences:
            s_lower = s.lower()
            matches = sum(1 for term in q_terms if term in s_lower)
            if matches > 0:
                scored_sentences.append((matches, s))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        if scored_sentences:
            best_sentences = [s[1] for s in scored_sentences[:3]]
            extracted_text = " ".join(best_sentences)
            return (
                f"**Extracted Tender Evidence:**\n\n{extracted_text}\n\n"
                f"*(Note: Generated via direct evidence extraction as local Ollama service was unavailable.)*"
            )

        return (
            f"**Retrieved Evidence Excerpt:**\n\n{context[:400]}...\n\n"
            f"*(Note: Generated via direct evidence extraction as local Ollama service was unavailable.)*"
        )

    def generate_answer(self, question: str, context: str) -> str:
        """
        Generate a grounded answer using only retrieved tender context.
        Attempts Ollama first; safely falls back to deterministic extraction on failure.
        """
        if not context or not context.strip():
            return "The information was not found in the retrieved tender evidence."

        prompt = f"""You are an assistant for analysing construction tender documents.

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
        if ollama is not None:
            try:
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
                return response["message"]["content"]
            except Exception:
                # Ollama daemon not running or connection error
                return self._fallback_extractive_answer(question, context)

        return self._fallback_extractive_answer(question, context)
