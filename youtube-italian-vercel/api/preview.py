from http.server import BaseHTTPRequestHandler
import json

# Shared cache
text_cache = {}

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        try:
            # Extract video_id from path
            path_parts = self.path.split('/')
            video_id = path_parts[-1] if len(path_parts) > 0 else None
            
            if not video_id:
                return self.send_error_response('Missing video_id', 400)
            
            # Get cached text
            cached = text_cache.get(video_id)
            
            if not cached:
                return self.send_error_response('Testo non disponibile', 404)
            
            response = {
                'text': cached['italian_text'],
                'length': len(cached['italian_text']),
                'source_lang': cached.get('source_lang', 'Sconosciuta')
            }
            
            return self.send_json_response(response, 200)
            
        except Exception as e:
            return self.send_error_response(str(e), 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, message, status_code=500):
        return self.send_json_response({'error': message}, status_code)