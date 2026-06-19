const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const http = require('http');

const BACKEND = 'http://127.0.0.1:8000';
const PORT = 3000;

let client = null;
let isReady = false;

function createClient() {
    const c = new Client({
        authStrategy: new LocalAuth({ dataPath: '.wwebjs_auth' }),
        puppeteer: {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        },
        webVersionCache: {
            type: 'remote',
            remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html'
        }
    });

    c.on('qr', (qr) => {
        console.log('Escanea el QR con WhatsApp:');
        qrcode.generate(qr, { small: true });
    });

    c.on('ready', async () => {
        isReady = true;
        console.log('WhatsApp conectado y listo');
        try {
            await axios.post(`${BACKEND}/bridge/status`, { status: 'connected' });
        } catch (e) {}
    });

    c.on('authenticated', () => {
        console.log('Autenticado correctamente');
    });

    c.on('auth_failure', (msg) => {
        console.error('Error de autenticacion:', msg);
        isReady = false;
    });

    c.on('disconnected', async (reason) => {
        console.log('WhatsApp desconectado:', reason);
        isReady = false;
        try {
            await axios.post(`${BACKEND}/bridge/status`, { status: 'disconnected' });
        } catch (e) {}
        console.log('Reconectando en 5 segundos...');
        setTimeout(() => {
            client = createClient();
            client.initialize().catch(err => console.error('Error al reconectar:', err.message));
        }, 5000);
    });

    c.on('message', async (msg) => {
        if (msg.fromMe) return;
        // Reintentar hasta 3 veces si el backend no responde
        for (let attempt = 1; attempt <= 3; attempt++) {
            try {
                const res = await axios.post(`${BACKEND}/webhook/whatsapp`, {
                    From: msg.from,
                    Body: msg.body
                }, { timeout: 10000 });
                const reply = res.data?.reply;
                if (reply && reply.trim()) {
                    await msg.reply(reply);
                }
                break;
            } catch (e) {
                if (attempt < 3) {
                    console.log(`Backend no disponible, reintentando (${attempt}/3)...`);
                    await new Promise(r => setTimeout(r, 2000 * attempt));
                } else {
                    console.error('Error enviando al backend:', e.message);
                }
            }
        }
    });

    return c;
}

// Servidor HTTP para enviar mensajes desde el backend
const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/send') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { phone, message } = JSON.parse(body);
                if (!isReady) {
                    res.writeHead(503);
                    res.end(JSON.stringify({ error: 'Cliente no listo' }));
                    return;
                }
                const chatId = phone.includes('@c.us') ? phone : `${phone.replace(/\D/g, '')}@c.us`;
                await client.sendMessage(chatId, message);
                res.writeHead(200);
                res.end(JSON.stringify({ ok: true }));
            } catch (e) {
                res.writeHead(500);
                res.end(JSON.stringify({ error: e.message }));
            }
        });
    } else {
        res.writeHead(404);
        res.end();
    }
});

server.listen(PORT, () => {
    console.log(`Bridge escuchando en puerto ${PORT}`);
});

// Iniciar cliente con manejo de error
client = createClient();
client.initialize().catch(err => {
    console.error('Error al inicializar:', err.message);
    console.log('Reintentando en 5 segundos...');
    setTimeout(() => {
        client = createClient();
        client.initialize().catch(e => console.error('Error reintento:', e.message));
    }, 5000);
});
