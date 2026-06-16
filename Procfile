web: /bin/sh -c 'exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips "${TRUSTED_PROXY_HOSTS:-127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16}"'
