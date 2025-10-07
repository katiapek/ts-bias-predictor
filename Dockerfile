# Use an official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app
COPY . .

# Expose port 8000 for Beanstalk
EXPOSE 8000

# Start the app with Uvicorn
CMD ["uvicorn", "timeseriespredictor.main:app", "--host", "0.0.0.0", "--port", "8000"]