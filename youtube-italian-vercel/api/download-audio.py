from http.server import BaseHTTPRequestHandler
from gtts import gTTS
import io
from datetime import datetime

# Shared cache
text_cache = {}

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        try:
            # Extract video_id from path: /api/download-audio/VIDEO_ID
            path_parts = self.path.split('/')
            video_id = path_parts[-1] if len(path_parts) > 0 else None
            
            if not video_id:
                return self.send_error('Missing video_id', 400)
            
            print(f"⬇️ Download audio request for: {video_id}")
            
            # Get cached text
            cached = text_cache.get(video_id)
            
            if not cached:
                return self.send_error('Testo non disponibile. Rigenera il contenuto.', 404)
            
            italian_text = cached['italian_text']
            slow = cached.get('slow', False)
            
            # Limit text length
            max_length = 100000
            if len(italian_text) > max_length:
                print(f"⚠️ Testo troppo lungo ({len(italian_text)}), tronco a {max_length}")
                italian_text = italian_text[:max_length]
            
            print(f"🎵 Generazione audio: {len(italian_text)} caratteri, slow={slow}")
            
            # Generate TTS
            tts = gTTS(text=italian_text, lang='it', slow=slow)
            
            # Save to BytesIO
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            size_kb = audio_buffer.getbuffer().nbytes / 1024
            print(f"✅ Audio generato: {size_kb:.2f} KB")
            
            # Send response
            filename = f'youtube_audio_{video_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3'
            
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(audio_buffer.read())
            
        except Exception as e:
            print(f"❌ Errore download audio: {e}")
            import traceback
            traceback.print_exc()
            return self.send_error(str(e), 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def send_error(self, message, status_code):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))