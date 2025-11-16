"""
Vector Embeddings Generator for Knowledge Base
Generates embeddings for newly downloaded files from download statistics
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dao import CourseDAO
from rag.service import RagService
from rag_scraper.logger import get_logger


class VectorEmbeddingsGenerator:
    """Generates vector embeddings for newly downloaded course materials"""
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.docx', '.pptx', '.html', '.htm'}
    
    def __init__(self, base_url: str = "http://127.0.0.1:8009/"):
        """
        Initialize the embeddings generator
        
        Args:
            base_url: Base URL for the HTTP service serving knowledge_base files
        """
        self.base_url = base_url.rstrip("/") + "/"
        self.course_dao = CourseDAO()
        self.rag_service = RagService()
        self.logger = get_logger(log_file="rag_scraper.log", verbose=True)
    
    def _get_course_id(self, course_name: str) -> Optional[int]:
        """
        Get course ID from course name
        
        Args:
            course_name: Full course name
            
        Returns:
            Course ID if found, None otherwise
        """
        course_id = self.course_dao.find_id_by_name(course_name)
        return int(course_id) if course_id is not None else None
    
    def generate_embeddings_for_files(
        self,
        file_paths: List[str],
        course_name: str
    ) -> Dict[str, any]:
        """
        Generate embeddings for a list of files from a specific course
        
        Args:
            file_paths: List of absolute file paths to process
            course_name: Full course name
            
        Returns:
            Dictionary with statistics about embedding generation
        """
        if not file_paths:
            return {
                "course_name": course_name,
                "success": True,
                "files_processed": 0,
                "files_success": 0,
                "files_failed": 0,
                "vectors_generated": 0
            }
        
        self.logger.info(f"  📚 Processing {len(file_paths)} files for: {course_name[:50]}...", force=True)
        
        # Get course ID
        course_id = self._get_course_id(course_name)
        if course_id is None:
            self.logger.warning(f"    ⚠️  Course ID not found, skipping: {course_name}")
            return {
                "course_name": course_name,
                "success": False,
                "error": "Course ID not found",
                "files_processed": 0,
                "files_success": 0,
                "files_failed": 0,
                "vectors_generated": 0
            }
        
        files_success = 0
        files_failed = 0
        total_vectors = 0
        
        # Process each file
        for file_path in file_paths:
            try:
                # Check file extension
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext not in self.SUPPORTED_EXTENSIONS:
                    self.logger.info(f"    ⏩ Skipping unsupported file type: {os.path.basename(file_path)}")
                    continue
                
                # Check if file exists
                if not os.path.exists(file_path):
                    self.logger.warning(f"    ⚠️  File not found: {file_path}")
                    files_failed += 1
                    continue
                
                self.logger.info(f"    🔄 Ingesting: {os.path.basename(file_path)}", force=True)
                
                # Generate embeddings using RAG service
                # Note: ingest_file() expects local file path, not HTTP URL
                # It will internally build the HTTP URL using build_http_url()
                result = self.rag_service.ingest_file(
                    course_id=course_id,      # int: course ID
                    file_path=file_path,      # str: local absolute file path
                    base_url=self.base_url    # str: HTTP service base URL
                )
                
                # ingest_file returns: {"course_id": int, "chunks": int, "vectors_added": int}
                chunks_count = result.get('chunks', 0)
                vectors_count = result.get('vectors_added', 0)
                total_vectors += vectors_count
                files_success += 1
                self.logger.info(f"      ✅ Generated {chunks_count} chunks, {vectors_count} vectors", force=True)

                    
            except Exception as e:
                files_failed += 1
                self.logger.error(f"      ❌ Error processing {os.path.basename(file_path)}: {e}")
        
        self.logger.info(
            f"  ✅ Completed: {files_success} success, {files_failed} failed, {total_vectors} vectors",
            force=True
        )
        
        return {
            "course_name": course_name,
            "success": files_failed == 0,
            "files_processed": len(file_paths),
            "files_success": files_success,
            "files_failed": files_failed,
            "vectors_generated": total_vectors
        }


def generate_embeddings_from_download_stats(
    download_stats: Dict,
    base_url: str = None
) -> Dict:
    """
    Generate embeddings for files downloaded in the scraping session
    
    This function processes the download statistics from Moodle/Exambase scraping
    and generates vector embeddings for newly downloaded files.
    
    Args:
        download_stats: Download statistics from scrape() function, should contain:
            - 'moodle': {'downloaded_file_paths': [...], ...}
            - 'exambase': {'downloaded_file_paths': [...], ...}  (if available)
        base_url: Base URL for HTTP file access (default: http://127.0.0.1:8009/)
        
    Returns:
        Dictionary with embedding generation statistics:
        {
            'success': bool,
            'total_files': int,
            'total_vectors': int,
            'courses_processed': int
        }
    """
    if base_url is None:
        base_url = os.getenv("KNOWLEDGE_BASE_URL", "http://kengu-api.natapp1.cc/")
    
    logger = get_logger(log_file="rag_scraper.log", verbose=True)
    generator = VectorEmbeddingsGenerator(base_url=base_url)
    
    # Collect all file paths by course
    course_files = {}  # course_name -> list of file paths
    
    # Process Moodle downloads
    moodle_stats = download_stats.get('moodle', {})
    moodle_file_paths = moodle_stats.get('downloaded_file_paths', [])
    
    logger.info(f"  Moodle: {len(moodle_file_paths)} files downloaded", force=True)
    
    # Group Moodle files by course (extract course name from path)
    for file_path in moodle_file_paths:
        # File path format: /path/to/knowledge_base/CourseName/file.pdf
        path_parts = Path(file_path).parts
        try:
            kb_index = path_parts.index('knowledge_base')
            if kb_index + 1 < len(path_parts):
                course_folder = path_parts[kb_index + 1]
                if course_folder not in course_files:
                    course_files[course_folder] = []
                course_files[course_folder].append(file_path)
        except (ValueError, IndexError):
            logger.warning(f"  ⚠️  Could not extract course from path: {file_path}")
    
    # Process Exambase downloads (if available)
    exambase_stats = download_stats.get('exambase', {})
    exambase_file_paths = exambase_stats.get('downloaded_file_paths', [])
    
    logger.info(f"  Exambase: {len(exambase_file_paths)} files downloaded", force=True)
    
    # Group Exambase files by course
    for file_path in exambase_file_paths:
        path_parts = Path(file_path).parts
        try:
            kb_index = path_parts.index('knowledge_base')
            if kb_index + 1 < len(path_parts):
                course_folder = path_parts[kb_index + 1]
                if course_folder not in course_files:
                    course_files[course_folder] = []
                course_files[course_folder].append(file_path)
        except (ValueError, IndexError):
            logger.warning(f"  ⚠️  Could not extract course from path: {file_path}")
    
    if not course_files:
        logger.info("  ℹ️  No new files to process for embeddings", force=True)
        return {
            'success': True,
            'total_files': 0,
            'total_vectors': 0,
            'courses_processed': 0,
            'message': 'No new files to process'
        }
    
    logger.info(f"  📊 Processing {len(course_files)} courses with new files", force=True)
    
    # Generate embeddings for each course
    total_files = 0
    total_vectors = 0
    courses_processed = 0
    all_success = True
    
    for course_folder, files in course_files.items():
        result = generator.generate_embeddings_for_files(files, course_folder)
        total_files += result['files_processed']
        total_vectors += result['vectors_generated']
        courses_processed += 1
        if not result['success']:
            all_success = False
    
    return {
        'success': all_success,
        'total_files': total_files,
        'total_vectors': total_vectors,
        'courses_processed': courses_processed
    }
