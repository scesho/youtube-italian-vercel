from http.server import BaseHTTPRequestHandler
from fpdf import FPDF
import io
from datetime import datetime
import re

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
            
            # Clean text (remove problematic characters)
            clean_text = italian_text.encode('latin-1', 'replace').decode('latin-1')
            
            # Split in paragraphs
            sentences = re.split(r'(?<=[.!?])\s+', clean_text)
            paragraphs = []
            current = ""
            
            for sentence in sentences:
                if len(current) + len(sentence) > 600:
                    if current:
                        paragraphs.append(current.strip())
                    current = sentence
                else:
                    current += " " + sentence if current else sentence
            
            if current:
                paragraphs.append(current.strip())
            
            for para in paragraphs:
                pdf.multi_cell(0, 6, para, 0, 'J')
                pdf.ln(3)
            
            # Save to BytesIO
            pdf_buffer = io.BytesIO()
            pdf_output = pdf.output()
            pdf_buffer.write(pdf_output)
            pdf_buffer.seek(0)
            
            filename = f'sottotitoli_{video_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(pdf_buffer.read())
            
        except Exception as e:
            print(f"❌ Errore PDF: {e}")
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
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))