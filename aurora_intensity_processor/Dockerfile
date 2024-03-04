# Use an official Python runtime as a parent image, with GDAL pre-installed
FROM osgeo/gdal:ubuntu-small-3.6.3

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y python3-pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME AuroraProcessor

# Run app.py when the container launches
CMD ["python3", "./aurora_intensity_processor.py"]
