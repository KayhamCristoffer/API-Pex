// main.js

// ==============================
// 1. IMPORTS NO TOPO DO ARQUIVO
// ==============================
const express = require('express');
const admin = require('firebase-admin');
const dotenv = require('dotenv');
const { v4: uuidv4 } = require('uuid');

// Carrega variáveis de ambiente do arquivo .env
dotenv.config();

// ===============================================
// 2. INICIALIZAÇÃO DA APLICAÇÃO E FIREBASE
// ===============================================
const app = express();
const PORT = process.env.PORT || 8000; // Pega a porta do ambiente ou usa 8000

// Middleware para JSON (body-parser em Express)
app.use(express.json());

// Configuração de CORS (Express padrão permite todas as origens por padrão para rotas GET, mas configuramos explicitamente para todos os métodos)
const cors = require('cors');
app.use(cors()); // Permite requisições de qualquer origem ("*")

// Inicialização do Firebase a partir das variáveis de ambiente
if (!admin.apps.length) {
    try {
        const firebaseConfigStr = process.env.FIREBASE_CONFIG_JSON;
        const firebaseDbUrl = process.env.FIREBASE_DB_URL;

        if (!firebaseConfigStr || !firebaseDbUrl) {
            throw new Error("Variáveis de ambiente 'FIREBASE_CONFIG_JSON' ou 'FIREBASE_DB_URL' não encontradas.");
        }

        // Converte a string JSON em um objeto JavaScript
        const credInfo = JSON.parse(firebaseConfigStr);
        
        admin.initializeApp({
            credential: admin.credential.cert(credInfo),
            databaseURL: firebaseDbUrl
        });

        console.log("Firebase inicializado com sucesso a partir das variáveis de ambiente.");

    } catch (e) {
        if (e instanceof SyntaxError) {
            console.error("Erro: A variável de ambiente FIREBASE_CONFIG_JSON não é um JSON válido.");
        } else {
            console.error(`Erro ao inicializar o Firebase: ${e.message}`);
        }
        process.exit(1); // Encerra a aplicação se a inicialização falhar
    }
}

const db = admin.database();
const auth = admin.auth();


// ===============================================
// 3. SEGURANÇA E DEPENDÊNCIAS (Middleware de Autenticação)
// ===============================================
const get_current_user = async (req, res, next) => {
    const token = req.headers.authorization ? req.headers.authorization.split(' ')[1] : req.query.token;

    if (!token) {
        return res.status(401).send({ detail: "Token de autenticação ausente." });
    }

    try {
        const decodedToken = await auth.verifyIdToken(token);
        req.user = decodedToken; // Anexa os dados do usuário à requisição
        next(); // Continua para a próxima função (o handler da rota)
    } catch (error) {
        console.error("Erro de autenticação:", error.message);
        return res.status(401).send({ detail: "Token de autenticação inválido", "WWW-Authenticate": "Bearer" });
    }
};


// ===============================================
// 4. ROTAS DA API
// ===============================================

// Rota de Teste/Exibição do Banco Completo
app.get("/full-db", async (req, res) => {
    /*
    Retorna todo o conteúdo do banco de dados do Firebase.
    */
    try {
        const snapshot = await db.ref('/').once('value');
        const dadosCompletos = snapshot.val() || {};
        res.status(200).json(dadosCompletos);
    } catch (e) {
        res.status(500).send({ detail: `Erro ao buscar dados: ${e.message}` });
    }
});

// --- Rotas de Usuários ---

// POST /register
app.post("/register", async (req, res) => {
    /*
    Cria um novo usuário no Firebase Auth e salva dados adicionais.
    */
    const { email, senha, nome, usuario } = req.body;

    if (!email || !senha || !nome || !usuario) {
        return res.status(400).send({ detail: "Dados incompletos." });
    }

    try {
        // 1. Cria o usuário no Firebase Authentication
        const firebaseUser = await auth.createUser({
            email,
            password: senha
        });

        const uid = firebaseUser.uid;
        
        // 2. Salva os dados adicionais no Realtime Database
        await db.ref(`users/${uid}`).set({
            email,
            nome,
            usuario
        });

        // Retorna o formato UsuarioOut
        res.status(201).json({ id: uid, email, nome, usuario });

    } catch (e) {
        // Trata erro de e-mail já em uso
        if (e.code === 'auth/email-already-exists') {
            return res.status(409).send({ detail: "O e-mail já está em uso." });
        }
        res.status(500).send({ detail: `Erro ao criar usuário: ${e.message}` });
    }
});

// GET /users/me
// Usa o middleware get_current_user para autenticação
app.get("/users/me", get_current_user, async (req, res) => {
    /*
    Retorna os dados do usuário autenticado.
    */
    const uid = req.user.uid; // ID do usuário vindo do token decodificado
    
    try {
        const userSnapshot = await db.ref(`users/${uid}`).once('value');
        const userData = userSnapshot.val();

        if (!userData) {
            return res.status(404).send({ detail: "Usuário não encontrado no banco de dados." });
        }

        // Retorna o formato UsuarioOut
        res.status(200).json({
            id: uid,
            email: req.user.email, // Pega o email do token (mais confiável)
            nome: userData.nome,
            usuario: userData.usuario
        });
    } catch (e) {
        res.status(500).send({ detail: `Erro ao buscar dados do usuário: ${e.message}` });
    }
});

