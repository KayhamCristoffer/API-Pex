import firebase_admin
from firebase_admin import credentials, db
import os

# Caminho para o arquivo da chave privada
# (coloque o arquivo no mesmo diretório do main.py)
SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(__file__), 
    "bd-sustambitech-firebase-adminsdk-fbsvc-4dcbb3939e.json"
)

# Inicializa o Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://bd-sustambitech-default-rtdb.firebaseio.com"
    })

# Agora você pode usar firebase_admin em toda a API
