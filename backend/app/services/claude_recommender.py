"""
Claude Agent adapted for FastAPI backend with AsyncSession
Original: claude_agent.py - NO LOGIC CHANGES, ONLY ASYNC ADAPTATION
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Optional

import anthropic
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Option

load_dotenv()

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

claude_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


# Load styles and motions data
def load_styles_and_motions():
    """Load image styles and video motions from JSON files."""
    import pathlib
    
    # Get the app directory (backend/app)
    # In Docker: /app/backend/app/services/claude_recommender.py -> /app/backend/app/
    # Locally: .../higgsfield/backend/app/services/claude_recommender.py -> .../higgsfield/backend/app/
    app_dir = pathlib.Path(__file__).parent.parent
    
    styles_path = app_dir / "image_styles.json"
    motions_path = app_dir / "motions.json"
    
    with open(styles_path, "r", encoding="utf-8") as f:
        image_styles = json.load(f)
    
    with open(motions_path, "r", encoding="utf-8") as f:
        motions = json.load(f)
    
    return image_styles, motions


IMAGE_STYLES, MOTIONS = load_styles_and_motions()


def sanitize_tool_name(name: str) -> str:
    """Sanitize tool name to match pattern ^[a-zA-Z0-9_-]{1,128}$"""
    sanitized = name.lower()
    sanitized = ''.join(c if c.isalnum() or c in '_-' else '_' for c in sanitized)
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    sanitized = sanitized.strip('_')
    return sanitized[:100]


def generate_claude_tools() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """
    Generate tools for Claude API and create metadata mapping.
    Returns: (tools_list, tool_name_to_metadata_mapping)
    """
    tools = []
    metadata_mapping = {}
    
    # Create tools for each image style
    for style in IMAGE_STYLES:
        style_id = style["id"]
        style_name = style["name"]
        style_description = style.get("description", "")
        
        tool_name = f"create_image_{sanitize_tool_name(style_name)}"
        
        tool = {
            "name": tool_name,
            "description": f"Creates an image in '{style_name}' style. {style_description}",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "User's image description"
                    }
                },
                "required": ["user_prompt"]
            }
        }
        tools.append(tool)
        
        metadata_mapping[tool_name] = {
            "style_id": style_id,
            "style_name": style_name,
            "model_type": "text-to-image",
            "description": style_description
        }
    
    # Create tools for each video effect
    for motion in MOTIONS:
        motion_id = motion["id"]
        motion_name = motion["name"]
        motion_description = motion.get("description", "")
        
        tool_name = f"create_video_{sanitize_tool_name(motion_name)}"
        
        tool = {
            "name": tool_name,
            "description": f"Creates a video with '{motion_name}' effect. {motion_description}",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "User's video description"
                    }
                },
                "required": ["user_prompt"]
            }
        }
        tools.append(tool)
        
        metadata_mapping[tool_name] = {
            "motion_id": motion_id,
            "motion_name": motion_name,
            "model_type": "image-to-video",
            "description": motion_description,
            "start_end_frame": motion.get("start_end_frame", False)
        }
    
    return tools, metadata_mapping


# Generate tools and metadata
CLAUDE_TOOLS, TOOL_METADATA = generate_claude_tools()

# System prompt - EXACT COPY from claude_agent.py
SYSTEM_PROMPT = """You are an intelligent assistant for video and image generation on the Higgsfield AI platform.

Your main task is to help users choose the right style and model to create visual content.

IMPORTANT WORKFLOW:
1. Analyze user's request carefully
2. Select most relevant styles/effects from available tools
3. For EACH recommended style, you must:
   a) ALWAYS Explain why this style suits the user's request 
   b) IMMEDIATELY call the corresponding tool for that style
   c) The tool will return option_id and message_id

4. Present your recommendations in this EXAMPLE format:

Based on your request, I can offer you [N] styles:

