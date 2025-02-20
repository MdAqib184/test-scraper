FROM python:3.9

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python scripts
COPY hashTags.py script.py ./

# CMD ["sh", "-c", "python script.py && python hashTags.py"]
# CMD ["python", "script.py"]
CMD ["python", "hashTags.py"]