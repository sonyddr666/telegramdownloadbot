## ytdlp-telegram-bot (Docker)

### Subir
1) Copie `.env.example` para `.env` e preencha BOT_TOKEN
2) Rode:
   docker compose up -d --build

### Uso no Telegram
- Envie um link (URL)
- O bot analisa e mostra botões com formatos
- Clique em um formato para baixar e receber o arquivo
- /links lista histórico
- /cancel tenta abortar o download atual e limpa a pasta temp do usuário

### Pastas no volume
data/users/{user_id}/temp  -> temporário, apagado após TTL
data/users/{user_id}/links -> histórico em JSON (permanece)
