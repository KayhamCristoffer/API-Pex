# ==============================
# 1. IMPORTS NO TOPO DO ARQUIVO
# ==============================
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, db, initialize_app
from datetime import datetime
import uuid, os, json

# ===============================================
# 2. INICIALIZAÇÃO DA APLICAÇÃO E FIREBASE
# ===============================================

app = FastAPI(
    title="API de Teste de Conexão com o Banco de Dados",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# 3. ROTA DE TESTE
# ==============================
@app.get("/test-db")
def test_database_connection():
    try:
        # Tenta ler um nó do banco de dados para confirmar a conexão
        ref = db.reference("ecopontos")
        data = ref.get()
        return {"status": "ok", "message": "Conexão com o banco de dados bem-sucedida!", "data": data}
    except Exception as e:
        # Se algo falhar, retorna um erro 500 com a mensagem de erro detalhada
        raise HTTPException(status_code=500, detail=f"Erro na conexão com o banco de dados: {e}")

@app.get("/full-db")
def mostrar_banco_completo():
    """
    Retorna todo o conteúdo do banco de dados do Firebase.
    """
    ref = db.reference()
    dados_completos = ref.get() or {}
    return dados_completos
