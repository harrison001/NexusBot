module.exports = {
  apps: [
    {
      name: 'telegram-img2pdf-bot',
      script: 'uvicorn',
      args: 'telegram_img2pdf_bot:app --host 0.0.0.0 --port 8001',
      cwd: '/work/backEnd/telegram_bot',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        PORT: 8001
      },
      env_production: {
        NODE_ENV: 'production',
        PORT: 8001
      },
      log_file: './logs/combined.log',
      out_file: './logs/out.log',
      error_file: './logs/error.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z',
      merge_logs: true
    }
  ]
};