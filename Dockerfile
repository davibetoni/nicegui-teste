FROM python:3.11-slim

RUN pip install --upgrade pip

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "app.py"]
