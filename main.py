# ==============================
# 1. IMPORTS NO TOPO DO ARQUIVO
# ==============================
from typing import Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import firebase_admin
from firebase_admin import credentials, db, auth, initialize_app
from datetime import datetime
import os, json, uuid

# ===============================================
# 2. INICIALIZAÇÃO DA APLICAÇÃO E FIREBASE
# ===============================================
app = FastAPI(
    title="API Sustentabilidade - SustaMbiTech",
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
        
        # Converte a string JSON da variável de ambiente em um dicionário Python
        cred_info = json.loads(firebase_config_str)
        cred = credentials.Certificate(cred_info)
        initialize_app(cred, {
            "databaseURL": firebase_db_url
        })
        
        print("Firebase inicializado com sucesso a partir das variáveis de ambiente.")

    except json.JSONDecodeError:
        print("Erro: A variável de ambiente FIREBASE_CONFIG_JSON não é um JSON válido.")
        raise
    except Exception as e:
        print(f"Erro ao inicializar o Firebase: {e}")
        raise

# ===============================================
# 3. SCHEMAS PYDANTIC
# ===============================================

# Schemas para a rota de usuários
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

# Schemas para a rota de ecopontos
class Avaliacao(BaseModel):
    usuarioId: str
    nota: int
    comentario: str
    data: str = ""

class EcopontoCreate(BaseModel):
    nome: str
    endereco: str
    cep: str
    latitude: float
    longitude: float
    criadoPor: str
    status: str
    avaliacoes: Optional[Dict[str, Avaliacao]] = {}

class EcopontoUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    cep: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None

# Schema para a rota de sugestões
class SugestaoCreate(BaseModel):
    usuarioId: str
    nome: str
    endereco: str
    cep: str
    latitude: float
    longitude: float

class SugestaoOut(BaseModel):
    usuarioId: str
    nome: str
    endereco: str
    cep: str
    latitude: float
    longitude: float
    data: str
    status: str

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
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        return decoded_token
    except auth.AuthError:
        raise credentials_exc
    except Exception:
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

# Rotas de Usuários (mantidas do código anterior)
@app.post("/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def criar_usuario(user_data: UsuarioCreate):
    """
    Cria um novo usuário no Firebase Auth e salva dados adicionais.
    """
    try:
        firebase_user = auth.create_user(
            email=user_data.email,
            password=user_data.senha
        )
        db_ref = db.reference(f'users/{firebase_user.uid}')
        db_ref.set({
            "email": user_data.email,
            "nome": user_data.nome,
            "usuario": user_data.usuario
        })
        return UsuarioOut(id=firebase_user.uid, email=user_data.email, nome=user_data.nome, usuario=user_data.usuario)
    except firebase_admin.auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O e-mail já está em uso.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar usuário: {e}")

@app.get("/users/me", response_model=UsuarioOut)
def ler_usuario_atual(token: str, current_user: dict = Depends(get_current_user)):
    """
    Retorna os dados do usuário autenticado.
    """
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

# Rotas para Ecopontos
@app.get("/ecopontos")
def listar_ecopontos():
    """
    Lista todos os ecopontos do banco de dados.
    """
    ecopontos_ref = db.reference('ecopontos')
    ecopontos = ecopontos_ref.get() or {}
    return ecopontos

@app.get("/ecopontos/{ecoponto_id}")
def obter_ecoponto(ecoponto_id: str):
    """
    Retorna um ecoponto específico pelo seu ID.
    """
    ecoponto_ref = db.reference(f'ecopontos/{ecoponto_id}')
    ecoponto = ecoponto_ref.get()
    if not ecoponto:
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado.")
    return ecoponto

@app.post("/ecopontos", status_code=status.HTTP_201_CREATED)
def criar_ecoponto(ecoponto_data: EcopontoCreate):
    """
    Cria um novo ecoponto no banco de dados.
    """
    ecopontos_ref = db.reference('ecopontos')
    
    # Adiciona a data de criação e gera um ID único
    ecoponto_dict = ecoponto_data.dict()
    ecoponto_dict["criadoEm"] = datetime.utcnow().isoformat() + "Z"
    
    # O método 'push()' cria um ID único para o novo registro
    novo_ecoponto_ref = ecopontos_ref.push(ecoponto_dict)
    return {"message": "Ecoponto criado com sucesso.", "id": novo_ecoponto_ref.key}

@app.put("/ecopontos/{ecoponto_id}")
def atualizar_ecoponto(ecoponto_id: str, ecoponto_data: EcopontoUpdate):
    """
    Atualiza um ecoponto existente.
    """
    ecoponto_ref = db.reference(f'ecopontos/{ecoponto_id}')
    existente = ecoponto_ref.get()
    if not existente:
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado para atualização.")
    
    # O método 'update()' atualiza apenas os campos fornecidos
    ecoponto_ref.update(ecoponto_data.dict(exclude_unset=True))
    return {"message": "Ecoponto atualizado com sucesso."}

@app.delete("/ecopontos/{ecoponto_id}")
def deletar_ecoponto(ecoponto_id: str):
    """
    Deleta um ecoponto específico.
    """
    ecoponto_ref = db.reference(f'ecopontos/{ecoponto_id}')
    if not ecoponto_ref.get():
        raise HTTPException(status_code=404, detail="Ecoponto não encontrado.")
    ecoponto_ref.delete()
    return {"message": "Ecoponto deletado com sucesso."}

# Rotas para Sugestões
@app.post("/sugestoes_ecopontos", response_model=SugestaoOut, status_code=status.HTTP_201_CREATED)
def criar_sugestao(sugestao_data: SugestaoCreate):
    """
    Cria uma nova sugestão de ecoponto.
    """
    sugestoes_ref = db.reference('sugestoes_ecopontos')
    sugestao_dict = sugestao_data.dict()
    sugestao_dict.update({
        "data": datetime.utcnow().isoformat() + "Z",
        "status": "pendente"
    })
    
    # Usa um UUID para garantir um ID único para cada sugestão
    sugestoes_ref.child(str(uuid.uuid4())).set(sugestao_dict)
    
    return SugestaoOut(**sugestao_dict)
