import boto3
import logging
from botocore.exceptions import ClientError
from typing import Optional
import config
import datetime
import re

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION
        )
        self.bucket_name = config.AWS_S3_BUCKET_NAME
    
    def _generate_result_filename(self, original_filename: str) -> str:
        """
        Generate a formatted result filename with timestamp
        
        Args:
            original_filename: The original filename
            
        Returns:
            Formatted result filename with internal spaces replaced by a single underscore
            and leading/trailing spaces removed
        """
  
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Trim leading and trailing spaces, then replace spaces with underscore
        normalized_filename = original_filename.strip().replace(' ', '_')
        # Remove file extension for cleaner, shorter URLs
        if '.' in normalized_filename:
            normalized_filename = normalized_filename.rsplit('.', 1)[0]
        return f"results_{timestamp}_{normalized_filename}.png"
    
    def upload_file(self, file_bytes: bytes, filename: str, use_formatted_name: bool = True) -> Optional[str]:
        """
        Upload a file to S3 and return the public URL
        
        Args:
            file_bytes: The file content in bytes
            filename: The name of the file
            use_formatted_name: Whether to format the filename (default: True)
            
        Returns:
            The public URL of the uploaded file or None if upload failed
        """
        try:
            # Generate formatted filename if requested
            if use_formatted_name:
                s3_filename = self._generate_result_filename(filename)
            else:
                s3_filename = filename
            
            # Upload the file (PNG only)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_filename,
                Body=file_bytes,
                ContentType='image/png',
                ContentDisposition='inline; filename="{}"'.format(s3_filename),
                CacheControl='public, max-age=31536000'
            )
            
            # Generate the public URL
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_filename}"
            logger.info(f"File uploaded successfully to S3: {url}")
            return url
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            return None