## --- mysql Commands ---
use (database_name)
SHOW TABLES;
describe (table_name)
SELECT * FROM users_user LIMIT 100

## -- dbshell -- 
<!--  -->
SELECT * FROM django_migrations WHERE app = 'inventory';
DELETE FROM django_migrations WHERE app = 'appname' AND name = '0001_initial';

## Restart Server
<!--  -->
sudo systemctl restart gunicorn

## Server Logs
<!--  -->
watch -d -n 1 systemctl status gunicorn.service

