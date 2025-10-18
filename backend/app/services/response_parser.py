"""Response parser for Claude LLM output."""
from __future__ import annotations

import json
import re
from uuid import UUID

from app.domain.schemas import ButtonChunk, RenderChunk, TextChunk


def parse_claude_response(claude_text: str) -> list[RenderChunk]:
    """
    Parse Claude's response into render chunks.
    
    Structure:
    1. Text before ```json``` becomes TextChunk
    2. Each object in JSON array becomes:
       - explanation field → TextChunk
       - rest of object → ButtonChunk with option_id
    
    Args:
        claude_text: Raw text response from Claude
        
    Returns:
        List of TextChunk and ButtonChunk objects
        
    Example:
        Input:
            "I recommend the 90s Grain style...\n\n```json\n[{...}]\n```"
        Output:
            [
                TextChunk(text="I recommend..."),
                TextChunk(text="explanation text"),
                ButtonChunk(label="90s Grain", option_id=UUID(...)),
                ...
            ]
    """
    chunks: list[RenderChunk] = []
    
    # Extract text before ```json block
    json_pattern = r"```json\s*(.*?)\s*```"
    match = re.search(json_pattern, claude_text, re.DOTALL | re.IGNORECASE)
    
    if not match:
        # No JSON found - return entire text as single TextChunk
        return [TextChunk(text=claude_text.strip())]
    
    # Add text before JSON as TextChunk
    text_before = claude_text[:match.start()].strip()
    if text_before:
        chunks.append(TextChunk(text=text_before))
    
    # Parse JSON array
    try:
        json_str = match.group(1)
        options = json.loads(json_str)
        
        if not isinstance(options, list):
            options = [options]  # Wrap single object in list
        
        for option in options:
            # Add explanation as TextChunk
            explanation = option.get("explanation", "")
            if explanation:
                chunks.append(TextChunk(text=explanation))
            
            # Add button for this option
            style_name = option.get("style") or option.get("motion", "Unknown")
            option_id = option.get("option_id")
            
            if option_id:
                # Convert string UUID to UUID object if needed
                if isinstance(option_id, str):
                    option_id = UUID(option_id)
                
                chunks.append(
                    ButtonChunk(
                        label=f"Generate {style_name}",
                        option_id=option_id
                    )
                )
    
    except (json.JSONDecodeError, ValueError) as e:
        # JSON parsing failed - add error message
        chunks.append(TextChunk(text=f"⚠️ Failed to parse options: {e}"))
    
    # Add text after JSON (if any)
    text_after = claude_text[match.end():].strip()
    if text_after:
        chunks.append(TextChunk(text=text_after))
    
    return chunks


def parse_claude_options_list(options: list[dict]) -> list[RenderChunk]:
    """
    Parse list of option dictionaries directly into render chunks.
    
    Alternative to parse_claude_response when you already have parsed JSON.
    
    Args:
        options: List of option dictionaries from Claude
        
    Returns:
        List of TextChunk and ButtonChunk objects
    """
    chunks: list[RenderChunk] = []
    
    for option in options:
        # Skip options with errors
        if "error" in option:
            continue
        
        # Handle intro text (Claude's initial response before tool calls)
        if option.get("type") == "intro_text":
            intro_text = option.get("text", "")
            if intro_text:
                chunks.append(TextChunk(text=intro_text))
            continue
        
        # Add button FIRST
        model_type = option.get("model", "")
        if model_type == "text-to-image":
            display_name = option.get("style", "Unknown Style")
        else:  # image-to-video
            display_name = option.get("motion", "Unknown Motion")
        
        option_id = option.get("option_id")
        if option_id:
            if isinstance(option_id, str):
                option_id = UUID(option_id)
            
            chunks.append(
                ButtonChunk(
                    label=f"Generate {display_name}",
                    option_id=option_id
                )
            )
        
        # Add explanation/advice as TextChunk AFTER button
        text = option.get("explanation") or option.get("advice", "")
        if text:
            chunks.append(TextChunk(text=text))
    
    return chunks
