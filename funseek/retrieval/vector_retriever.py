from dataclasses import dataclass
from pathlib import Path

from funseek.parsing.parser import FunctionInfo
from funseek.retrieval.types import ScoredFunction


@dataclass
class VectorRetriever:
    index: "VectorIndex"

    def search(self, query: str, top_k: int = 20, similarity_threshold: float = 0.3) -> list[ScoredFunction]:
        query_embedding = self.index.model.encode([query]).tolist()

        results = self.index.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
        )

        ids = results["ids"][0]
        if not ids:
            raise RuntimeError(
                "Vector index returned no results. It may be empty or damaged; run 'funseek reindex'."
            )
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]


        scored_functions = []
        MIN_KEEP = 3

        for rank, (dist, doc_id, meta) in enumerate(zip(distances, ids, metadatas), start=1):
            similarity = 1 - dist
            if rank > MIN_KEEP and similarity < similarity_threshold:
                continue

            function = FunctionInfo(
                name=meta["name"],
                file=Path(meta["file"]),
                line=meta["line"],
                doc_string=meta["doc_string"],
                class_name=meta["class_name"] if meta["class_name"] else None,
                params=[],
                return_type=None,
                callees=[],
                callers=[],
            )

            scored_functions.append(ScoredFunction(
                function=function,
                score=similarity,
                rank=rank,
                retriever="vector",
            ))

        return scored_functions

