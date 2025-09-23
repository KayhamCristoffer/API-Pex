# ==============================
# 1. IMPORTS NO TOPO DO ARQUIVO
# ==============================
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # Importa o BaseModel para criar modelos de dados
import firebase_admin
from firebase_admin import credentials, db, initialize_app
from datetime import datetime
import uuid, os, json

# ===============================================
# 2. MODELOS Pydantic
# ===============================================
# Define a estrutura dos dados que a API vai receber e enviar
class EcopontoBase(BaseModel):
    nome: str
    endereco: str
    cep: str
    latitude: float
    longitude: float

class EcopontoCreate(EcopontoBase):
    criadoPor: str

class Avaliacao(BaseModel):
    usuarioId: str
    nota: int
    comentario: str

class SugestaoEcoponto(EcopontoBase):
    usuarioId: str
    
# ===============================================
# 3. INICIALIZAÇÃO DA APLICAÇÃO E FIREBASE
# ===============================================

app = FastAPI(
    title="Rotas Ecopontos API",
    description="API única para ecopontos, avaliações, rotas e sugestões",
    version="1.0.0"
)

# 🔹 CORS
# Configura o CORS para aceitar requisições de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Inicializa Firebase
if not firebase_admin._apps:
    try:
        firebase_config_str = os.getenv("FIREBASE_CONFIG_JSON")
        if not firebase_config_str:
            raise Exception("Variável de ambiente 'FIREBASE_CONFIG_JSON' não encontrada.")
        cred_info = json.loads(firebase_config_str)
        cred = credentials.Certificate(cred_info)
        initialize_app(cred, {
            "databaseURL": os.getenv("FIREBASE_DB_URL")
        })
    except json.JSONDecodeError:
        print("Erro: A variável de ambiente FIREBASE_CONFIG_JSON não é um JSON válido.")
        raise
    except Exception as e:
        print(f"Erro ao inicializar o Firebase: {e}")
        raise

# ==============================
# 4. ROTAS DA API
# ==============================
@app.get("/")
def root():
    return {"message": "🚀 API Rotas Ecopontos Online!", "docs": "/docs"}


# --- ROTAS ECOPONTOS ---
@app.get("/ecopontos")
def listar_ecopontos():
    ref = db.reference("ecopontos")
    return ref.get() or {}
    
@app.get("/ecopontos/{eco_id}")
def obter_ecoponto(eco_id: str):
    ref = db.reference(f"ecopontos/{eco_id}")
    ecoponto = ref.get()
    if not ecoponto:
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado")
    return ecoponto
    
@app.post("/ecopontos")
def criar_ecoponto(ecoponto: EcopontoCreate):
    eco_id = str(uuid.uuid4())
    ref = db.reference(f"ecopontos/{eco_id}")
    ref.set({
        "nome": ecoponto.nome,
        "endereco": ecoponto.endereco,
        "cep": ecoponto.cep,
        "latitude": ecoponto.latitude,
        "longitude": ecoponto.longitude,
        "criadoPor": ecoponto.criadoPor,
        "criadoEm": datetime.utcnow().isoformat() + "Z",
        "status": "ativo"
    })
    return {"id": eco_id, "message": "Ecoponto adicionado com sucesso"}

@app.put("/ecopontos/{eco_id}")
def atualizar_ecoponto(eco_id: str, ecoponto: EcopontoBase):
    ref = db.reference(f"ecopontos/{eco_id}")
    if not ref.get():
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado")
    
    ref.update(ecoponto.dict())
    return {"id": eco_id, "message": "Ecoponto atualizado com sucesso"}

@app.delete("/ecopontos/{eco_id}")
def deletar_ecoponto(eco_id: str):
    ref = db.reference(f"ecopontos/{eco_id}")
    if not ref.get():
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado")
    ref.delete()
    return {"id": eco_id, "message": "Ecoponto deletado com sucesso"}


# --- ROTAS AVALIAÇÕES ---
@app.post("/avaliacoes/{eco_id}")
def adicionar_avaliacao(eco_id: str, avaliacao: Avaliacao):
    ref_eco = db.reference(f"ecopontos/{eco_id}")
    if not ref_eco.get():
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado")

    av_id = str(uuid.uuid4())
    ref = db.reference(f"ecopontos/{eco_id}/avaliacoes/{av_id}")
    ref.set({
        **avaliacao.dict(),
        "data": datetime.utcnow().isoformat() + "Z"
    })
    return {"id": av_id, "message": "Avaliação adicionada com sucesso"}


# --- ROTAS SUGESTÕES DE ECOPONTOS ---
@app.post("/sugestoes")
def sugerir_ecoponto(sugestao: SugestaoEcoponto):
    sug_id = str(uuid.uuid4())
    ref = db.reference(f"sugestoes_ecopontos/{sug_id}")
    ref.set({
        **sugestao.dict(),
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
@app.get("/ecopontos/{eco_id}/avaliacoes")
def obter_avaliacoes_ecoponto(eco_id: str):
    ref = db.reference(f"ecopontos/{eco_id}/avaliacoes")
    avaliacoes = ref.get()
    if not avaliacoes:
        raise HTTPException(status_code=404, detail="Ecoponto ou avaliações não encontrados")
    return avaliacoes
@app.post("/sugestoes/rejeitar/{sug_id}")
def rejeitar_sugestao(sug_id: str):
    ref = db.reference(f"sugestoes_ecopontos/{sug_id}")
    if not ref.get():
        raise HTTPException(status_code=404, detail="Sugestão não encontrada")
    ref.update({"status": "rejeitado"})
    return {"message": "Sugestão rejeitada"}
    # Obtém os dados de um usuário pelo ID
@app.get("/users/{user_id}")
def obter_usuario(user_id: str):
    ref = db.reference(f"users/{user_id}")
    usuario = ref.get()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario
