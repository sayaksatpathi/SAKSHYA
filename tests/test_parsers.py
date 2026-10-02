import pytest
from backend.services.parsers import GenericVideoParser, HikvisionParser, DahuaParser, FutureVendorParser

def test_generic_parser():
    parser = GenericVideoParser()
    assert parser.identify(b"some ftyp mp4 header") == True
    assert parser.parse(b"") == {"vendor": "Generic", "status": "VALIDATED"}

def test_hikvision_parser():
    parser = HikvisionParser()
    assert parser.identify(b"HKVS data") == True
    assert parser.parse(b"") == {"vendor": "Hikvision", "status": "PARTIAL"}

def test_dahua_parser():
    parser = DahuaParser()
    assert parser.identify(b"DHAV data") == True
    assert parser.parse(b"") == {"vendor": "Dahua", "status": "PARTIAL"}

def test_unsupported_parser():
    parser = FutureVendorParser()
    assert parser.identify(b"Unknown data") == False
    assert parser.parse(b"") == {"vendor": "Future", "status": "UNSUPPORTED_VENDOR_FORMAT"}
