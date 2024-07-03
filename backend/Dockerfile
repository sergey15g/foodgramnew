FROM python:3.11.4-bullseye
WORKDIR /app
COPY requirements.txt .
RUN  pip install --upgrade pip && pip install -r requirements.txt
COPY . ./