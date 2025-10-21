"""
title: California Legal Code Citation Validator
author: Legal AI Team  
version: 2.0.0
description: Production-ready pipeline for hallucination-free legal citations using actual ca_codes_db schema
required_open_webui_version: 0.3.0
requirements: pymongo>=4.0.0
"""

from typing import List, Dict, Optional, Union, Generator, Iterator
from pydantic import BaseModel, Field
import re
from pymongo import MongoClient
from datetime import datetime, timedelta


class Filter:
    class Valves(BaseModel):
        """Configuration for the legal citation pipeline"""
        mongodb_uri: str = Field(
            default="mongodb://admin:legalcodes123@localhost:27017",
            description="MongoDB connection string with authentication"
        )
        database_name: str = Field(
            default="ca_codes_db",
            description="Database containing California legal codes"
        )
        collection_name: str = Field(
            default="section_contents",
            description="Collection with code section content"
        )
        architecture_collection: str = Field(
            default="code_architectures",
            description="Collection with code tree structure"
        )
        enable_direct_lookup: bool = Field(
            default=True,
            description="Enable direct MongoDB lookup for explicit citations"
        )
        enable_post_validation: bool = Field(
            default=True,
            description="Validate all citations after generation"
        )
        enable_legislative_history: bool = Field(
            default=True,
            description="Include legislative history in responses"
        )
        cache_ttl_seconds: int = Field(
            default=3600,
            description="Cache TTL for frequently accessed sections (1 hour default)"
        )
        debug_mode: bool = Field(
            default=False,
            description="Enable verbose logging"
        )

    def __init__(self):
        self.type = "filter"
        self.name = "California Legal Citation Validator"
        self.valves = self.Valves()
        
        # Enhanced citation patterns for California codes
        self.citation_patterns = [
            # Full name: "California Penal Code Section 187" or "Penal Code 187"
            re.compile(
                r'(?:California\s+)?([A-Za-z\s]+)\s+Code\s+(?:Section\s+)?§?\s*(\d+(?:\.\d+)?)',
                re.IGNORECASE
            ),
            # Abbreviations: "PEN 187", "CCP §1234", "CIV 1234.5"
            re.compile(
                r'\b(PEN|CIV|CCP|FAM|GOV|CORP|PROB|EVID)\s+§?\s*(\d+(?:\.\d+)?)\b',
                re.IGNORECASE
            ),
            # Alternative: "PC 187", "CC 1234" (common abbreviations)
            re.compile(
                r'\b(PC|CC|FC|GC|EC)\s+§?\s*(\d+(?:\.\d+)?)\b',
                re.IGNORECASE
            )
        ]
        
        # Map full names and abbreviations to database codes
        self.code_mapping = {
            "penal": "PEN", "pen": "PEN", "pc": "PEN",
            "civil": "CIV", "civ": "CIV", "cc": "CIV",
            "code of civil procedure": "CCP", "ccp": "CCP",
            "family": "FAM", "fam": "FAM", "fc": "FAM",
            "government": "GOV", "gov": "GOV", "gc": "GOV",
            "corporations": "CORP", "corp": "CORP",
            "probate": "PROB", "prob": "PROB",
            "evidence": "EVID", "evid": "EVID", "ec": "EVID"
        }
        
        self.code_names = {
            "PEN": "Penal",
            "CIV": "Civil",
            "CCP": "Code of Civil Procedure",
            "FAM": "Family",
            "GOV": "Government",
            "CORP": "Corporations",
            "PROB": "Probate",
            "EVID": "Evidence"
        }
        
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.architecture_collection = None
        self.section_cache = {}
        self.cache_timestamps = {}
    
    async def on_startup(self):
        """Initialize MongoDB connection"""
        try:
            self.mongo_client = MongoClient(
                self.valves.mongodb_uri,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.mongo_client[self.valves.database_name]
            self.collection = self.db[self.valves.collection_name]
            self.architecture_collection = self.db[self.valves.architecture_collection]
            
            # Test connection
            self.mongo_client.server_info()
            
            # Log connection info
            section_count = self.collection.count_documents({})
            print(f"✓ Legal Citation Validator: Connected to {self.valves.database_name}")
            print(f"✓ Loaded {section_count} California code sections")
            print(f"✓ Available codes: PEN, CIV, CCP, FAM, GOV, CORP, PROB, EVID")
            
        except Exception as e:
            print(f"✗ MongoDB connection failed: {e}")
            print(f"  URI: {self.valves.mongodb_uri.replace('legalcodes123', '***')}")
    
    async def on_shutdown(self):
        """Cleanup MongoDB connection"""
        if self.mongo_client:
            self.mongo_client.close()
            print("✓ MongoDB connection closed")
    
    def extract_citations(self, text: str) -> List[Dict[str, str]]:
        """
        Extract legal code citations from text using multiple patterns
        
        Returns:
            List of dicts with 'code', 'section', and 'full_citation'
        """
        citations = []
        seen_citations = set()  # Avoid duplicates
        
        for pattern in self.citation_patterns:
            matches = pattern.finditer(text)
            
            for match in matches:
                code_raw = match.group(1).strip().lower()
                section = match.group(2)
                
                # Map to database code format
                code = self.code_mapping.get(code_raw, code_raw.upper())
                
                # Ensure code is valid
                if code not in self.code_names:
                    continue
                
                # Create unique key to avoid duplicates
                citation_key = f"{code}-{section}"
                
                if citation_key not in seen_citations:
                    seen_citations.add(citation_key)
                    citations.append({
                        "code": code,
                        "section": section,
                        "full_citation": match.group(0)
                    })
        
        return citations
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached entry is still valid"""
        if cache_key not in self.cache_timestamps:
            return False
        
        timestamp = self.cache_timestamps[cache_key]
        age = (datetime.now() - timestamp).total_seconds()
        
        return age < self.valves.cache_ttl_seconds
    
    def clear_cache(self):
        """Clear all cached sections - useful for debugging cache issues"""
        self.section_cache.clear()
        self.cache_timestamps.clear()
        if self.valves.debug_mode:
            print("[CACHE CLEARED] All cached sections removed")
    
    async def fetch_exact_sections(
        self,
        citations: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Retrieve exact code sections from MongoDB (ca_codes_db.section_contents)

        Args:
            citations: List of parsed citations with 'code' and 'section' keys

        Returns:
            List of matching documents from MongoDB with actual schema fields
        """
        # Ensure MongoDB connection exists
        if self.collection is None:
            print("[FETCH] MongoDB not connected, initializing...")
            await self.on_startup()

        sections = []

        for citation in citations:
            try:
                # Check cache first
                cache_key = f"{citation['code']}-{citation['section']}"
                if self.is_cache_valid(cache_key):
                    cached = self.section_cache[cache_key].copy()
                    
                    # CRITICAL FIX: Validate cached content matches requested code
                    if cached.get("code") != citation["code"]:
                        if self.valves.debug_mode:
                            print(f"  [CACHE INVALID] {cache_key} - code mismatch: cached={cached.get('code')}, requested={citation['code']}")
                        # Remove invalid cache entry
                        del self.section_cache[cache_key]
                        del self.cache_timestamps[cache_key]
                    else:
                        cached["citation"] = citation["full_citation"]
                        sections.append(cached)
                        if self.valves.debug_mode:
                            print(f"  [CACHE HIT] {cache_key}")
                        continue

                # Query MongoDB using actual schema
                query = {
                    "code": citation["code"],
                    "section": citation["section"],
                    "is_current": True  # Only get current version
                }

                if self.valves.debug_mode:
                    print(f"  [QUERY] {query}")

                document = self.collection.find_one(query)
                
                if document:
                    section_data = {
                        "code": document.get("code"),
                        "section": document.get("section"),
                        "content": document.get("content", ""),
                        "legislative_history": document.get("legislative_history", "") if self.valves.enable_legislative_history else "",
                        "url": document.get("url", ""),
                        "division": document.get("division"),
                        "part": document.get("part"),
                        "chapter": document.get("chapter"),
                        "article": document.get("article"),
                        "citation": citation["full_citation"],
                        "updated_at": document.get("updated_at")
                    }
                    
                    # Cache the result with validation
                    # CRITICAL FIX: Ensure cached content matches the requested code
                    if document.get("code") == citation["code"]:
                        self.section_cache[cache_key] = section_data.copy()
                        self.cache_timestamps[cache_key] = datetime.now()
                        if self.valves.debug_mode:
                            print(f"  [CACHE STORE] {cache_key} - Validated and stored")
                    else:
                        if self.valves.debug_mode:
                            print(f"  [CACHE SKIP] {cache_key} - Code mismatch: db={document.get('code')}, requested={citation['code']}")
                    
                    sections.append(section_data)
                    
                    if self.valves.debug_mode:
                        print(f"  [DB FETCH] {cache_key} - Found")
                else:
                    # Log missing sections
                    if self.valves.debug_mode:
                        print(f"  ⚠ Warning: Section not found - {citation['full_citation']}")
                        print(f"    Query: code={citation['code']}, section={citation['section']}")
                    
            except Exception as e:
                print(f"✗ Error fetching section {citation['full_citation']}: {e}")
        
        return sections
    
    def format_section_context(self, sections: List[Dict]) -> str:
        """Format retrieved sections for context injection using actual schema"""
        context_parts = []
        
        for section in sections:
            code_name = self.code_names.get(section['code'], section['code'])
            
            # Build hierarchical location
            hierarchy_parts = []
            if section.get('division'):
                hierarchy_parts.append(f"Division {section['division']}")
            if section.get('part'):
                hierarchy_parts.append(f"Part {section['part']}")
            if section.get('chapter'):
                hierarchy_parts.append(f"Chapter {section['chapter']}")
            if section.get('article'):
                hierarchy_parts.append(f"Article {section['article']}")
            
            hierarchy_str = " > ".join(hierarchy_parts) if hierarchy_parts else "N/A"
            
            formatted = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**California {code_name} Code § {section['section']}**
Location: {hierarchy_str}

{section['content']}
"""
            if self.valves.enable_legislative_history and section.get('legislative_history'):
                formatted += f"\nLegislative History: {section['legislative_history']}"
            
            formatted += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            context_parts.append(formatted)
        
        return "\n".join(context_parts)
    
    async def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Pre-process user queries to detect direct citation requests"""
        try:
            messages = body.get("messages", [])
            if not messages or not self.valves.enable_direct_lookup:
                return body

            user_message = messages[-1].get("content", "")

            # Detect if user is asking for specific code sections
            citations_in_query = self.extract_citations(user_message)

            if citations_in_query:
                # User explicitly asked for specific sections
                exact_sections = await self.fetch_exact_sections(citations_in_query)

                if exact_sections:
                    # Inject exact content as context
                    context = self.format_section_context(exact_sections)
                    enriched_message = f"""{user_message}

[SYSTEM: Retrieved exact code sections from California codes database]
{context}

Instructions: Use ONLY the exact text provided above. Do not paraphrase or generate content not present in the retrieved sections."""

                    messages[-1]["content"] = enriched_message
                    body["messages"] = messages

                    if self.valves.debug_mode:
                        print(f"[INLET] Injected {len(exact_sections)} sections")

            return body
        except Exception as e:
            print(f"[INLET ERROR] {e}")
            import traceback
            traceback.print_exc()
            return body

    async def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Post-process LLM responses to validate citations"""
        try:
            messages = body.get("messages", [])
            if not messages or not self.valves.enable_post_validation:
                return body

            assistant_message = messages[-1].get("content", "")

            # Extract all citations from the response
            citations = self.extract_citations(assistant_message)

            if citations:
                exact_sections = await self.fetch_exact_sections(citations)

                # Create lookup map using actual schema field names
                section_map = {
                    f"{s['code']}-{s['section']}": s
                    for s in exact_sections
                }

                validated_response = assistant_message
                hallucinations_found = []
                verified_count = 0

                for citation in citations:
                    key = f"{citation['code']}-{citation['section']}"

                    if key in section_map:
                        # Citation exists in database - add verification badge
                        verified_count += 1
                        validated_response = validated_response.replace(
                            citation["full_citation"],
                            f"{citation['full_citation']} ✓",
                            1  # Replace only first occurrence
                        )
                    else:
                        # Citation does not exist in database - flag it
                        hallucinations_found.append(citation["full_citation"])

                        # Replace or flag the hallucinated citation
                        validated_response = validated_response.replace(
                            citation["full_citation"],
                            f"~~{citation['full_citation']}~~ ⚠️",
                            1
                        )

                # Add validation summary if hallucinations found
                if hallucinations_found:
                    validation_note = f"\n\n---\n⚠️ **Citation Validation Warning**\n"
                    validation_note += f"The following citations could not be verified in the database:\n"
                    for cite in hallucinations_found:
                        validation_note += f"- {cite}\n"
                    validation_note += "\nPlease verify these references independently."
                    validated_response += validation_note

                if self.valves.debug_mode:
                    print(f"[OUTLET] Verified: {verified_count}, Hallucinations: {len(hallucinations_found)}")

                messages[-1]["content"] = validated_response
                body["messages"] = messages

            return body
        except Exception as e:
            print(f"[OUTLET ERROR] {e}")
            import traceback
            traceback.print_exc()
            return body

