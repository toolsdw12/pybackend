import os
import logging
import httpx
from pathlib import Path
from typing import Optional, Dict
import io
from services.notifications.financial_report_builder import FinancialReportBuilder

logger = logging.getLogger(__name__)

class TelegramNotificationService:
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram service with bot token and chat ID
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.financial_report_builder = FinancialReportBuilder()

    def send_message(self, text: str, parse_mode: Optional[str] = None) -> bool:
        """
        Send a text message to Telegram
        
        Args:
            text: The message text to send
            parse_mode: Optional parse mode for message formatting (HTML, Markdown, MarkdownV2)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare the message data
            data = {
                'chat_id': self.chat_id,
                'text': text
            }
            
            if parse_mode:
                data['parse_mode'] = parse_mode

            # Send the message
            response = httpx.post(
                f"{self.base_url}/sendMessage",
                data=data
            )

            if response.status_code == 200:
                logger.info("Successfully sent message to Telegram")
                return True
            else:
                logger.error(f"Failed to send message to Telegram. Status code: {response.status_code}, Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending message to Telegram: {str(e)}")
            return False

    def send_document(self, file_path: str, caption: Optional[str] = None) -> bool:
        """
        Send a document to Telegram
        
        Args:
            file_path: Path to the file to send
            caption: Optional caption for the document
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False

            # Prepare the file for sending
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {'chat_id': self.chat_id}
                if caption:
                    data['caption'] = caption

                # Send the file
                response = httpx.post(
                    f"{self.base_url}/sendDocument",
                    files=files,
                    data=data
                )

                if response.status_code == 200:
                    logger.info(f"Successfully sent document to Telegram: {file_path}")
                    return True
                else:
                    logger.error(f"Failed to send document to Telegram. Status code: {response.status_code}, Response: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error sending document to Telegram: {str(e)}")
            return False

    def send_document_bytes(self, pdf_bytes: bytes, filename: str, caption: Optional[str] = None) -> bool:
        """
        Send a PDF document directly from bytes to Telegram
        
        Args:
            pdf_bytes: PDF content as bytes
            filename: Name to give the file in Telegram
            caption: Optional caption for the document
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a file-like object from bytes
            file_obj = io.BytesIO(pdf_bytes)
            file_obj.name = filename

            # Prepare the file for sending
            files = {'document': file_obj}
            data = {'chat_id': self.chat_id}
            if caption:
                data['caption'] = caption

            # Send the file
            response = httpx.post(
                f"{self.base_url}/sendDocument",
                files=files,
                data=data
            )

            if response.status_code == 200:
                logger.info(f"Successfully sent document to Telegram: {filename}")
                return True
            else:
                logger.error(f"Failed to send document to Telegram. Status code: {response.status_code}, Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending document to Telegram: {str(e)}")
            return False 