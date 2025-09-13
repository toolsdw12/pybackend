from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time
from core.document_processor import DocumentProcessor
from services.ocr_integration.ocr_factory import OCRServiceType
import config

# Configure logging
logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    yield
    # Shutdown
    logger.info("Application shutting down...")

app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_CREDENTIALS,
    allow_methods=config.CORS_METHODS,
    allow_headers=config.CORS_HEADERS,
)

# Initialize components
document_processor = DocumentProcessor()

def get_default_ocr_service() -> OCRServiceType:
    """Get the default OCR service type from config"""
    try:
        return OCRServiceType(config.DEFAULT_OCR_SERVICE)
    except ValueError:
        logger.warning(f"Invalid OCR service type in config: {config.DEFAULT_OCR_SERVICE}. Using AWS Textract as default.")
        return OCRServiceType.TEXTRACT_SERVICE

@app.post("/api/extract-text")
async def extract_text(
    file: UploadFile = File(...),
    announcement: str = Form(None),
    stockData: str = Form(None),
    ocr_service: OCRServiceType = None
) -> dict:
    python_start = time.perf_counter()
    
    try:
        # Use provided OCR service or default from config
        if ocr_service is None:
            ocr_service = get_default_ocr_service()
            
        logger.info(f"Processing file: {file.filename} with OCR service: {ocr_service.value}")
        
        # Read the uploaded file
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        #sample data of stockData
        """
        {
            _id: ObjectId("..."),  // MongoDB's unique identifier
            isin: "INE123456789",  // Unique ISIN code
                stockName: "Example Company Limited",
                bse: {
                    isTradable: true,
                    scriptCode: 12345
                },
                nse: {
                    isTradable: true,
                    scriptCode: "EXAMPLE"
                },
                resultPageConfig: {
                    type: "Single",  // or "Multi"
                    display: "One",  // or "Different" or null
                    pageType: "Consolidated"  // or "Standalone" or null
                },
                firstAnnouncementSent: false
            }
        """
        
        # Process the document using the document processor service
        result = await document_processor.process_document(
            content=content,
            filename=file.filename,
            ocr_service=ocr_service,
            stock_data=stockData,
            python_start=python_start
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )
    
@app.get("/")
async def read_root():
    return {"message": config.API_TITLE}

@app.get("/test")
async def test_endpoint():
    return {"message": "API is working correctly", "status": "success"}
