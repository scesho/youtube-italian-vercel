from http.server import BaseHTTPRequestHandler
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
                return self.send_error_response('Missing video_id', 400)
            
            if not USE_REDIS:
                return self.send_error_response('Cache non disponibile', 503)
            
            cached = redis.get(f'text:{video_id}')
            if not cached:
                return self.send_error_response('Testo non disponibile', 404)
            
            data = json.loads(cached)
            
            response = {
                'text': data['italian_text'],
                'length': len(data['italian_text']),
                'source_lang': data.get('source_lang', 'Sconosciuta')
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
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def send_error_response(self, message, status_code=500):
        response = {'success': False, 'error': message}
        return self.send_json_response(response, status_code)
