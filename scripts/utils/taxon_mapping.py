#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BMB 2026-06-05
# Centralized taxon alias and suppression logic for Python scripts. Single source of
# truth for what counts as a valid/invalid taxon across the pipeline.

import json
import os
from typing import Dict, Set, FrozenSet, Optional, List
from functools import lru_cache

# Load configuration from JSON
_config_path = os.path.join(
    os.path.dirname(__file__), 'taxon_mapping_config.json'
)


@lru_cache(maxsize=1)
def _load_config() -> Dict:
    """Load taxon mapping configuration from JSON (cached)."""
    if not os.path.exists(_config_path):
        raise FileNotFoundError(f"Configuration file not found: {_config_path}")
    
    with open(_config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Lazy-loaded mappings with caching
@lru_cache(maxsize=1)
def get_na_tokens() -> FrozenSet[str]:
    """Get set of tokens that represent 'not applicable' / missing data."""
    config = _load_config()
    return frozenset(config.get('na_tokens', []))


@lru_cache(maxsize=1)
def get_taxon_aliases() -> Dict[str, str]:
    """Get mapping of taxon aliases to canonical GBIF-resolved names."""
    config = _load_config()
    return dict(config.get('alias_to_canonical', {}))


@lru_cache(maxsize=1)
def get_non_taxon_phrases() -> FrozenSet[str]:
    """Get set of generic/methodological phrases to suppress (not real taxon names)."""
    config = _load_config()
    return frozenset(config.get('suppress_non_taxon_phrases', []))


@lru_cache(maxsize=1)
def get_non_target_taxa() -> FrozenSet[str]:
    """Get set of taxa outside scope (bacteria, oomycetes, etc.) to suppress."""
    config = _load_config()
    return frozenset(config.get('suppress_non_target_taxa', []))


@lru_cache(maxsize=1)
def get_protected_higher_taxa() -> FrozenSet[str]:
    """Get set of higher taxa (class/phylum level) to protect from suppression."""
    config = _load_config()
    return frozenset(config.get('keep_higher_taxa', []))


@lru_cache(maxsize=1)
def get_allowed_taxon_ranks() -> FrozenSet[str]:
    """Get set of GBIF taxon ranks we accept in resolution."""
    config = _load_config()
    return frozenset(config.get('allowed_taxon_ranks', []))


@lru_cache(maxsize=1)
def get_allowed_kingdoms() -> FrozenSet[str]:
    """Get set of kingdoms to include in study (Fungi, Plantae)."""
    config = _load_config()
    return frozenset(k.lower() for k in config.get('allowed_kingdoms', []))


@lru_cache(maxsize=1)
def get_excluded_phyla() -> FrozenSet[str]:
    """Get set of phyla to explicitly exclude from final dataset."""
    config = _load_config()
    return frozenset(p.lower() for p in config.get('excluded_phyla', []))


@lru_cache(maxsize=1)
def get_excluded_classes() -> FrozenSet[str]:
    """Get set of classes to explicitly exclude from final dataset."""
    config = _load_config()
    return frozenset(c.lower() for c in config.get('excluded_classes', []))


@lru_cache(maxsize=1)
def get_excluded_guilds() -> FrozenSet[str]:
    """Get set of guilds to exclude from study focus (e.g., mycorrhiza, pgpr)."""
    config = _load_config()
    return frozenset(g.lower() for g in config.get('excluded_guilds', []))


@lru_cache(maxsize=1)
def get_default_fungal_phyla() -> FrozenSet[str]:
    """Get set of known fungal phyla for classification defaults."""
    config = _load_config()
    return frozenset(p.lower() for p in config.get('default_fungal_phyla', []))


@lru_cache(maxsize=1)
def get_default_plant_phyla() -> FrozenSet[str]:
    """Get set of known plant phyla for classification defaults."""
    config = _load_config()
    return frozenset(p.lower() for p in config.get('default_plant_phyla', []))


@lru_cache(maxsize=1)
def get_default_fungal_classes() -> FrozenSet[str]:
    """Get set of known fungal classes for classification defaults."""
    config = _load_config()
    return frozenset(c.lower() for c in config.get('default_fungal_classes', []))


@lru_cache(maxsize=1)
def get_default_plant_classes() -> FrozenSet[str]:
    """Get set of known plant classes for classification defaults."""
    config = _load_config()
    return frozenset(c.lower() for c in config.get('default_plant_classes', []))


# Helper functions for common checks
def should_skip_token(token: str) -> bool:
    """Return True if the token is NA, a non-taxon phrase, or a non-target kingdom."""
    if not token or not isinstance(token, str):
        return True
    
    token_lower = token.lower().strip()
    
    # Check NA tokens
    if token_lower in get_na_tokens():
        return True

    # Protected higher taxa are never skipped (not an allowlist).
    if token_lower in get_protected_higher_taxa():
        return False
    
    # Check non-taxon phrases
    if token_lower in get_non_taxon_phrases():
        return True
    
    # Check non-target taxa
    if token_lower in get_non_target_taxa():
        return True
    
    return False


def should_alias_token(token: str) -> Optional[str]:
    """Return the canonical alias for a token, or None if no alias exists."""
    if not token or not isinstance(token, str):
        return None
    
    token_lower = token.lower().strip()
    aliases = get_taxon_aliases()
    return aliases.get(token_lower)


def is_protected_higher_taxon(token: str) -> bool:
    """Return True if the token is in the protected higher-taxon list."""
    if not token or not isinstance(token, str):
        return False
    
    token_lower = token.lower().strip()
    return token_lower in get_protected_higher_taxa()


def is_allowed_kingdom(kingdom: str) -> bool:
    """Check if kingdom is in allowed set (Fungi or Plantae)."""
    if not kingdom or not isinstance(kingdom, str):
        return False
    
    return kingdom.lower().strip() in get_allowed_kingdoms()


def is_excluded_phylum(phylum: str) -> bool:
    """Check if phylum is in excluded set."""
    if not phylum or not isinstance(phylum, str):
        return False
    
    return phylum.lower().strip() in get_excluded_phyla()


def is_excluded_class(cls: str) -> bool:
    """Check if class is in excluded set."""
    if not cls or not isinstance(cls, str):
        return False
    
    return cls.lower().strip() in get_excluded_classes()


def is_excluded_guild(guild: str) -> bool:
    """Check if guild is in excluded set."""
    if not guild or not isinstance(guild, str):
        return False
    
    return guild.lower().strip() in get_excluded_guilds()


# Configuration statistics
MAPPING_STATS = {
    "total_na_tokens": 17,
    "total_aliases": 26,
    "total_suppress_non_taxon_phrases": 33,
    "total_suppress_non_target_taxa": 17,
    "total_protected_higher_taxa": 14,
    "total_allowed_ranks": 9,
    "total_default_fungal_phyla": 15,
    "total_default_plant_phyla": 11,
    "total_default_fungal_classes": 13,
    "total_default_plant_classes": 10,
}
