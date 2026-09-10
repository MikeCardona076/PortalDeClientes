# Deploy — Nginx Proxy Manager (portalclientes.pacifico.mikecardona076.com)

Cuando subas a producción:

1. Levanta los contenedores:
   ```bash
   cp .env.example .env   # edita SECRET_KEY, POSTGRES_*, SMTP y DJANGO_ENV=prod
   docker compose up -d --build
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   docker compose exec web python manage.py seed_bustrax --bunit set_tj2
   docker compose exec web python manage.py backfill 2026
   ```

2. En Nginx Proxy Manager crea un **Proxy Host**:
   - Domain: `portalclientes.pacifico.mikecardona076.com`
   - Scheme: `http`
   - Forward Hostname: `clientesd_web` (o la IP del host si NPM no comparte red)
   - Forward Port: `8000`
   - Block Common Exploits: ON
   - Websockets Support: ON (opcional)

3. Pestaña **SSL**:
   - Request a new SSL Certificate (Let's Encrypt)
   - Force SSL: ON
   - HTTP/2: ON

4. En `.env` (prod) confirma:
   ```
   DJANGO_ENV=prod
   DEBUG=False
   ALLOWED_HOSTS=portalclientes.pacifico.mikecardona076.com
   CSRF_TRUSTED_ORIGINS=https://portalclientes.pacifico.mikecardona076.com
   SECRET_KEY=<clave larga y aleatoria>
   EMAIL_HOST=...   # SMTP para reset de contraseña
   ```

5. Si NPM y el compose no están en la misma red Docker, agrégalos a una red común:
   ```yaml
   networks:
     web_network:
       external: true
   ```
   y referencia esa red en el servicio `web`.
