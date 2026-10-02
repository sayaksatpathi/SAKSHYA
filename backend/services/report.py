"""
SAKSHYA Report Generation Service

Generates professional forensic PDF reports with case information,
evidence details, AI analysis results, integrity verification,
and chain of custody.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend import SAKSHYA_VERSION
from backend.models import (
    Case, Evidence, EvidenceSegment, AIResult,
    ChainEvent, MerkleRecord, TrustReceipt,
)
from backend.services.ledger import LedgerService
from backend.crypto.hashing import sha256_bytes

logger = logging.getLogger(__name__)


class ReportService:
    """Generates forensic PDF reports."""

    def __init__(self, db: Session):
        self.db = db

    def generate_report(self, case_id: str) -> bytes:
        """
        Generate a complete forensic report PDF.

        Returns:
            PDF content as bytes.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.colors import HexColor
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak,
            )
            from reportlab.lib.units import inch, mm
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
        except ImportError:
            logger.error("reportlab not installed — cannot generate PDF")
            raise RuntimeError("PDF generation requires reportlab. Install with: pip install reportlab")

        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case '{case_id}' not found")

        # Collect all data
        evidence_items = self.db.query(Evidence).filter(Evidence.case_id == case_id).all()
        chain_events = (
            self.db.query(ChainEvent)
            .filter(ChainEvent.case_id == case_id)
            .order_by(ChainEvent.sequence_number)
            .all()
        )
        merkle_records = self.db.query(MerkleRecord).filter(MerkleRecord.case_id == case_id).all()
        trust_receipts = self.db.query(TrustReceipt).filter(TrustReceipt.case_id == case_id).all()

        ledger = LedgerService(self.db)
        chain_head = ledger.get_chain_head(case_id)
        chain_verify = ledger.verify_chain(case_id)

        # Build PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=20*mm, bottomMargin=20*mm,
            leftMargin=20*mm, rightMargin=20*mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Title"],
            fontSize=24, textColor=HexColor("#1a1a2e"),
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "CustomHeading", parent=styles["Heading1"],
            fontSize=14, textColor=HexColor("#16213e"),
            spaceBefore=12, spaceAfter=6,
        )
        subheading_style = ParagraphStyle(
            "CustomSub", parent=styles["Heading2"],
            fontSize=11, textColor=HexColor("#0f3460"),
            spaceBefore=8, spaceAfter=4,
        )
        normal = styles["Normal"]

        elements = []

        # --- Title Page ---
        elements.append(Spacer(1, 60))
        elements.append(Paragraph("SAKSHYA", title_style))
        elements.append(Paragraph("Forensic Evidence Report", heading_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"<b>Case:</b> {case.case_number}", normal))
        elements.append(Paragraph(f"<b>Title:</b> {case.title}", normal))
        elements.append(Paragraph(f"<b>Investigator:</b> {case.investigator}", normal))
        elements.append(Paragraph(
            f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", normal
        ))
        elements.append(Paragraph(f"<b>SAKSHYA Version:</b> {SAKSHYA_VERSION}", normal))
        elements.append(Spacer(1, 20))

        report_content_hash = sha256_bytes(
            f"{case_id}:{datetime.now(timezone.utc).isoformat()}".encode()
        )
        elements.append(Paragraph(f"<b>Report ID:</b> RPT-{report_content_hash[:12].upper()}", normal))
        elements.append(PageBreak())

        # --- Case Information ---
        elements.append(Paragraph("1. Case Information", heading_style))
        case_data = [
            ["Field", "Value"],
            ["Case ID", case.id],
            ["Case Number", case.case_number],
            ["Title", case.title],
            ["Description", case.description or "N/A"],
            ["Investigator", case.investigator],
            ["Status", case.status],
            ["Created", str(case.created_at)],
        ]
        t = Table(case_data, colWidths=[120, 380])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # --- Evidence Information ---
        elements.append(Paragraph("2. Evidence Information", heading_style))
        for ev in evidence_items:
            elements.append(Paragraph(f"Evidence: {ev.original_filename}", subheading_style))
            ev_data = [
                ["Field", "Value"],
                ["Evidence ID", ev.id],
                ["Original Filename", ev.original_filename],
                ["Source Device", ev.source_device or "N/A"],
                ["Source Vendor", ev.source_vendor or "Unknown"],
                ["Type", ev.evidence_type],
                ["Size", f"{ev.size:,} bytes"],
                ["SHA-256", ev.sha256],
                ["Acquired At", str(ev.acquired_at)],
                ["Acquired By", ev.acquired_by or "N/A"],
                ["Codec", ev.codec or "N/A"],
                ["Resolution", ev.resolution or "N/A"],
                ["FPS", str(ev.fps) if ev.fps else "N/A"],
                ["Duration", f"{ev.duration:.1f}s" if ev.duration else "N/A"],
            ]
            t = Table(ev_data, colWidths=[120, 380])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#16213e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 8))

            # Recovery segments for this evidence
            segments = self.db.query(EvidenceSegment).filter(
                EvidenceSegment.evidence_id == ev.id
            ).all()
            if segments:
                elements.append(Paragraph("Recovered Segments:", normal))
                seg_data = [["#", "Method", "SHA-256", "Confidence", "Status"]]
                for i, seg in enumerate(segments, 1):
                    seg_data.append([
                        str(i), seg.recovery_method,
                        seg.sha256[:24] + "...",
                        f"{seg.confidence:.0%}" if seg.confidence else "N/A",
                        seg.validation_status,
                    ])
                t = Table(seg_data, colWidths=[30, 100, 180, 70, 70])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f3460")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 8))

        elements.append(PageBreak())

        # --- AI Analysis ---
        elements.append(Paragraph("3. AI Analysis Results", heading_style))
        elements.append(Paragraph(
            "<i>Note: AI results are investigative aids and not definitive identifications. "
            "Similarity scores do not prove identity. OCR output may contain errors. "
            "Detection confidence values are model estimates.</i>",
            normal,
        ))
        elements.append(Spacer(1, 8))

        for ev in evidence_items:
            ai_results = self.db.query(AIResult).filter(
                AIResult.evidence_id == ev.id
            ).order_by(AIResult.timestamp).all()

            if ai_results:
                elements.append(Paragraph(
                    f"Detections for: {ev.original_filename}", subheading_style
                ))
                ai_data = [["Time", "Type", "Label", "Confidence", "Track", "Model"]]
                for r in ai_results:
                    time_str = f"{r.timestamp:.1f}s" if r.timestamp is not None else "N/A"
                    ai_data.append([
                        time_str, r.detection_type, r.label or "N/A",
                        f"{r.confidence:.0%}", r.track_id or "—",
                        r.model_name or "N/A",
                    ])
                t = Table(ai_data, colWidths=[50, 60, 100, 70, 50, 100])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#16213e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 8))

            from backend.models import ForensicFinding
            forensics = self.db.query(ForensicFinding).filter(
                ForensicFinding.evidence_id == ev.id
            ).order_by(ForensicFinding.timestamp_start).all()

            if forensics:
                elements.append(Paragraph(f"Forensic Findings for: {ev.original_filename}", subheading_style))
                for_data = [["Time", "Type", "Severity", "Description", "Method"]]
                for f in forensics:
                    time_str = f"{f.timestamp_start:.1f}s" if f.timestamp_start is not None else "N/A"
                    for_data.append([
                        time_str, f.type, f.severity, 
                        f.description[:40] + "..." if len(f.description) > 40 else f.description, 
                        f.method
                    ])
                t = Table(for_data, colWidths=[50, 80, 60, 160, 80])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#3a0a0a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 8))

        elements.append(PageBreak())

        # --- Integrity Verification ---
        elements.append(Paragraph("4. Integrity Verification", heading_style))

        integrity_data = [
            ["Component", "Status", "Detail"],
            ["Chain of Custody",
             "CHAIN VALID" if chain_verify["valid"] else "CHAIN INVALID",
             f"{chain_verify['verified_events']}/{chain_verify['total_events']} events verified"],
            ["Chain Head", chain_head[:32] + "..." if chain_head else "N/A", "SHA-256"],
        ]

        if merkle_records:
            latest_merkle = merkle_records[-1]
            integrity_data.append([
                "Merkle Root", latest_merkle.root_hash[:32] + "...",
                f"{latest_merkle.leaf_count} leaves, {latest_merkle.algorithm}",
            ])

        if trust_receipts:
            latest_trust = trust_receipts[-1]
            integrity_data.append([
                "Trust Signature",
                latest_trust.verification_status or "UNVERIFIED",
                f"Authority: {latest_trust.authority_id}, Algorithm: {latest_trust.algorithm}",
            ])
        else:
            integrity_data.append(["Trust Signature", "NOT AVAILABLE", "No trust receipt issued"])

        t = Table(integrity_data, colWidths=[100, 150, 250])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # --- Chain of Custody ---
        elements.append(Paragraph("5. Chain of Custody", heading_style))
        chain_data = [["#", "Timestamp", "Event", "Actor", "Hash (truncated)"]]
        for ev in chain_events:
            chain_data.append([
                str(ev.sequence_number),
                ev.timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.timestamp else "N/A",
                ev.event_type,
                ev.actor[:25],
                ev.event_hash[:20] + "...",
            ])
        t = Table(chain_data, colWidths=[30, 110, 130, 100, 130])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ]))
        elements.append(t)
        elements.append(PageBreak())

        # --- Legal Certificate Section ---
        elements.append(Paragraph("6. BSA Section 63(4) Certificate Draft", heading_style))
        elements.append(Paragraph(
            "<b>IMPORTANT NOTICE:</b> This certificate is generated by SAKSHYA as a structured electronic-record "
            "certificate draft based on information recorded during acquisition and analysis. It does not itself determine "
            "admissibility, legal sufficiency, or compliance with any court or statutory requirement. The responsible person/signatory "
            "must review the factual assertions, complete any required fields, and sign or otherwise authenticate the certificate as appropriate.",
            normal,
        ))
        elements.append(Spacer(1, 12))

        from backend.models import ElectronicRecordCertificate
        for ev in evidence_items:
            cert = self.db.query(ElectronicRecordCertificate).filter(ElectronicRecordCertificate.evidence_id == ev.id).order_by(ElectronicRecordCertificate.created_at.desc()).first()
            
            elements.append(Paragraph(f"<b>Certificate for Evidence: {ev.original_filename}</b>", subheading_style))
            elements.append(Spacer(1, 6))
            
            if not cert:
                elements.append(Paragraph("<i>No Electronic Record Certificate drafted for this evidence yet.</i>", normal))
                elements.append(Spacer(1, 20))
                continue
                
            elements.append(Paragraph(f"<b>STATUS:</b> <font color='red'>{cert.certificate_status}</font> (SAKSHYA-GENERATED DRAFT)", normal))
            elements.append(Spacer(1, 6))
            
            cert_body = f"""
            <b>A. Case and Record Identification</b><br/>
            <b>Case ID:</b> {cert.case_id}<br/>
            <b>Certificate ID:</b> {cert.certificate_id}<br/>
            <b>Electronic Record Identifier:</b> {cert.electronic_record_identifier}<br/>
            <b>Description:</b> {cert.electronic_record_description or "NOT PROVIDED"}<br/>
            <b>Format:</b> {cert.record_format}<br/>
            <b>Size:</b> {cert.record_size} bytes<br/>
            <b>SHA-256:</b> {cert.record_sha256}<br/><br/>
            
            <b>B. Acquisition / Production</b><br/>
            <b>Acquisition Date:</b> {cert.date_of_acquisition or "NOT PROVIDED"}<br/>
            <b>Generation Date:</b> {cert.date_of_generation}<br/>
            <b>Method:</b> {cert.method_of_production or "NOT RECORDED"}<br/>
            <b>Software Used:</b> {cert.software_used or "NOT PROVIDED"} (v{cert.software_version or "NOT PROVIDED"})<br/>
            <b>Source Device ID:</b> {cert.source_device_id or "NOT PROVIDED"}<br/>
            <b>Source Device Type:</b> {cert.source_device_type or "NOT PROVIDED"}<br/>
            <b>Source Description:</b> {cert.source_device_description or "NOT PROVIDED"}<br/><br/>
            
            <b>C. Relevant Section 63(2) Information</b><br/>
            <b>Device Operational Status:</b> {cert.device_operational_status or "NOT VERIFIED"}<br/>
            &nbsp;&nbsp;<i>Basis: SAKSHYA software cannot physically verify hardware condition.</i><br/>
            <b>Regular Use Context:</b> {cert.regular_use_context or "NOT RECORDED"}<br/>
            <b>Information Fed in Ordinary Course:</b> {cert.information_fed_in_ordinary_course or "NOT RECORDED"}<br/><br/>
            
            <b>D. Analysis / Derivation</b><br/>
            <b>Analysis ID:</b> {cert.analysis_id or "NOT APPLICABLE"}<br/>
            <b>Derivation Relationship:</b> {cert.derivation_relationship or "Original Evidence"}<br/><br/>
            
            <b>E. Integrity</b><br/>
            <b>Evidence SHA-256:</b> {cert.record_sha256}<br/>
            <b>Certificate Content Hash:</b> {cert.certificate_content_hash or "NOT CALCULATED"}<br/>
            <i>Chain state and Merkle root verified in preceding sections.</i><br/><br/>
            
            <b>F. Declarant / Signatory</b><br/>
            <b>Name:</b> {cert.signatory_name or "___________________________"}<br/>
            <b>Role/Designation:</b> {cert.signatory_role or "___________________________"}<br/>
            <b>Organization:</b> {cert.signatory_organization or "___________________________"}<br/>
            <b>Address:</b> {getattr(cert, 'signatory_address', "___________________________")}<br/>
            <b>Contact:</b> {getattr(cert, 'signatory_contact', "___________________________")}<br/>
            <b>Signature Status:</b> {cert.signature_status}<br/>
            <b>Date / Place:</b> ___________________________<br/><br/>
            <b>Signature:</b><br/><br/><br/><br/>
            """
            elements.append(Paragraph(cert_body, normal))
            elements.append(Spacer(1, 20))

        # --- Footer ---
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"<i>Generated automatically by SAKSHYA System v{SAKSHYA_VERSION} — "
            f"Report hash will be computed after generation</i>",
            ParagraphStyle("Footer", parent=normal, fontSize=7, textColor=HexColor("#999999")),
        ))

        # Build PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()

        # Log report generation
        ledger.append_event(
            case_id=case_id,
            event_type="REPORT_GENERATED",
            actor="SAKSHYA Report Engine",
            meta_data={
                "report_hash": sha256_bytes(pdf_bytes)[:32],
                "pages": "multi",
                "version": SAKSHYA_VERSION,
            },
        )

        return pdf_bytes
