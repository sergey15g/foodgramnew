FROM python:3.11.4-bullseye
WORKDIR /code
COPY requirements.txt .
RUN pip install -r /code/requirements.txt --no-cache-dir
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram.wsgi"]