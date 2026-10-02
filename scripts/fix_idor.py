import re

def add_idor(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Add dependencies to all functions
    func_pattern = re.compile(r'def (\w+)\(.*?(evidence_id:\s*str.*?)db:\s*Session\s*=\s*Depends\(get_db\)(.*?)\):', re.DOTALL)
    
    def replacer(match):
        func_name = match.group(1)
        args_before = match.group(2)
        args_after = match.group(3)
        # Skip if already has current_user
        if 'current_user' in args_after or 'current_user' in args_before:
            return match.group(0)
        
        return f'def {func_name}({args_before}db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator){args_after}):'
        
    content = func_pattern.sub(replacer, content)

    # Now replace the query logic
    query_pattern = re.compile(r'evidence\s*=\s*db\.query\(Evidence\)\.filter\(Evidence\.id\s*==\s*evidence_id\)\.first\(\)\s+if not evidence:\s+raise HTTPException\(status_code=404, detail=.*?\"Evidence .*? not found\"\)', re.DOTALL)
    
    replacement = '''evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")'''
    
    content = query_pattern.sub(replacement, content)
    
    with open(filepath, 'w') as f:
        f.write(content)

add_idor('backend/api/evidence.py')
add_idor('backend/api/analysis.py')
print('IDOR applied')
