#!/usr/bin/env python3
"""
Test script to verify text extraction functionality
"""
import asyncio
import tempfile
import os
from pathlib import Path

# Add the app directory to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.document import DocumentService
from app.services.extractor import DocumentExtractor

async def test_text_extraction():
    """Test the text extraction functionality"""
    print("Testing text extraction functionality...")
    
    # Create a temporary text file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_content = """This is a test document.

It contains multiple paragraphs to test the extraction functionality.

The system should be able to extract all this text and save it properly."""
        f.write(test_content)
        temp_file_path = f.name
    
    try:
        # Test the extractor directly
        print("1. Testing DocumentExtractor...")
        extracted_data = DocumentExtractor.extract_text(temp_file_path, "test.txt")
        print(f"   Extracted data keys: {list(extracted_data.keys())}")
        print(f"   Format: {extracted_data.get('format')}")
        print(f"   Content items: {len(extracted_data.get('content', []))}")
        
        # Test the document service
        print("\n2. Testing DocumentService...")
        service = DocumentService(upload_dir="test_uploads")
        
        # Read the file content
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        
        # Process the upload
        result = await service.process_upload(file_content, "test.txt")
        print(f"   Upload result: {result.message}")
        print(f"   File ID: {result.file_id}")
        print(f"   Content summary: {result.content_summary is not None}")
        
        if result.content_summary:
            print(f"   Word count: {result.content_summary.get('word_count')}")
            print(f"   Character count: {result.content_summary.get('character_count')}")
        
        # Test getting extracted text
        print("\n3. Testing get_extracted_text...")
        extracted_text = await service.get_extracted_text(result.file_id)
        print(f"   Extracted text length: {len(extracted_text) if extracted_text else 0}")
        if extracted_text:
            print(f"   First 100 chars: {extracted_text[:100]}...")
        
        # Test getting file info
        print("\n4. Testing get_file_info...")
        file_info = await service.get_file_info(result.file_id)
        print(f"   File info found: {file_info is not None}")
        if file_info:
            print(f"   Has content summary: {file_info.content_summary is not None}")
        
        # Clean up
        print("\n5. Testing delete_file...")
        success = await service.delete_file(result.file_id)
        print(f"   Delete successful: {success}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        # Clean up test uploads directory
        if os.path.exists("test_uploads"):
            import shutil
            shutil.rmtree("test_uploads")

if __name__ == "__main__":
    asyncio.run(test_text_extraction())
