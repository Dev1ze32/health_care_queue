# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Create the static directory if it doesn't exist (for qr.png)
RUN mkdir -p static

# Expose the port the app runs on
EXPOSE 5001

# Run the application
CMD ["python", "app.py"]