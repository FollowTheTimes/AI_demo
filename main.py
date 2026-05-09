import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import setup_logging
from engines.intent_parser import IntentParser
from engines.rag_retriever import RAGRetriever
from engines.cube_builder import CubeBuilder
from engines.data_cleaner import DataCleaner
from engines.schema_registry import SchemaRegistry
from engines.llm_gateway import LLMGateway
from integrations.datacube_importer import DataCubeImporter
import config

setup_logging()

app = FastAPI(title="AI智能建模引擎", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

intent_parser = IntentParser()
rag_retriever = RAGRetriever()
cube_builder = CubeBuilder()
data_cleaner = DataCleaner()
schema_registry = SchemaRegistry()
importer = DataCubeImporter()
llm_gateway = LLMGateway({
    "api_type": config.LLM_API_TYPE,
    "api_url": config.LLM_API_URL,
    "model_name": config.LLM_MODEL_NAME,
    "timeout": config.LLM_TIMEOUT,
    "max_tokens": config.LLM_MAX_TOKENS,
})

rag_retriever.load_templates()
rag_retriever.build_index()
schema_registry.load()


class GenerateRequest(BaseModel):
    description: str
    auto_import: bool = False


class CleanRequest(BaseModel):
    data: list
    rules: list[str] = []


class ImportRequest(BaseModel):
    file_path: str


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    intent = await intent_parser.parse(req.description)

    search_results = rag_retriever.search(intent, top_k=1)
    if not search_results:
        return {
            "success": False,
            "message": "未找到匹配的模板",
            "model_type": intent.get("model_type", ""),
        }

    best_match = search_results[0]
    template = best_match["template"]

    cube_content = cube_builder.build(intent, template)
    file_path = cube_builder.save(cube_content)

    import_result = None
    if req.auto_import:
        import_result = await importer.import_cube(
            cube_content, file_name=os.path.basename(file_path)
        )

    return {
        "success": True,
        "model_type": intent.get("model_type", ""),
        "confidence": intent.get("confidence", 0),
        "match_type": best_match.get("match_type", ""),
        "match_score": best_match.get("score", 0),
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "cube_content": cube_content,
        "import_result": import_result,
    }


@app.post("/api/clean")
async def clean(req: CleanRequest):
    original_count = len(req.data)
    cleaned = data_cleaner.clean(req.data)
    report = data_cleaner.generate_clean_report(req.data, cleaned)
    return {
        "success": True,
        "cleaned_count": len(cleaned),
        "original_count": original_count,
        "report": report,
    }


@app.post("/api/import")
async def import_cube(req: ImportRequest):
    result = await importer.import_from_path(req.file_path)
    return {
        "success": result.get("success", False),
        "import_result": result,
    }


@app.get("/api/templates")
async def get_templates():
    templates = []
    for t in rag_retriever.templates:
        templates.append({
            "name": t.get("name", ""),
            "title": t.get("title", ""),
            "bz": t.get("bz", ""),
        })
    return {"templates": templates}


@app.get("/api/schemas")
async def get_schemas():
    tables = schema_registry.get_all_tables()
    result = []
    for t in tables:
        fields = schema_registry.get_table_fields(t["name"])
        result.append({
            "name": t["name"],
            "label": t["label"],
            "description": t["description"],
            "fields": fields,
        })
    return {"tables": result}


@app.get("/api/health")
async def health():
    llm_available = await llm_gateway.check_available()
    return {
        "status": "ok",
        "templates_loaded": len(rag_retriever.templates),
        "schemas_loaded": schema_registry.table_count,
        "llm_available": llm_available,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
