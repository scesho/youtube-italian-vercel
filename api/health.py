from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        response = {
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'version': '4.0.0',
            'platform': 'Vercel Serverless',
            'features': {
                'translator': True,
                'docx_export': True,
                'pdf_export': True,
                'audio_tts': True
            }
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
