import boto3
from datetime import datetime
import json
import numpy as np
from scipy.interpolate import griddata
from rasterio.transform import from_origin
from rasterio.io import MemoryFile

BUCKET_NAME = "aurora-explorer-data"
PREFIX = "aurora-data-raw/"


def aurora_intensity_processor(aurora_data):
    """
    Processes aurora observation data to generate a gridded intensity map.

    Args:
        aurora_data (dict): A dictionary containing coordinates and aurora intensity data.

    Returns:
        MemoryFile: A rasterio MemoryFile object containing the generated GeoTIFF data.
    """

    # Filter out coordinates with aurora intensity of 0
    filtered_coordinates = [
        coord for coord in aurora_data["coordinates"] if coord[2] > 0
    ]

    points = np.array(
        [(coord[0], coord[1]) for coord in filtered_coordinates]
    )  # Longitude, Latitude
    values = np.array([coord[2] for coord in filtered_coordinates])  # Aurora intensity

    # Define grid
    grid_x, grid_y = np.mgrid[-180:180:360j, -90:90:180j]

    # Perform interpolation
    grid_z = griddata(points, values, (grid_x, grid_y), method="linear")

    # Define the spatial resolution and transform for the output raster
    transform = from_origin(-180, 90, 1, 1)

    # We need to transfrom this as its currently vertical, we need it horizontal
    grid_z = np.rot90(grid_z)

    memory_file = MemoryFile()

    # Create a new GeoTIFF file
    with memory_file.open(
        driver="GTiff",
        height=grid_z.shape[0],
        width=grid_z.shape[1],
        count=1,
        dtype=str(grid_z.dtype),
        crs="+proj=latlong",
        transform=transform,
    ) as memfile:
        memfile.write(grid_z[::-1], 1)

    return memory_file


def download_latest_s3_file(bucket_name, prefix):
    """
    Fetches the latest file from a specified S3 bucket and prefix, returning its content as a JSON object.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix used to filter objects within the bucket.

    Returns:
        dict: The content of the latest file as a JSON object, or None if no files are found.
    """

    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    latest_file = None
    latest_time = None
    latest_content = None  # New variable to store the latest file content

    for page in page_iterator:
        if "Contents" in page:
            for obj in page["Contents"]:
                if latest_time is None or obj["LastModified"] > latest_time:
                    latest_time = obj["LastModified"]
                    latest_file = obj["Key"]

    if latest_file:
        obj = s3.get_object(Bucket=bucket_name, Key=latest_file)
        latest_content = json.loads(obj["Body"].read())

    return latest_content


def upload_memory_file_to_s3(memory_file, bucket_name, object_name):
    """
    Uploads a file stored in memory to an S3 bucket.

    Args:
        memory_file (MemoryFile): The file to upload, as a rasterio MemoryFile object.
        bucket_name (str): The name of the target S3 bucket.
        object_name (str): The object name (path) within the S3 bucket.
    """

    s3 = boto3.client("s3")
    s3.upload_fileobj(memory_file, bucket_name, object_name)
    print(f"Uploaded {object_name} to {bucket_name}")


def main():
    """
    Main function that orchestrates the downloading of the latest aurora data, processing it into a gridded intensity map, and uploading the result to S3.
    """

    aurora_data = download_latest_s3_file(BUCKET_NAME, PREFIX)

    if aurora_data is None:
        print("No aurora_data found")
        return

    # Process aurora data
    mem_file = aurora_intensity_processor(aurora_data)

    # Genearte file name with timestamp
    file_name_with_timestamp = (
        "aurora_intensity_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".tif"
    )
    upload_prefix_folder = "aurora_intensity_gridded_tiffs/"
    full_target_path = upload_prefix_folder + file_name_with_timestamp

    # Upload to S3
    print(f"Uploading to {full_target_path}")
    upload_memory_file_to_s3(
        mem_file, BUCKET_NAME, upload_prefix_folder + file_name_with_timestamp
    )


if __name__ == "__main__":
    main()
