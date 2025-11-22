from http.server import BaseHTTPRequestHandler
import json
import re
import time
import os
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator

# Upstash Redis per cache condivisa
try:
    from upstash_redis import Redis
    redis = Redis(
        url=os.environ.get('UPSTASH_REDIS_REST_URL'),
        token=os.environ.get('UPSTASH_REDIS_REST_TOKEN')
    )
    USE_REDIS = True
except:
    USE_REDIS = False
    print("⚠️ Redis non disponibile")

class handler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            youtube_url = data.get('youtube_url', '')
            mode = data.get('mode', 'both')
            slow = data.get('slow', False)
            
            print(f"📥 Processing: {youtube_url}")
            
            video_id = self.get_video_id(youtube_url)
            if not video_id:
                return self.send_error_response('URL YouTube non valido', 400)
            
            self.update_progress(video_id, 1, 10, 'Ricerca sottotitoli...')
            
            subtitles, source_lang = self.get_subtitles(video_id)
            if not subtitles:
                return self.send_error_response('Sottotitoli non disponibili', 404)
            
            print(f"✅ Sottotitoli: {source_lang} ({len(subtitles)} char)")
            
            self.update_progress(video_id, 2, 30, f'Traduzione da {source_lang}...')
            
            italian_text = self.translate_text(subtitles, video_id)
            
            print(f"✅ Traduzione: {len(italian_text)} char")
            
            self.update_progress(video_id, 3, 90, 'Preparazione download...')
            
            cache_data = {
                'italian_text': italian_text,
                'source_lang': source_lang,
                'slow': slow,
                'timestamp': time.time()
            }
            
            if USE_REDIS:
                redis.set(f'text:{video_id}', json.dumps(cache_data), ex=3600)
                redis.set(f'status:{video_id}', json.dumps({
                    'step': 4,
                    'percentage': 100,
                    'message': 'Completato!',
                    'timestamp': time.time()
                }), ex=3600)
            
            self.update_progress(video_id, 4, 100, 'Completato!')
            
            response = {
                'success': True,
                'video_id': video_id,
                'source_lang': source_lang,
                'text_length': len(italian_text),
                'preview': italian_text[:500] + '...' if len(italian_text) > 500 else italian_text
            }
            
            return self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"❌ Errore: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.send_error_response(str(e), 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def get_video_id(self, url):
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_subtitles(self, video_id):
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'es', 'fr', 'de', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi', 'it'])
                source_lang = transcript.language_code
            except:
                transcript = transcript_list.find_transcript(['en', 'es', 'fr', 'de', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi', 'it'])
                source_lang = transcript.language_code
            
            subtitle_data = transcript.fetch()
            full_text = ' '.join([entry['text'] for entry in subtitle_data])
            return full_text, source_lang
        except Exception as e:
            print(f"❌ Errore sottotitoli: {str(e)}")
            return None, None
    
    def translate_text(self, text, video_id):
        MAX_LENGTH = 50000
        if len(text) > MAX_LENGTH:
            text = text[:MAX_LENGTH]
        
        CHUNK_SIZE = 4500
        chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
        
        translated_chunks = []
        translator = GoogleTranslator(source='auto', target='it')
        
        for i, chunk in enumerate(chunks):
            try:
                progress = 30 + (i / len(chunks)) * 60
                self.update_progress(video_id, 2, int(progress), f'Traduzione {i+1}/{len(chunks)}...')
                
                translated = translator.translate(chunk)
                translated_chunks.append(translated)
                time.sleep(0.3)
            except Exception as e:
                print(f"⚠️ Errore chunk {i}: {str(e)}")
                translated_chunks.append(chunk)
        
        return ' '.join(translated_chunks)
    
    def update_progress(self, video_id, step, percentage, message):
        status = {
            'step': step,
            'percentage': percentage,
            'message': message,
            'timestamp': time.time()
        }
        if USE_REDIS:
            try:
                redis.set(f'status:{video_id}', json.dumps(status), ex=3600)
            except:
                pass
    
    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def send_error_response(self, message, status_code=500):
        response = {'success': False, 'error': message}
        return self.send_json_response(response, status_code)
