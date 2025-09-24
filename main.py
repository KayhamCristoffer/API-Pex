# main.py
from fastapi import FastAPI
from pydantic import BaseModel
import os
import json
import firebase_admin
from firebase_admin import credentials, db

# Inicializa o app FastAPI
app = FastAPI()

# Modelos Pydantic para validação dos dados de entrada
class User(BaseModel):
    email: str
    nome: str
    sobrenome: str
    newsletterOptIn: bool = False
    nivel: str = "comum"
    
class Ecoponto(BaseModel):
    nome: str
    endereco: str
    cep: str
    latitude: float
    longitude: float
    criadoPor: str
    status: str = "ativo"

class SugestaoEcoponto(BaseModel):
    usuarioId: str
    nome: str
    endereco: str
    cep: str
    latitude: float
    longitude: float
    status: str = "pendente"

# Configuração e inicialização do Firebase
firebase_creds_json_string = os.environ.get('FIREBASE_CREDENTIALS')
firebase_db_url = os.environ.get('FIREBASE_DATABASE_URL')

# Referências globais para o banco de dados
users_ref = None
ecopontos_ref = None
sugestoes_ref = None

if firebase_creds_json_string and firebase_db_url:
    cred_dict = json.loads(firebase_creds_json_string)
    cred = credentials.Certificate(cred_dict)

    firebase_admin.initialize_app(cred, {
        'databaseURL': firebase_db_url
    })

    # Define as referências para as coleções principais
    users_ref = db.reference('users')
    ecopontos_ref = db.reference('ecopontos')
    sugestoes_ref = db.reference('sugestoes_ecopontos')

# Rota de teste
@app.get("/")
def read_root():
    return {"message": "API está funcionando!"}

# Rotas para interagir com 'users'
@app.get("/users/{user_id}")
def get_user(user_id: str):
    if users_ref is None:
        return {"error": "Firebase não inicializado."}
    user_data = users_ref.child(user_id).get()
    if user_data:
        return {"user": user_data}
    return {"error": "Usuário não encontrado."}

@app.post("/users/")
def create_user(user: User):
    if users_ref is None:
        return {"error": "Firebase não inicializado."}
    new_user_ref = users_ref.push(user.dict())
    return {"message": "Usuário criado com sucesso!", "id": new_user_ref.key}

# Rotas para interagir com 'ecopontos'
@app.get("/ecopontos/")
def get_all_ecopontos():
    if ecopontos_ref is None:
        return {"error": "Firebase não inicializado."}
    ecopontos_data = ecopontos_ref.get()
    return {"ecopontos": ecopontos_data}

@app.post("/ecopontos/")
def add_ecoponto(ecoponto: Ecoponto):
    if ecopontos_ref is None:
        return {"error": "Firebase não inicializado."}
    new_ecoponto_ref = ecopontos_ref.push(ecoponto.dict())
    return {"message": "Ecoponto adicionado com sucesso!", "id": new_ecoponto_ref.key}

# Rotas para interagir com 'sugestoes_ecopontos'
@app.post("/sugestoes/")
def add_sugestao(sugestao: SugestaoEcoponto):
    if sugestoes_ref is None:
        return {"error": "Firebase não inicializado."}
    new_sugestao_ref = sugestoes_ref.push(sugestao.dict())
    return {"message": "Sugestão de ecoponto adicionada com sucesso!", "id": new_sugestao_ref.key}

@app.get("/sugestoes/")
def get_all_sugestoes():
    if sugestoes_ref is None:
        return {"error": "Firebase não inicializado."}
    sugestoes_data = sugestoes_ref.get()
    return {"sugestoes": sugestoes_data}
