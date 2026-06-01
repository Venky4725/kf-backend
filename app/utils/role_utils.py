def normalize_role(role: str | None) -> str:
    """
    Normalizes role strings to standard formats:
    AI/ML -> AIML
    Full Stack -> FULLSTACK
    empty/null/GENERAL/UNSPECIFIED -> GENERAL
    """
    if not role:
        return "GENERAL"
    
    role_upper = role.strip().upper()
    
    # Handle variations of AIML
    if any(var in role_upper for var in ("AI/ML", "AI-ML", "AIML", "AI_ML", "AI ML", "ARTIFICIAL INTELLIGENCE", "MACHINE LEARNING", "DATA SCIENCE")):
        return "AIML"
    
    # Handle variations of FULLSTACK
    if any(var in role_upper for var in ("FULL STACK", "FULLSTACK", "FULL-STACK", "FULL_STACK", "FULLSTACK", "MERN STACK", "DJANGO FULL STACK")):
        return "FULLSTACK"
        
    # Handle variations of GENERAL
    if role_upper in ("GENERAL", "UNSPECIFIED", "NULL", "NONE", "ALL"):
        return "GENERAL"
        
    return "GENERAL"
