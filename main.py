# ==============================
# 1. IMPORTS NO TOPO DO ARQUIVO
# ==============================
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import firebase_admin
from firebase_admin import credentials, db, auth, initialize_app
import os, json

# ===============================================
# 2. INICIALIZAÇÃO DA APLICAÇÃO E FIREBASE
# ===============================================
app = FastAPI(
    title="API de Usuários com Firebase",
    version="1.0.0"
)

# Configuração de CORS para permitir requisições de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialização do Firebase a partir das variáveis de ambiente
if not firebase_admin._apps:
    try:
        firebase_config_str = os.getenv("FIREBASE_CONFIG_JSON")
        firebase_db_url = os.getenv("FIREBASE_DB_URL")
        if not firebase_config_str or not firebase_db_url:
            raise Exception("Variáveis de ambiente 'FIREBASE_CONFIG_JSON' ou 'FIREBASE_DB_URL' não encontradas.")
        
        cred_info = json.loads(firebase_config_str)
        cred = credentials.Certificate(cred_info)
        initialize_app(cred, {
            "databaseURL": firebase_db_url
        })
    except json.JSONDecodeError:
        print("Erro: A variável de ambiente FIREBASE_CONFIG_JSON não é um JSON válido.")
        raise
    except Exception as e:
        print(f"Erro ao inicializar o Firebase: {e}")
        raise

# ===============================================
# 3. SCHEMAS PYDANTIC
# ===============================================
class UsuarioCreate(BaseModel):
    email: EmailStr
    senha: str
    nome: str
    usuario: str

class UsuarioOut(BaseModel):
    id: str
    email: str
    nome: str
    usuario: str

class TokenData(BaseModel):
    uid: str

# ===============================================
# 4. SEGURANÇA E DEPENDÊNCIAS
# ===============================================
async def get_current_user(token: str) -> dict:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autenticação inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Verifica e decodifica o token de ID do Firebase
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        return decoded_token
    except auth.AuthError:
        # Erro de autenticação do Firebase (token expirado, inválido, etc.)
        raise credentials_exc
    except Exception:
        # Outros erros
        raise credentials_exc

# ===============================================
# 5. ROTAS DA API
# ===============================================

@app.get("/full-db")
def mostrar_banco_completo():
    """
    Retorna todo o conteúdo do banco de dados do Firebase.
    """
    ref = db.reference()
    dados_completos = ref.get() or {}
    return dados_completos

@app.post("/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def criar_usuario(user_data: UsuarioCreate):
    """
    Cria um novo usuário com email e senha no Firebase Auth
    e salva dados adicionais no Firebase Realtime Database.
    """
    try:
        # 1. Cria o usuário no Firebase Authentication
        firebase_user = auth.create_user(
            email=user_data.email,
            password=user_data.senha
        )
        
        # 2. Salva informações adicionais no Realtime Database
        db_ref = db.reference(f'users/{firebase_user.uid}')
        db_ref.set({
            "email": user_data.email,
            "nome": user_data.nome,
            "usuario": user_data.usuario
        })

        return UsuarioOut(
            id=firebase_user.uid,
            email=user_data.email,
            nome=user_data.nome,
            usuario=user_data.usuario
        )
    except firebase_admin.auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O e-mail já está em uso."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {e}"
        )

@app.get("/users/me", response_model=UsuarioOut)
def ler_usuario_atual(token: str, current_user: dict = Depends(get_current_user)):
    """
    Retorna os dados do usuário autenticado.
    
    Esta rota é protegida. O cliente deve enviar o token de ID
    do Firebase no cabeçalho Authorization como 'Bearer <token>'.
    """
    # Recupera os dados do banco de dados
    db_ref = db.reference(f'users/{current_user["uid"]}')
    user_data = db_ref.get()
    
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    return UsuarioOut(
        id=current_user["uid"],
        email=current_user.get("email"),
        nome=user_data.get("nome"),
        usuario=user_data.get("usuario")
    )
