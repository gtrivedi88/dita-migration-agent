"""
LLM client module.

Handles communication with LLM APIs for targeted edits.
Supports OpenAI-compatible endpoints (including internal Gemini proxies).
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from openai import OpenAI


def get_bundled_cert_path() -> Optional[Path]:
    """Get path to bundled SSL certificate."""
    # Check for bundled cert in package
    package_dir = Path(__file__).parent.parent
    cert_path = package_dir / "certs" / "2022-IT-Root-CA.pem"
    if cert_path.exists():
        return cert_path
    return None


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class RateLimitError(LLMError):
    """Rate limit exceeded."""
    pass


class InvalidResponseError(LLMError):
    """LLM returned invalid or unparseable response."""
    pass


@dataclass
class LLMResponse:
    """Response from LLM API."""
    
    success: bool
    """Whether the request succeeded."""
    
    content: Optional[str] = None
    """Raw text content from LLM."""
    
    parsed: Optional[Dict[str, Any]] = None
    """Parsed JSON response if applicable."""
    
    tokens_used: int = 0
    """Number of tokens used."""
    
    error: Optional[str] = None
    """Error message if request failed."""
    
    retry_count: int = 0
    """Number of retries attempted."""


@dataclass
class TargetedEdit:
    """A targeted edit to apply to a file."""
    
    old_string: str
    """Text to find and replace."""
    
    new_string: str
    """Replacement text."""
    
    def is_valid(self) -> bool:
        """Check if the edit is valid."""
        # old_string must be non-empty
        if not self.old_string or not self.old_string.strip():
            return False
        # new_string can be empty (for deletions) but must be different
        return self.old_string != self.new_string


class LLMClient:
    """
    Client for interacting with LLM APIs via OpenAI-compatible interface.
    
    Supports:
    - Internal Gemini proxies (OpenAI-compatible endpoints)
    - Standard OpenAI API
    - Any OpenAI-compatible endpoint
    
    Key design principle: Always request TARGETED EDITS (old_string → new_string),
    never ask for complete file rewrites. This prevents:
    - Content loss from token limits
    - LLM "summarizing" content
    - Breaking conditional blocks
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        base_url: Optional[str] = None,
        cert_path: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: API key for authentication.
            model: Model to use.
            base_url: Custom API endpoint (for internal proxies).
            cert_path: Optional custom SSL certificate.
            temperature: Temperature for generation (0.1 for deterministic).
            max_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
        """
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self._api_key = api_key
        self._base_url = base_url
        
        # Determine SSL certificate to use
        # Priority: 1) Explicitly provided, 2) Bundled with package
        effective_cert = cert_path
        if not effective_cert:
            bundled_cert = get_bundled_cert_path()
            if bundled_cert:
                effective_cert = str(bundled_cert)
        
        # Initialize OpenAI client
        self.client = None
        if api_key:
            # Create HTTP client with SSL certificate if available
            http_client = None
            if effective_cert and base_url:
                # Use custom SSL cert for internal endpoints
                http_client = httpx.Client(verify=effective_cert, timeout=timeout)
            
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                http_client=http_client,
            )
        
        # Track usage
        self.total_requests = 0
        self.total_tokens = 0
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        expect_json: bool = True,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The main prompt.
            system_prompt: Optional system instructions.
            expect_json: If True, attempt to parse response as JSON.
            
        Returns:
            LLMResponse with the result.
        """
        # Handle missing client (no API key, dry-run mode)
        if self.client is None:
            return LLMResponse(
                success=False,
                error="No API key configured",
            )
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Make request using OpenAI SDK
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                
                self.total_requests += 1
                
                # Extract text
                if not response.choices or not response.choices[0].message.content:
                    raise InvalidResponseError("Empty response from LLM")
                
                content = response.choices[0].message.content.strip()
                
                # Get token usage
                tokens_used = 0
                if response.usage:
                    tokens_used = response.usage.total_tokens
                else:
                    # Estimate if not provided
                    tokens_used = len(content.split()) * 2
                
                self.total_tokens += tokens_used
                
                # Parse JSON if expected
                parsed = None
                if expect_json:
                    parsed = self._extract_json(content)
                    if parsed is None:
                        raise InvalidResponseError(f"Could not parse JSON from response: {content[:200]}")
                
                return LLMResponse(
                    success=True,
                    content=content,
                    parsed=parsed,
                    tokens_used=tokens_used,
                    retry_count=attempt,
                )
                
            except Exception as e:
                last_error = str(e)
                
                # Check for rate limiting
                if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                
                # Check for retryable errors
                if "timeout" in str(e).lower() or "connection" in str(e).lower():
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                # For InvalidResponseError, try with more explicit formatting
                if isinstance(e, InvalidResponseError) and attempt < self.max_retries - 1:
                    # Modify prompt to be more explicit about JSON format
                    if "IMPORTANT: Return ONLY valid JSON" not in messages[-1]["content"]:
                        messages[-1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON, no markdown, no explanation."
                    continue
                
                # Non-retryable error
                break
        
        return LLMResponse(
            success=False,
            error=last_error,
            retry_count=self.max_retries - 1,
        )
    
    def get_targeted_edit(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[TargetedEdit], Optional[str]]:
        """
        Request a targeted edit from the LLM.
        
        Args:
            prompt: The prompt describing what to fix.
            system_prompt: Optional system instructions.
            
        Returns:
            Tuple of (TargetedEdit, error_message).
            If successful, error_message is None.
            If failed, TargetedEdit is None.
        """
        response = self.generate(prompt, system_prompt, expect_json=True)
        
        if not response.success:
            return None, response.error
        
        # Extract edit from parsed response
        try:
            parsed = response.parsed
            
            # Handle nested 'edit' structure
            if "edit" in parsed:
                parsed = parsed["edit"]
            
            old_string = parsed.get("old_string", "")
            new_string = parsed.get("new_string", "")
            
            edit = TargetedEdit(old_string=old_string, new_string=new_string)
            
            if not edit.is_valid():
                return None, "Invalid edit: old_string is empty or same as new_string"
            
            return edit, None
            
        except (KeyError, TypeError, AttributeError) as e:
            return None, f"Failed to parse edit from response: {e}"
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response text.
        
        Handles various response formats:
        - Pure JSON
        - JSON wrapped in markdown code blocks
        - JSON with surrounding text
        
        Args:
            text: Raw response text.
            
        Returns:
            Parsed JSON dict, or None if parsing fails.
        """
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(json_block_pattern, text)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
        
        # Try to find JSON object in text
        # Look for { ... } pattern
        brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(brace_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "model": self.model_name,
        }
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "LLMClient":
        """
        Create an LLMClient from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with keys:
                - api_key: Required
                - model: Optional, defaults to gemini-3-flash-preview
                - base_url: Optional, for custom endpoints
                - cert_path: Optional
                
        Returns:
            Configured LLMClient instance.
        """
        return cls(
            api_key=config["api_key"],
            model=config.get("model", "gemini-3-flash-preview"),
            base_url=config.get("base_url"),
            cert_path=config.get("cert_path"),
        )
