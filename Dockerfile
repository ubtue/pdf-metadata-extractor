FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y pandoc && \
    apt-get clean

COPY . /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8090

CMD ["python", "webserver.py"]
