# YouTube to Italian Translator

Converti video YouTube in sottotitoli e audio italiani. Supporta 12+ lingue.

## Features

- ✅ Estrazione sottotitoli YouTube
- 🇮🇹 Traduzione automatica in italiano
- 📄 Export TXT, PDF, DOCX, MP3
- 🌙 Tema scuro/chiaro
- 📱 PWA installabile
- ⚡ Serverless (Vercel)

## Deployment

1. Installa Vercel CLI: `npm i -g vercel`
2. Collega Upstash Redis: https://vercel.com/integrations/upstash
3. Deploy: `vercel --prod`

## Environment Variables

Richieste da Upstash integration:
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

## Local Development

