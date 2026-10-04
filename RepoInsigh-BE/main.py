from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.ai_analysis_router import router as ai_router
from routers.analysis import router as analysis_router
from routers.graphQL_analysis_router import router as graphQL_router

app = FastAPI(
    title="Git Repo Analyzer",
    description="Analyze any public GitHub repository via the GitHub REST API.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # not for prod
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(analysis_router)
app.include_router(graphQL_router)
app.include_router(ai_router)

@app.get("/", tags=["meta"])
async def root():
    return {
        "service": "Git Repo Analyzer",
        "version": "0.1.0",
        "docs": "/docs",
        "usage": "GET /analyze/full?repo=facebook/react&token=ghp_...",
    }


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
