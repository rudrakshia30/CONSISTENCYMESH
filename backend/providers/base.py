"""LLM provider abstraction layer.

All AI interactions go through this interface. Business logic depends
only on LLMProvider, never on a specific provider implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models.schemas import Clause, RawAnswer, RawJudgment


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    Every AI operation is defined here. Implementations must be fully
    async and handle their own timeout/retry logic.
    """

    @abstractmethod
    async def analyze_consistency(
        self, clause_a: Clause, clause_b: Clause, context: dict[str, str]
    ) -> RawJudgment:
        """Analyze the relationship between two clauses.
        
        Args:
            clause_a: First clause for comparison.
            clause_b: Second clause for comparison.
            context: Additional context (document filenames, metadata).
            
        Returns:
            Raw judgment from the LLM, pending validation.
        """
        ...

    @abstractmethod
    async def classify_candidate(
        self, clause_a: Clause, clause_b: Clause
    ) -> bool:
        """Quick pre-check whether a clause pair warrants full analysis.
        
        Args:
            clause_a: First clause.
            clause_b: Second clause.
            
        Returns:
            True if the pair should proceed to full analysis.
        """
        ...

    @abstractmethod
    async def answer_question(
        self, question: str, clauses: list[Clause]
    ) -> RawAnswer:
        """Answer a follow-up question grounded in specific clauses.
        
        Args:
            question: The user's question.
            clauses: Relevant clauses to ground the answer.
            
        Returns:
            Raw answer from the LLM, pending validation.
        """
        ...
