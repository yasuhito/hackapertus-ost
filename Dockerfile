FROM python:3.11-slim
WORKDIR /app
COPY track_2a/requirements.txt /app/track_2a/requirements.txt
RUN pip install --no-cache-dir -r /app/track_2a/requirements.txt
COPY track_2a/src /app/track_2a/src
ENTRYPOINT ["python", "/app/track_2a/src/predict.py"]
CMD ["--input", "/data/cases.jsonl", "--output", "/output/predictions.jsonl"]
