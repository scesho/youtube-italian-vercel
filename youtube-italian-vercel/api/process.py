from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.parse
import time
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator

# In-memory cache (persiste durante l'esecuzione della function)
text_cache = {}
processing_status = {}

class handler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            youtube_url = data.get('youtube_url', '')
            mode = data.get('mode', 'both')
            slow = data.get('slow', False)
            
            print(f"📥 Processing: {youtube_url}, mode={mode}, slow={slow}")
            
            # Extract video ID
            video_id = self.get_video_id(youtube_url)
            if not video_id:
                return self.send_error_response('URL YouTube non valido', 400)
            
            print(f"🎬 Video ID: {video_id}")
            
            # Update progress
            self.update_progress(video_id, 1, 10, 'Ricerca sottotitoli...')
            
            # Get subtitles
            subtitles, source_lang, lang_name = self.get_subtitles(video_id)
            if not subtitles:
                return self.send_error_response('Nessun sottotitolo disponibile per questo video', 404)
            
            print(f"📝 Sottotitoli trovati in {lang_name}: {len(subtitles)} segmenti")
            
            # Update progress
            self.update_progress(video_id, 1, 30, f'Sottotitoli in {lang_name}')
            
            # Combine text
            full_text = ' '.join([item['text'] for item in subtitles])
            print(f"📄 Testo combinato: {len(full_text)} caratteri")
            
            # Update progress
            self.update_progress(video_id, 2, 40, 'Traduzione in italiano...')
            
            # Translate to Italian
            italian_text = self.translate_to_italian(full_text, source_lang, video_id)
            print(f"🇮🇹 Tradotto: {len(italian_text)} caratteri")
            
            # Cache text
            text_cache[video_id] = {
                'italian_text': italian_text,
                'source_lang': lang_name,
                'slow': slow,
                'timestamp': time.time()
            }
            
            # Update progress
            self.update_progress(video_id, 3, 100, '✅ Completato!')
            
            # Success response
            response = {
                'success': True,
                'message': 'Contenuto pronto',
                'video_id': video_id,
                'source_lang': lang_name,
                'text_length': len(italian_text),
                'audio_generating': mode in ['audio', 'both']
            }
            
            print(f"✅ Processo completato per {video_id}")
            
            return self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"❌ Errore: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.send_error_response(str(e), 500)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def get_video_id(self, url):
        """Extract video ID from YouTube URL"""
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Method 1: Query parameter
            if parsed.query:
                params = urllib.parse.parse_qs(parsed.query)
                if 'v' in params:
                    video_id = params['v'][0]
                    video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)
                    if len(video_id) == 11:
                        return video_id
            
            # Method 2: Pattern matching
            patterns = [
                r'(?:youtube\.com\/watch\?v=)([\w-]+)',
                r'(?:youtu\.be\/)([\w-]+)',
                r'(?:youtube\.com\/embed\/)([\w-]+)',
                r'(?:youtube\.com\/shorts\/)([\w-]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)
                    if len(video_id) == 11:
                        return video_id
            
            return None
            
        except Exception as e:
            print(f"❌ Errore estrazione video ID: {e}")
            return None
    
    def get_subtitles(self, video_id):
        """Extract subtitles from YouTube"""
        try:
            # Priority language list
            priority_languages = [
                (['it'], 'it', 'Italiano'),
                (['en'], 'en', 'Inglese'),
                (['es'], 'es', 'Spagnolo'),
                (['fr'], 'fr', 'Francese'),
                (['de'], 'de', 'Tedesco'),
                (['pt'], 'pt', 'Portoghese'),
            ]
            
            # Try each language
            for langs, lang_code, lang_name in priority_languages:
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
                    return transcript, lang_code, lang_name
                except:
                    continue
            
            # Last attempt: auto-detect
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = transcript_list.find_generated_transcript(['en', 'it', 'es', 'fr'])
                return transcript.fetch(), 'auto', 'Automatica'
            except:
                pass
            
            return None, None, 'Nessun sottotitolo disponibile'
            
        except Exception as e:
            print(f"❌ Errore get_subtitles: {e}")
            return None, None, str(e)
    
    def translate_to_italian(self, text, source_lang, video_id):
        """Translate text to Italian"""
        if source_lang == 'it':
            self.update_progress(video_id, 2, 60, 'Testo già in italiano')
            return text
        
        try:
            max_chunk = 4500
            
            if len(text) > max_chunk:
                # Split in chunks
                parts = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
                translated_parts = []
                total_parts = len(parts)
                
                for i, part in enumerate(parts):
                    try:
                        progress = 40 + int((i / total_parts) * 20)
                        self.update_progress(video_id, 2, progress, f'Traduzione parte {i+1}/{total_parts}')
                        
                        translated = GoogleTranslator(source='auto', target='it').translate(part)
                        translated_parts.append(translated)
                        
                        time.sleep(0.3)  # Rate limiting
                        
                    except Exception as e:
                        print(f"⚠️ Errore traduzione parte {i+1}: {e}")
                        translated_parts.append(part)
                
                result = ' '.join(translated_parts)
                self.update_progress(video_id, 2, 60, '✅ Traduzione completata')
                return result
            else:
                translated = GoogleTranslator(source='auto', target='it').translate(text)
                self.update_progress(video_id, 2, 60, '✅ Traduzione completata')
                return translated
                
        except Exception as e:
            print(f"❌ Errore traduzione: {e}")
            self.update_progress(video_id, 2, 60, '⚠️ Errore traduzione, uso originale')
            return text
    
    def update_progress(self, video_id, step, percentage, message):
        """Update processing status"""
        processing_status[video_id] = {
            'step': step,
            'percentage': percentage,
            'message': message,
            'timestamp': time.time()
        }
        print(f"[{video_id}] {percentage}% - {message}")
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response with CORS headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, message, status_code=500):
        """Send error response"""
        response = {
            'success': False,
            'error': message
        }
        return self.send_json_response(response, status_code)