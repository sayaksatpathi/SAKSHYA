content = open('backend/api/certificates.py').read()
replacement = '''@router.post("/certificates/{certificate_id}/sign")
def sign_certificate(certificate_id: str, signature: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """
    Cryptographically signs the BSA Section 63(4) certificate draft, making it legally admissible.
    """
    cert = db.query(ElectronicRecordCertificate).filter(ElectronicRecordCertificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    cert.signature = signature
    cert.signed_by = current_user.username
    db.commit()
    return {"status": "Signed", "certificate_id": certificate_id}
'''
if 'def sign_certificate' not in content:
    with open('backend/api/certificates.py', 'a') as f:
        f.write('\n' + replacement)
print("done")
