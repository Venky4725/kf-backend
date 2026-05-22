#!/usr/bin/env python3
"""
Verification script for fixed Roadmap Block Parsing.
Tests date detection, header ignoring, and multiline support.
"""

import sys
import os
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.roadmap_service import roadmap_service

def verify_parser():
    content = """
    Day
    Topic / Theme
    Key Activities & Exercises
    Daily Outcome

    Mon May 18
    Free AI APIs — Chat & Streaming
    Free LLM providers: Groq, Together, etc.
    Add free LLM-powered streaming chat to Knowledge Factory.
    Daily Outcome: Streaming chat UI working.

    Tue May 19
    RAG with Free APIs & Vector Search
    What RAG solves and how it works.
    Build a complete RAG chatbot.
    """
    
    print("Testing Parser with raw content...")
    entries = roadmap_service.preview_roadmap(content)
    
    print(f"Found {len(entries)} entries.")
    
    for i, e in enumerate(entries):
        print(f"\nEntry {i+1}:")
        print(f"  Day: {e['day']}")
        print(f"  Topic: {e['topic']}")
        print(f"  Activities:\n{e['activities']}")
        print(f"  Outcome:\n{e['outcome']}")
        
    if len(entries) == 2:
        print("\n✅ Entry count correct.")
    else:
        print(f"\n❌ Expected 2 entries, found {len(entries)}")

    # Test with "Wednesday Jun 2"
    content_2 = "Wednesday Jun 2\nAdvanced Topic\nActivity 1\nOutcome 1"
    entries_2 = roadmap_service.preview_roadmap(content_2)
    if len(entries_2) == 1 and entries_2[0]['day'] == "Wednesday Jun 2":
         print("✅ Date detection for 'Wednesday Jun 2' successful.")
    else:
         print("❌ Date detection failed for 'Wednesday Jun 2'.")

if __name__ == "__main__":
    verify_parser()
