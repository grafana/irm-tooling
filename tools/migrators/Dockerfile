FROM python:3.14.1-alpine3.21@sha256:fd8407cacb1028c803566276ae25eb7c2a00fbaa210a0a5670994f6866e29278

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt requirements.txt
RUN python3 -m pip install -r requirements.txt

COPY . .

# Create data directory and generate session ID
RUN mkdir -p /app/data && \
    python3 -c "import uuid; open('/app/data/.session', 'w').write(str(uuid.uuid4()))"

# Set session file location
ENV SESSION_FILE=/app/data/.session

CMD ["python3", "main.py"]
