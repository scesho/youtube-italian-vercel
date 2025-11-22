from http.server import BaseHTTPRequestHandler
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
            
            if not USE_REDIS:
                return self.send_error('Cache non disponibile', 503)
            
            cached = redis.get(f'text:{video_id}')
            if not cached:
                return self.send_error('Testo non disponibile', 404)
            
            data = json.loads(cached)
            italian_text = data['italian_text']
            source_lang = data.get('source_lang', 'Sconosciuta')
            
            # Create TXT content
            header = f"# Sottotitoli YouTube - Video ID: {video_id}\n"
            header += f"# Lingua originale: {source_lang}\n"
            header += f"# Tradotto in: Italiano\n"
            header += f"# Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += f"# Caratteri: {len(italian_text)}\n"
            header += "#" + "="*60 + "\n\n"
            
            full_text = header + italian_text
            filename = f'sottotitoli_{video_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(full_text.encode('utf-8'))
            
        except Exception as e:
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
