import os
import time
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class TextractOCR:
    def __init__(self):
        self.client = boto3.client(
            'textract',
            region_name=os.getenv('AWS_REGION'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

    async def process_document(self, content: bytes) -> Dict[str, Any]:
        """
        Extract text from document content using AWS Textract
        
        Args:
            content (bytes): The document content as bytes
            
        Returns:
            Dict containing extracted text and timing information
        """
        try:
            # Start Textract processing
            textract_start = time.perf_counter()
            logger.info(f'Textract API call started at: {textract_start}')
            
            response = self.client.detect_document_text(
                Document={
                    'Bytes': content
                }
            )
            
            textract_end = time.perf_counter()
            logger.info(f'Textract API call completed at: {textract_end}')
            logger.info(f'Textract API duration: {textract_end - textract_start} seconds')

           # Extract text from blocks
            extracted_text = '\n'.join(
                block['Text'] for block in response['Blocks']
                if block['BlockType'] == 'LINE'
            )

            #logger.info(f'Extracted text: {extracted_text}')

            return {
                'text': extracted_text,
                'timing': {
                    'start': textract_start,
                    'end': textract_end,
                    'duration': textract_end - textract_start
                }
            }

        except ClientError as e:
            logger.error(f'Error in Textract processing: {str(e)}')
            raise e
        except Exception as e:
            logger.error(f'Unexpected error in Textract processing: {str(e)}')
            raise e

# Create a singleton instance
textract_service = TextractOCR() 