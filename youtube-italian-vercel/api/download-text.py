from http.server import BaseHTTPRequestHandler
from datetime import datetime

text_cache = {}

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        try:
            path_parts = self.path.split('/')
            video_id = path_parts[-1] if len(path_parts) > 0 else None
            
            if not video_id:
                return self.send_error('Missing video_id', 400)
            
            cached = text_cache.get(video_id)
            
            if not cached:
                return self.send_error('Testo non disponibile', 404)
            
            italian_text = cached['italian_text']
            source_lang = cached.get('source_lang', 'Sconosciuta')
            
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
    
    def send_error(self, message, status_code):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))