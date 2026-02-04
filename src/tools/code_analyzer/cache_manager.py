"""
Cache Manager for Code Analyzer
Handles caching of AST parsing and analysis results to speed up processing.
"""
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class CachingManager:
    """
    Manages caching for file analysis.
    Uses file content hash as key.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize caching manager.
        
        Args:
            cache_dir: custom cache directory (default: ~/.yaver/cache/ast)
        """
        if cache_dir:
            self.base_dir = cache_dir
        else:
            self.base_dir = Path.home() / ".yaver" / "cache" / "ast"
            
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read 4k bytes at a time
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return ""

    def _get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path for a given hash"""
        # Use first 2 chars for subfolder to avoid too many files in one dir
        subfolder = self.base_dir / file_hash[:2]
        subfolder.mkdir(exist_ok=True)
        return subfolder / f"{file_hash}.pkl"

    def get_cached_analysis(self, file_path: Path) -> Optional[Any]:
        """
        Retrieve cached analysis result if valid.
        
        Args:
            file_path: Path to the source file
            
        Returns:
            Cached object or None
        """
        if not file_path.exists():
            return None
            
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return None
            
        cache_path = self._get_cache_path(file_hash)
        
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {file_path}: {e}")
                
        return None

    def save_analysis(self, file_path: Path, data: Any):
        """
        Save analysis result to cache.
        
        Args:
            file_path: Path to the source file (to calculate hash key)
            data: The analysis object/data to pickle
        """
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return
            
        cache_path = self._get_cache_path(file_hash)
        
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save cache for {file_path}: {e}")

    def clear(self):
        """Clear all cache"""
        import shutil
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)
