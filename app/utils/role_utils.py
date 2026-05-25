def normalize_role(role: str | None) -> str:
    """
    Normalizes role strings to standard formats:
    AI/ML -> AIML
    ai-ml -> AIML
    Full Stack -> FULLSTACK
    fullstack -> FULLSTACK
    empty/null/GENERAL/UNSPECIFIED -> ALL
    """
    if not role:
        return "ALL"
    
    role = role.strip().upper()
    
    # Handle variations of AIML
    if role in ("AI/ML", "AI-ML", "AIML", "AI_ML", "AI / ML"):
        return "AIML"
    
    # Handle variations of FULLSTACK
    if role in ("FULL STACK", "FULLSTACK", "FULL-STACK", "FULL_STACK"):
        return "FULLSTACK"
        
    # Handle variations of ALL
    if role in ("GENERAL", "UNSPECIFIED", "NULL", "NONE", "ALL"):
        return "ALL"
        
    return role
