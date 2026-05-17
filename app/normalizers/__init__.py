"""Normalizers package - convert raw collector data to normalized intermediate representation."""
from app.normalizers.github_normalizer import GitHubNormalizer
from app.normalizers.vercel_normalizer import VercelNormalizer
from app.normalizers.cloudflare_normalizer import CloudflareNormalizer
from app.normalizers.conversation_normalizer import ConversationNormalizer

__all__ = [
    "GitHubNormalizer",
    "VercelNormalizer", 
    "CloudflareNormalizer",
    "ConversationNormalizer",
]