**[Style Name 1]**
[EXPLANATION HERE - Explain why this style suits the user's request - 1-2 sentences]
[CALL TOOL HERE - tool will return: option_id, message_id]

**[Style Name 2]**
[EXPLANATION HERE - Explain why this style suits the user's request - 1-2 sentences]
[CALL TOOL HERE - tool will return: option_id, message_id]

**[Style Name 3]**
[EXPLANATION HERE - Explain why this style suits the user's request - 1-2 sentences]
[CALL TOOL HERE - tool will return: option_id, message_id]

CRITICAL: Call tools in the SAME order as you present the styles. Call one tool per style immediately after explaining it.

GUIDELINES:
- Choose styles that match the mood, theme, or aesthetic the user described
- Explain your reasoning clearly - why each style fits their vision
- Call tools ONLY for the styles you recommended
- Be creative and thoughtful in your selections
- If user request is vague, ask clarifying questions before making recommendations

Remember: Your tools create actual generation options in the database."""


async def enhance_prompt_with_claude(user_prompt: str, style_description: str) -> str:
    """Enhance user's prompt using Claude with style-specific guidance."""
    enhancement_prompt = f"""You are an expert prompt engineer specializing in creating hyper-detailed, photorealistic image generation prompts.

Transform the user's basic request into a professional, cinematic prompt following these principles:

**CORE ELEMENTS TO INCLUDE:**

1. **Subject & Composition:**
   - Detailed physical description (ethnicity, age, features, expression, gaze direction)
   - Precise posture, positioning, and body language
   - Clothing with fabric textures, cuts, details (silk fibers, raw-edge denim, weave patterns)
   - Camera angle and framing (eye-level, 50mm focal balance, center framing, etc.)

2. **Lighting & Atmosphere:**
   - Light source type and direction (harsh key from above, golden fill, soft daylight)
   - Shadow quality and placement (deep chiaroscuro, pooling shadows, nuanced shadows)
   - Reflections and highlights on surfaces (glossed skin, dappled gleams, metallic surfaces)
   - Overall mood and color temperature (warm/cool tones, muted palette)

3. **Environment & Setting:**
   - Specific location details (jagged stones, glass skyscrapers, airport terminal)
   - Background elements and their textures
   - Spatial relationship between subject and environment
   - Depth of field and focus areas (crisp focus center, gentle vignette blur)

4. **Technical & Textural Details:**
   - Fabric textures (thread weaves, fraying, distressed patterns)
   - Skin details (freckles, subtle highlights, pores)
   - Material properties (reflective glass, polished metal, rough indigo)
   - Digital clarity level (film-like stillness, tactile grit, hyper-real fidelity)

5. **Style-Specific Touches:**
   - Integrate the style characteristics naturally: {style_description}
   - Maintain spontaneous/candid feel if appropriate
   - Balance sharpness with subtle softness where needed
   - Create contrast between elements (urban-wild, structured-natural)

**USER'S ORIGINAL REQUEST:**
{user_prompt}

**YOUR TASK:**
Transform this into a 150-300 word professional prompt that reads like a cinematographer's detailed shot description. Use vivid, precise language. Include specific measurements, materials, angles, and atmospheric qualities. Make it feel tangible and real.

Return ONLY the enhanced prompt - no explanations, no meta-commentary, just the final prompt."""

    message = await claude_client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=8192,
        messages=[{"role": "user", "content": enhancement_prompt}]
    )
    
    return message.content[0].text.strip()


async def generate_style_explanation(
    user_request: str,
    style_name: str,
    style_description: str
) -> str:
    """
    Generate explanation why this style was chosen for the user's request
    EXACT COPY from claude_agent.py
    """
    explanation_prompt = f"""Explain why this style matches the user's request.

User's request: {user_request}
Style: {style_name}
Style Description: {style_description}

Write a explanation focusing on:
- How this style matches their vision
- Key visual characteristics that align with their needs
- What makes this style special for their use case

RULES:
- Do NOT use greetings ("Hey there!", "Hi!", "Hello!")
- Do NOT start with "I chose" or "I picked" or "I recommend"
- Start directly describing the style benefits
- Be informative and natural
Example format: "This style captures [characteristic] that perfectly matches your [need]. The [feature] will create [benefit], making it ideal for [use case]."

Return ONLY the explanation text."""

    message = await claude_client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=8192,
        messages=[{"role": "user", "content": explanation_prompt}]
    )
    
    return message.content[0].text.strip()


async def create_option_in_background(
    message_id: uuid.UUID,
    style_id: str,
    user_prompt: str,
    model_type: str,
    style_name: str,
    style_description: str,
    db: AsyncSession,
    explanation: str = ""  # Add explanation parameter
) -> Optional[str]:
    """
    Background task for creating Option with enhanced prompt
    ADAPTED from claude_agent.py for AsyncSession
    """
    try:
        # Enhance prompt
        enhanced_prompt = await enhance_prompt_with_claude(user_prompt, style_description)
        
        # Create Option in database WITH explanation
        option = Option(
            id=uuid.uuid4(),
            message_id=message_id,
            rank=0,  # Will be updated later with proper rank
            tool_type=model_type.replace('-', '_'),
            model_key="higgsfield_default",  # TODO: Map to actual model
            parameters={},  # TODO: Add style-specific parameters
            enhanced_prompt=enhanced_prompt,
            reason=explanation if explanation else f"Selected {style_name} style",  # Use explanation or meaningful default
            confidence=0.9,
            est_cost=None,
            est_latency_ms=None,
            requires_attachment=False,
        )
        
        db.add(option)
        await db.flush()
        
        return str(option.id)
        
    except Exception as e:
        print(f"Error creating option: {e}")
        await db.rollback()
        return None


async def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    message_id: uuid.UUID,
    db: AsyncSession
) -> dict[str, Any]:
    """
    Executes tool call and launches background task
    EXACT LOGIC from claude_agent.py, adapted for AsyncSession
    """
    # Get metadata from mapping
    tool_metadata = TOOL_METADATA.get(tool_name)
    
    if not tool_metadata:
        return {"error": f"Tool metadata not found for: {tool_name}"}
    
    user_prompt = tool_input.get("user_prompt", "")
    model_type = tool_metadata.get("model_type")
    
    if model_type == "text-to-image":
        style_id = tool_metadata["style_id"]
        style_name = tool_metadata["style_name"]
        style_description = tool_metadata.get("description", "")
        
        # Launch background task
        option_id = await create_option_in_background(
            message_id=message_id,
            style_id=style_id,
            user_prompt=user_prompt,
            model_type="text-to-image",
            style_name=style_name,
            style_description=style_description,
            db=db
        )
        
        return {
            "option_id": option_id,
            "message_id": str(message_id),
            "style_id": style_id,
            "status": "created",
            "model": "text-to-image",
            "style": style_name,
            "style_description": style_description
        }
        
    elif model_type == "image-to-video":
        motion_id = tool_metadata["motion_id"]
        motion_name = tool_metadata["motion_name"]
        motion_description = tool_metadata.get("description", "")
        
        # Launch background task
        option_id = await create_option_in_background(
            message_id=message_id,
            style_id=motion_id,
            user_prompt=user_prompt,
            model_type="image-to-video",
            style_name=motion_name,
            style_description=motion_description,
            db=db
        )
        
        return {
            "option_id": option_id,
            "message_id": str(message_id),
            "motion_id": motion_id,
            "status": "created",
            "model": "image-to-video",
            "motion": motion_name,
            "motion_description": motion_description,
            "start_end_frame": tool_metadata.get("start_end_frame", False)
        }
    
    return {"error": f"Unknown model type: {model_type}"}


