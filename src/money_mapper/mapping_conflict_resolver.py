#!/usr/bin/env python3
"""
Mapping Conflict Resolver - Handle conflicts and duplicates in mappings.

This module provides functionality to detect, report, and resolve conflicts and
duplicate mappings across mapping files.
"""

from typing import Any
from difflib import SequenceMatcher


def detect_duplicate_patterns(mappings: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Detect duplicate or similar patterns within mappings.
    
    Args:
        mappings: Dictionary of mappings organized by section
        
    Returns:
        List of detected duplicates with details
    """
    duplicates = []
    seen_patterns = {}  # normalized pattern -> (section, pattern, mapping)
    
    for section, section_mappings in mappings.items():
        if not isinstance(section_mappings, dict):
            continue
        
        for pattern, mapping in section_mappings.items():
            # Normalize pattern for comparison
            normalized = pattern.lower().strip()
            
            if normalized in seen_patterns:
                # Found a duplicate
                prev_section, prev_pattern, prev_mapping = seen_patterns[normalized]
                
                duplicates.append({
                    "pattern": normalized,
                    "first": {
                        "section": prev_section,
                        "pattern": prev_pattern,
                        "mapping": prev_mapping
                    },
                    "duplicate": {
                        "section": section,
                        "pattern": pattern,
                        "mapping": mapping
                    }
                })
            else:
                seen_patterns[normalized] = (section, pattern, mapping)
    
    return duplicates


def check_mapping_conflicts(
    existing_mappings: dict[str, Any],
    new_mappings: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Check for conflicts between existing and new mappings.
    
    Args:
        existing_mappings: Existing mappings
        new_mappings: New mappings to add
        
    Returns:
        List of conflicts found
    """
    conflicts = []
    
    for pattern, new_mapping in new_mappings.items():
        # Check if pattern exists in existing mappings
        for existing_pattern, existing_mapping in existing_mappings.items():
            if existing_pattern.lower() == pattern.lower():
                # Check if the mappings are different
                if existing_mapping != new_mapping:
                    conflicts.append({
                        "pattern": pattern,
                        "existing": existing_mapping,
                        "new": new_mapping
                    })
                break
    
    return conflicts


def resolve_conflicts(
    conflicts: list[dict[str, Any]],
    action: str = "keep_existing"
) -> dict[str, Any]:
    """
    Resolve conflicts by choosing which mapping to keep.
    
    Args:
        conflicts: List of conflicts to resolve
        action: Resolution action ('keep_existing' or 'use_new')
        
    Returns:
        Resolved mappings
    """
    resolved = {}
    
    for conflict in conflicts:
        pattern = conflict["pattern"]
        
        if action == "use_new":
            resolved[pattern] = conflict["new"]
        else:  # keep_existing
            resolved[pattern] = conflict["existing"]
    
    return resolved


def find_duplicates_across_files(
    private_mappings: dict[str, Any],
    public_mappings: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Find duplicate patterns that exist in both private and public mappings.
    
    Args:
        private_mappings: Private mappings
        public_mappings: Public mappings
        
    Returns:
        List of patterns that appear in both files
    """
    duplicates = []
    
    private_patterns = set(p.lower() for p in private_mappings.keys())
    
    for public_pattern in public_mappings.keys():
        if public_pattern.lower() in private_patterns:
            duplicates.append({
                "pattern": public_pattern.lower(),
                "in_private": True,
                "in_public": True
            })
    
    return duplicates


def find_similar_patterns(
    patterns: list[str],
    threshold: float = 0.6
) -> list[list[str]]:
    """
    Find groups of similar patterns.
    
    Args:
        patterns: List of patterns to compare
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        List of groups containing similar patterns
    """
    groups = []
    used = set()
    
    for i, pattern1 in enumerate(patterns):
        if i in used:
            continue
        
        group = [pattern1]
        used.add(i)
        
        for j, pattern2 in enumerate(patterns[i+1:], i+1):
            if j in used:
                continue
            
            # Calculate similarity
            similarity = SequenceMatcher(None, pattern1.lower(), pattern2.lower()).ratio()
            
            if similarity >= threshold:
                group.append(pattern2)
                used.add(j)
        
        if len(group) > 1:
            groups.append(group)
    
    return groups


def detect_conflicting_categories(
    mappings: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Detect when the same merchant has multiple different categories assigned.
    
    Args:
        mappings: Dictionary of mappings
        
    Returns:
        List of category conflicts
    """
    conflicts = []
    merchant_categories = {}  # merchant -> set of categories
    
    for section, section_mappings in mappings.items():
        if not isinstance(section_mappings, dict):
            continue
        
        for pattern, mapping in section_mappings.items():
            if not isinstance(mapping, dict):
                continue
            
            merchant_name = mapping.get("name", "").lower()
            category = mapping.get("category")
            
            if merchant_name and category:
                if merchant_name not in merchant_categories:
                    merchant_categories[merchant_name] = set()
                
                merchant_categories[merchant_name].add(category)
    
    # Find merchants with multiple categories
    for merchant, categories in merchant_categories.items():
        if len(categories) > 1:
            conflicts.append({
                "merchant": merchant,
                "categories": list(categories)
            })
    
    return conflicts


def find_pattern_wildcards_overlap(
    patterns: list[str]
) -> list[dict[str, Any]]:
    """
    Find patterns where a wildcard might be overmatching.
    
    Args:
        patterns: List of patterns including wildcards
        
    Returns:
        List of potential overlap issues
    """
    issues = []
    wildcard_patterns = [p for p in patterns if "*" in p]
    exact_patterns = [p for p in patterns if "*" not in p]
    
    for wildcard in wildcard_patterns:
        for exact in exact_patterns:
            # Check if exact pattern matches the wildcard
            wildcard_regex = wildcard.replace("*", ".*")
            
            # Simple pattern matching
            if _matches_pattern(exact, wildcard):
                issues.append({
                    "wildcard": wildcard,
                    "pattern": exact,
                    "type": "exact_matches_wildcard"
                })
    
    return issues


def _matches_pattern(text: str, pattern: str) -> bool:
    """
    Check if text matches a wildcard pattern.
    
    Args:
        text: Text to match
        pattern: Pattern with * wildcards
        
    Returns:
        True if text matches pattern
    """
    import fnmatch
    return fnmatch.fnmatch(text.lower(), pattern.lower())