// --- Rotas para Ecopontos ---

// GET /ecopontos
app.get("/ecopontos", async (req, res) => {
    /*
    Lista todos os ecopontos do banco de dados.
    */
    try {
        const snapshot = await db.ref('ecopontos').once('value');
        const ecopontos = snapshot.val() || {};
        res.status(200).json(ecopontos);
    } catch (e) {
        res.status(500).send({ detail: `Erro ao buscar ecopontos: ${e.message}` });
    }
});

// GET /ecopontos/{ecoponto_id}
app.get("/ecopontos/:ecoponto_id", async (req, res) => {
    /*
    Retorna um ecoponto específico pelo seu ID.
    */
    const ecopontoId = req.params.ecoponto_id;
    try {
        const snapshot = await db.ref(`ecopontos/${ecopontoId}`).once('value');
        const ecoponto = snapshot.val();

        if (!ecoponto) {
            return res.status(404).send({ detail: "Ecoponto não encontrado." });
        }
        res.status(200).json(ecoponto);
    } catch (e) {
        res.status(500).send({ detail: `Erro ao buscar ecoponto: ${e.message}` });
    }
});

// POST /ecopontos
app.post("/ecopontos", async (req, res) => {
    /*
    Cria um novo ecoponto no banco de dados.
    */
    const ecopontoData = req.body;
    
    // Validação simples (baseada no EcopontoCreate)
    const requiredFields = ['nome', 'endereco', 'cep', 'latitude', 'longitude', 'criadoPor', 'status'];
    const missing = requiredFields.filter(f => ecopontoData[f] === undefined);
    if (missing.length > 0) {
        return res.status(400).send({ detail: `Campos obrigatórios ausentes: ${missing.join(', ')}` });
    }

    try {
        const ecopontoDict = {
            ...ecopontoData,
            criadoEm: new Date().toISOString(),
            avaliacoes: ecopontoData.avaliacoes || {} // Garante que avaliacoes existe
        };
        
        // O método 'push()' cria um ID único para o novo registro
        const novoEcopontoRef = await db.ref('ecopontos').push(ecopontoDict);
        
        res.status(201).json({ 
            message: "Ecoponto criado com sucesso.", 
            id: novoEcopontoRef.key 
        });
    } catch (e) {
        res.status(500).send({ detail: `Erro ao criar ecoponto: ${e.message}` });
    }
});

// PUT /ecopontos/{ecoponto_id}
app.put("/ecopontos/:ecoponto_id", async (req, res) => {
    /*
    Atualiza um ecoponto existente.
    */
    const ecopontoId = req.params.ecoponto_id;
    const updates = req.body;
    
    try {
        const ecopontoRef = db.ref(`ecopontos/${ecopontoId}`);
        const existente = await ecopontoRef.once('value');

        if (!existente.exists()) {
            return res.status(404).send({ detail: "Ecoponto não encontrado para atualização." });
        }
        
        // O método 'update()' atualiza apenas os campos fornecidos
        await ecopontoRef.update(updates);
        
        res.status(200).json({ message: "Ecoponto atualizado com sucesso." });
    } catch (e) {
        res.status(500).send({ detail: `Erro ao atualizar ecoponto: ${e.message}` });
    }
});

// DELETE /ecopontos/{ecoponto_id}
app.delete("/ecopontos/:ecoponto_id", async (req, res) => {
    /*
    Deleta um ecoponto específico.
    */
    const ecopontoId = req.params.ecoponto_id;

    try {
        const ecopontoRef = db.ref(`ecopontos/${ecopontoId}`);
        const existente = await ecopontoRef.once('value');
        
        if (!existente.exists()) {
            return res.status(404).send({ detail: "Ecoponto não encontrado." });
        }

        await ecopontoRef.remove();
        
        res.status(200).json({ message: "Ecoponto deletado com sucesso." });
    } catch (e) {
        res.status(500).send({ detail: `Erro ao deletar ecoponto: ${e.message}` });
    }
});

// --- Rotas para Sugestões ---

// POST /sugestoes_ecopontos
app.post("/sugestoes_ecopontos", async (req, res) => {
    /*
    Cria uma nova sugestão de ecoponto.
    */
    const sugestaoData = req.body;
    
    // Validação simples (baseada no SugestaoCreate)
    const requiredFields = ['usuarioId', 'nome', 'endereco', 'cep', 'latitude', 'longitude'];
    const missing = requiredFields.filter(f => sugestaoData[f] === undefined);
    if (missing.length > 0) {
        return res.status(400).send({ detail: `Campos obrigatórios ausentes: ${missing.join(', ')}` });
    }
    
    try {
        const sugestoesRef = db.ref('sugestoes_ecopontos');
        const sugestaoDict = {
            ...sugestaoData,
            data: new Date().toISOString(),
            status: "pendente"
        };
        
        // Usa um UUID para garantir um ID único para cada sugestão
        const id = uuidv4();
        await sugestoesRef.child(id).set(sugestaoDict);
        
        res.status(201).json(sugestaoDict); // Retorna o objeto completo com os campos gerados
    } catch (e) {
        res.status(500).send({ detail: `Erro ao criar sugestão: ${e.message}` });
    }
});


// ===============================================
// 5. INICIALIZAÇÃO DO SERVIDOR
// ===============================================

app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
    console.log(`API SustaMbiTech em Node.js/Express: http://localhost:${PORT}`);
});