class ClaudeRecommender:
    """LLM-powered recommender using Claude - FULL LOGIC from claude_agent.py"""

    @staticmethod
    async def generate_options_with_claude(
        text: str,
        message_id: uuid.UUID,
        db: AsyncSession,
        has_attachment: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Main function for communicating with Claude via Anthropic API with tools support
        COMPLETE COPY of chat_with_claude() logic from claude_agent.py
        Adapted for AsyncSession and returns list of dicts instead of formatted string
        """
        # Build messages for Claude
        messages = [{
            "role": "user",
            "content": text or "Create something creative"
        }]
        
        # First request to Claude with tools
        response = await claude_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=CLAUDE_TOOLS
        )
        
        # Check if there are tool calls
        stop_reason = response.stop_reason
        
        if stop_reason == "tool_use":
            # Extract text and tool calls
            text_parts = []
            tool_calls = []
            
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)
            
            initial_response = "\n".join(text_parts)
            
            # Add assistant message to history
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Execute tool calls
            tool_results = []
            tool_result_content = []
            
            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.input
                tool_use_id = tool_call.id
                
                # Execute tool
                tool_result = await execute_tool(tool_name, tool_input, message_id, db)
                tool_results.append(tool_result)
                
                # Format tool result for Claude
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
            
            # Add tool results to messages
            messages.append({
                "role": "user",
                "content": tool_result_content
            })
            
            # Continue tool calling loop until Claude stops requesting tools
            MAX_TOOL_ROUNDS = 10  # Safety limit to prevent infinite loops
            current_round = 1
            all_tool_results = tool_results.copy()
            
            while current_round < MAX_TOOL_ROUNDS:
                # Request to Claude with tool results
                next_response = await claude_client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=8192,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    tools=CLAUDE_TOOLS
                )
                
                # Check if Claude wants to use more tools
                has_tool_use = any(block.type == "tool_use" for block in next_response.content)
                
                if not has_tool_use:
                    # No more tool calls, get final text response
                    final_text = ""
                    for block in next_response.content:
                        if block.type == "text":
                            final_text += block.text
                    break
                
                # Process additional tool calls
                # Extract assistant message with tool calls
                assistant_content = []
                for block in next_response.content:
                    if block.type == "text":
                        assistant_content.append({
                            "type": "text",
                            "text": block.text
                        })
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })
                
                messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })
                
                # Execute new tool calls
                new_tool_results = []
                new_tool_result_content = []
                
                for block in next_response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id
                        
                        # Execute tool
                        tool_result = await execute_tool(tool_name, tool_input, message_id, db)
                        new_tool_results.append(tool_result)
                        
                        # Add tool result
                        new_tool_result_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })
                
                # Add new tool results to all results
                all_tool_results.extend(new_tool_results)
                
                # Add new tool results to messages
                messages.append({
                    "role": "user",
                    "content": new_tool_result_content
                })
                
                current_round += 1
            
            # Generate explanations for all options and update database
            for idx, result in enumerate(all_tool_results):
                if "error" not in result and result.get("option_id") is not None:
                    option_id = uuid.UUID(result['option_id']) if isinstance(result['option_id'], str) else result['option_id']
                    
                    # Get style/motion info
                    if result['model'] == 'text-to-image':
                        style_name = result['style']
                        style_description = result.get('style_description', '')
                    else:
                        style_name = result['motion']
                        style_description = result.get('motion_description', '')
                    
                    # Generate explanation
                    explanation = await generate_style_explanation(
                        text,  # Original user request
                        style_name,
                        style_description
                    )
                    
                    # Update Option in database with explanation and rank
                    from sqlalchemy import select
                    stmt = select(Option).where(Option.id == option_id)
                    result_obj = await db.execute(stmt)
                    option = result_obj.scalar_one_or_none()
                    
                    if option:
                        option.reason = explanation
                        option.rank = idx
                        await db.flush()
                    
                    # Add explanation to result for return value
                    result['explanation'] = explanation
                    result['advice'] = explanation
            
            await db.commit()
            
            # Build final results with initial response text if present
            final_results = []
            
            # Add initial response as introduction text if Claude provided it
            if initial_response and initial_response.strip():
                final_results.append({
                    "type": "intro_text",
                    "text": initial_response.strip(),
                    "model": "text"
                })
            
            # Add all tool results
            final_results.extend(all_tool_results)
            
            # Return combined results
            return final_results
        
        else:
            # Return empty if Claude didn't use tools (e.g., asking for clarification)
            return []
