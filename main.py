from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os módulos (routers)
from routers import ecopontos, avaliacoes, rotas, auth, sugestoes

app = FastAPI(
    title="Rotas Ecopontos API",
    description="API para ecopontos, rotas, avaliações e sugestões de novos ecopontos",
    version="1.0.0"
)

# 🔹 Permitir acesso do Frontend (GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Em produção, troque para o domínio do GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Rotas principais
app.include_router(ecopontos.router)
app.include_router(avaliacoes.router)
app.include_router(rotas.router)
app.include_router(auth.router)
app.include_router(sugestoes.router)

@app.get("/")
def root():
    return {
        "message": "🚀 API Rotas Ecopontos Online!",
        "docs": "/docs",
        "status": "ok"
    }
