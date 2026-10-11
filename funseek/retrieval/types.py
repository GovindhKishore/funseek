from dataclasses import dataclass
from funseek.parsing.parser import FunctionInfo

@dataclass
class ScoredFunction:
    function: FunctionInfo
    score: float | None
    rank: int
    retriever: str
    explanation: str | None = None