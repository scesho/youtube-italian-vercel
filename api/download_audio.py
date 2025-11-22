from http.server import BaseHTTPRequestHandler
from gtts import gTTS
import io
from datetime import datetime
import json
import os

try:
    from upstash_redis import Redis
    redis = Redis(
        url=os.environ.get('UPSTASH_REDIS_REST_URL'),
        token=os.environ.get('UPSTASH_REDIS_REST_TOKEN')
    )
    USE_REDIS = True
except:
    USE_REDIS = False

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        try:
            path_parts = self.path.split('/')
            video_id = path_parts[-1] if len(path_parts) > 0 else None
            
            if not video_id:
                return self.send_error('Missing video_id', 400)
            
            print(f"⬇️ Download audio request for: {video_id}")
            
            if not USE_REDIS:
                return self.send_error('Cache non disponibile', 503)
            
            cached = redis.get(f'text:{video_id}')
            if not cached:
                return self.send_error('Testo non disponibile. Rigenera il contenuto.', 404)
            
            data = json.loads(cached)
            italian_text = data['italian_text']
            slow = data.get('slow', False)
            
            # Limit text length
            max_length = 100000
            if len(italian_text) > max_length:
                print(f"⚠️ Testo troppo lungo ({len(italian_text)}), tronco a {max_length}")
                italian_text = italian_text[:max_length]
            
            print(f"🎵 Generazione audio: {len(italian_text)} caratteri, slow={slow}")
            
            # Generate TTS
            tts = gTTS(text=italian_text, lang='it', slow=slow)
            
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            filename = f'audio_{video_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3'
            
            print(f"✅ Audio generato: {filename}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(audio_buffer.read())
            
        except Exception as e:
            print(f"❌ Errore download audio: {str(e)}")
            return self.send_error(str(e), 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def send_error(self, message, status_code=500):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {'success': False, 'error': message}
        self.wfile.write(json.dumps(response).encode('utf-8'))
