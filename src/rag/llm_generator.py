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

        # If context contains rich structured knowledge (evaluations, bidder profiles, comparisons, or clauses)
        paragraphs = [p.strip() for p in context.split("\n\n") if p.strip()]

        stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
            "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
            "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for",
            "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
            "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
            "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
            "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she",
            "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them",
            "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too",
            "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
            "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself", "tender"
        }

        q_terms = [t for t in re.findall(r"\b\w{2,}\b", q_low) if t not in stopwords]
        if not q_terms:
            q_terms = [t for t in re.findall(r"\b\w{2,}\b", q_low)]

        # Score paragraphs
        scored_paras = []
        for p in paragraphs:
            p_clean = re.sub(r"\[Section [^\]]+\]", "", p).strip()
            p_low = p_clean.lower()
            matches = sum(1 for term in q_terms if term in p_low)

            # Extra weight for exact phrases and key intent words
            if len(q_low) > 4 and q_low in p_low:
                matches += 5
            for k in ["worst", "disqualif", "fail", "best", "winner", "turnover", "experience", "machinery", "schedule", "quote", "rate"]:
                if k in q_low and k in p_low:
                    matches += 3

            if matches > 0:
                scored_paras.append((matches, p_clean))

        scored_paras.sort(key=lambda x: x[0], reverse=True)

        if scored_paras:
            best_paragraphs = [p[1] for p in scored_paras[:2]]
            combined = "\n\n".join(best_paragraphs)
            return (
                f"### 📋 Retrieved Evidence & Analysis\n\n"
                f"{combined}\n\n"
                f"*(Note: Generated via direct evidence synthesis from indexed project records.)*"
            )

        # Fallback to general excerpt
        clean_context = re.sub(r"\[Section [^\]]+\]", "", context).strip()
        return (
            f"### 📋 Retrieved Tender Excerpt\n\n"
            f"{clean_context[:500]}...\n\n"
            f"*(Note: Generated via direct evidence extraction.)*"
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
