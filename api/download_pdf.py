from http.server import BaseHTTPRequestHandler
from fpdf import FPDF
import io
from datetime import datetime
import json
import re
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
            
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Title
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Sottotitoli YouTube', 0, 1, 'C')
            
            # Metadata
            pdf.set_font('Arial', '', 10)
            pdf.ln(5)
            pdf.cell(0, 6, f'Video ID: {video_id}', 0, 1)
            pdf.cell(0, 6, f'Lingua: {source_lang} -> Italiano', 0, 1)
            pdf.cell(0, 6, f'Data: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1)
            pdf.ln(10)
            
            # Content
            pdf.set_font('Arial', '', 10)
            
            # Clean text
            clean_text = re.sub(r'[^\x00-\x7F]+', lambda m: m.group(0).encode('latin-1', 'ignore').decode('latin-1'), italian_text)
            
            # Split into paragraphs
            paragraphs = clean_text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    pdf.multi_cell(0, 6, para.strip(), 0, 'J')
                    pdf.ln(3)
            
            # Generate PDF
            pdf_output = pdf.output(dest='S').encode('latin-1')
            filename = f'sottotitoli_{video_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(pdf_output)
            
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
