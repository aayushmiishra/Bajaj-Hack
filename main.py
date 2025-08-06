from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List
from legal_docs.indexing import index_to_qdrant
from legal_docs.retrieval import QdrantRetrievalEngine
from langchain_openai import OpenAIEmbeddings
from insight_generator import CaseInsightGenerator
from legal_docs.models import RetrievalResult
import uvicorn

app = FastAPI()

# Define input schema
class QueryRequest(BaseModel):
    documents: str  # URL of the document
    questions: List[str]

# Define output schema
class QueryResponse(BaseModel):
    answers: List[str]

@app.post("/hackrx/run", response_model=QueryResponse)
async def run_document_query(req: QueryRequest):
    try:
        # Step 1: Index the document
        print(f"Indexing document: {req.documents}")
        indexed_docs = index_to_qdrant(req.documents)
        print(f"Indexed {len(indexed_docs)} chunks")

        # Step 2: Initialize Retrieval Engine
        embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
        retrieval_engine = QdrantRetrievalEngine(embedding_model)

        # Step 3: Initialize Insight Generator
        insight_generator = CaseInsightGenerator(model_name="gpt-3.5-turbo")

        # Step 4: Answer each question using the insight generator
        answers = []
        for question in req.questions:
            retrieved_cases = retrieval_engine.retrieve_cases(
                query=question,
                k=5,
                source_filter=req.documents
            )

            insight = insight_generator.generate(
                query=question,
                retrieved_cases=retrieved_cases,
                insight_type="analysis"
            )

            answers.append(insight.content)

        return {"answers": answers}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the app if this is the main file
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

