from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, initialize_app, db
from datetime import datetime
import uuid, os
####
from fastapi import FastAPI
from firebase_config import db

app = FastAPI(title="Teste FastAPI Firebase")

@app.get("/")
def root():
    return {"message": "API funcionando"}
####
@app.get("/teste")
def teste_firebase():
    ref = db.reference("/")
    return {"firebase_root": ref.get()}
    
# 🔹 Inicializa Firebase
if not len(initialize_app._apps):
    cred = credentials.Certificate("serviceAccountKey.json")
    initialize_app(cred, {
        'databaseURL': os.getenv("FIREBASE_DB_URL")
    })

app = FastAPI(
    title="Rotas Ecopontos API",
    description="API única para ecopontos, avaliações, rotas e sugestões",
    version="1.0.0"
)

# 🔹 CORS (permitir chamadas do GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Em produção, troque para seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# ROTAS BÁSICAS
# ==============================
@app.get("/")
def root():
    return {"message": "🚀 API Rotas Ecopontos Online!", "docs": "/docs"}


# ==============================
# ECOPONTOS
# ==============================
@app.get("/ecopontos")
def listar_ecopontos():
    ref = db.reference("ecopontos")
    return ref.get() or {}

@app.post("/ecopontos")
def criar_ecoponto(nome: str, endereco: str, cep: str, latitude: float, longitude: float, criadoPor: str):
    eco_id = str(uuid.uuid4())
    ref = db.reference(f"ecopontos/{eco_id}")
    ref.set({
        "nome": nome,
        "endereco": endereco,
        "cep": cep,
        "latitude": latitude,
        "longitude": longitude,
        "criadoPor": criadoPor,
        "criadoEm": datetime.utcnow().isoformat() + "Z",
        "status": "ativo"
    })
    return {"id": eco_id, "message": "Ecoponto adicionado com sucesso"}


# ==============================
# AVALIAÇÕES
# ==============================
@app.post("/avaliacoes/{eco_id}")
def adicionar_avaliacao(eco_id: str, usuarioId: str, nota: int, comentario: str):
    ref_eco = db.reference(f"ecopontos/{eco_id}")
    if not ref_eco.get():
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado")

    av_id = str(uuid.uuid4())
    ref = db.reference(f"ecopontos/{eco_id}/avaliacoes/{av_id}")
    ref.set({
        "usuarioId": usuarioId,
        "nota": nota,
        "comentario": comentario,
        "data": datetime.utcnow().isoformat() + "Z"
    })
    return {"id": av_id, "message": "Avaliação adicionada com sucesso"}


# ==============================
# SUGESTÕES DE ECOPONTOS (FORM USUÁRIOS)
# ==============================
@app.post("/sugestoes")
def sugerir_ecoponto(usuarioId: str, nome: str, endereco: str, cep: str,
                     latitude: float, longitude: float):
    sug_id = str(uuid.uuid4())
    ref = db.reference(f"sugestoes_ecopontos/{sug_id}")
    ref.set({
        "usuarioId": usuarioId,
        "nome": nome,
        "endereco": endereco,
        "cep": cep,
        "latitude": latitude,
        "longitude": longitude,
        "data": datetime.utcnow().isoformat() + "Z",
        "status": "pendente"
    })
    return {"id": sug_id, "message": "Sugestão enviada para análise"}

@app.get("/sugestoes")
def listar_sugestoes():
    ref = db.reference("sugestoes_ecopontos")
    return ref.get() or {}

@app.post("/sugestoes/aprovar/{sug_id}")
def aprovar_sugestao(sug_id: str):
    ref = db.reference(f"sugestoes_ecopontos/{sug_id}")
    sugestao = ref.get()
    if not sugestao:
        raise HTTPException(status_code=404, detail="Sugestão não encontrada")

    eco_id = str(uuid.uuid4())
    eco_ref = db.reference(f"ecopontos/{eco_id}")
    eco_ref.set({
        "nome": sugestao["nome"],
        "endereco": sugestao["endereco"],
        "cep": sugestao["cep"],
        "latitude": sugestao["latitude"],
        "longitude": sugestao["longitude"],
        "criadoPor": sugestao["usuarioId"],
        "criadoEm": datetime.utcnow().isoformat() + "Z",
        "status": "ativo"
    })
    ref.update({"status": "aprovado"})
    return {"message": "Ecoponto aprovado e movido para ecopontos", "eco_id": eco_id}

@app.post("/sugestoes/rejeitar/{sug_id}")
def rejeitar_sugestao(sug_id: str):
    ref = db.reference(f"sugestoes_ecopontos/{sug_id}")
    if not ref.get():
        raise HTTPException(status_code=404, detail="Sugestão não encontrada")
    ref.update({"status": "rejeitado"})
    return {"message": "Sugestão rejeitada"}

