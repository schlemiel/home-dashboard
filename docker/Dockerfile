FROM python:3.11-slim

WORKDIR /app

COPY backend /app/backend
COPY data /app/data

RUN apt-get update && apt-get install -y --no-install-recommends \
	git \
	iputils-ping \
	net-tools \
	nmap \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

EXPOSE 8088

CMD ["python", "/app/backend/app.py"]
