"""
SAKSHYA Vendor-Agnostic Extension Architecture for DVR Parsers.
"""

from abc import ABC, abstractmethod
from typing import Optional

class DVRParser(ABC):
    """Abstract base class for all DVR parsers."""
    @abstractmethod
    def identify(self, data: bytes) -> bool:
        pass
        
    @abstractmethod
    def parse(self, data: bytes) -> Optional[dict]:
        pass

class GenericVideoParser(DVRParser):
    def identify(self, data: bytes) -> bool:
        # Standard generic headers (e.g., MP4)
        return b"ftyp" in data[:1024]
        
    def parse(self, data: bytes) -> Optional[dict]:
        return {"vendor": "Generic", "status": "VALIDATED"}

class VendorParserInterface(DVRParser):
    pass

class HikvisionParser(VendorParserInterface):
    def identify(self, data: bytes) -> bool:
        return b"HKVS" in data[:1024]
        
    def parse(self, data: bytes) -> Optional[dict]:
        return {"vendor": "Hikvision", "status": "PARTIAL"}

class DahuaParser(VendorParserInterface):
    def identify(self, data: bytes) -> bool:
        return b"DHAV" in data[:1024]
        
    def parse(self, data: bytes) -> Optional[dict]:
        return {"vendor": "Dahua", "status": "PARTIAL"}

class FutureVendorParser(VendorParserInterface):
    def identify(self, data: bytes) -> bool:
        return False
        
    def parse(self, data: bytes) -> Optional[dict]:
        return {"vendor": "Future", "status": "UNSUPPORTED_VENDOR_FORMAT"}

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class ProprietaryDVRParser:
    """
    Parses and recovers proprietary DVR formats like .dav or raw .h264
    by extracting the underlying stream and wrapping it in standard MP4.
    """
    def __init__(self, workspace: str):
        self.workspace = workspace
        
    def recover_dav(self, input_path: str, output_path: str) -> bool:
        """
        Uses FFmpeg to re-mux .dav (Dahua/CP Plus) to .mp4 without transcoding.
        .dav files are often just encrypted or multiplexed h264/h265 streams.
        """
        if not os.path.exists(input_path):
            return False
            
        try:
            # ffmpeg -i input.dav -c:v copy -c:a copy output.mp4
            cmd = [
                "ffmpeg", "-y", "-i", input_path, 
                "-c:v", "copy", "-c:a", "copy", 
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Successfully carved/recovered .dav file to {output_path}")
                return True
            else:
                logger.error(f"FFmpeg failed to carve .dav: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error parsing .dav: {str(e)}")
            return False
