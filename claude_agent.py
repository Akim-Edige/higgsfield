"""
Claude Agent for working with LLM and generating videos/images
Using Claude 3.5 Haiku via Anthropic API
"""
import json
import uuid
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import os

import anthropic
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from models import Option, Message
from base import get_db
load_dotenv()
# Get API key from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("⚠️  Warning: ANTHROPIC_API_KEY not found in environment variables")
    print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")

# Initialize Anthropic client
claude_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


# Load styles and motions data
with open("image_styles.json", "r", encoding="utf-8") as f:
    IMAGE_STYLES = json.load(f)

with open("motions.json", "r", encoding="utf-8") as f:
    MOTIONS = json.load(f)


# Generate tools for Claude (without metadata field)
def generate_claude_tools() -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Generates tools for Claude API and creates a mapping for metadata
    Returns: (tools_list, tool_name_to_metadata_mapping)
    """
    tools = []
    metadata_mapping = {}
    
    def sanitize_tool_name(name: str) -> str:
        """Sanitize tool name to match pattern ^[a-zA-Z0-9_-]{1,128}$"""
        # Replace spaces and special chars with underscore
        sanitized = name.lower()
        sanitized = ''.join(c if c.isalnum() or c in '_-' else '_' for c in sanitized)
        # Remove consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Limit to 128 chars
        return sanitized[:100]  # Leave room for prefix
    
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
        
        # Store metadata separately
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
        
        # Store metadata separately
        metadata_mapping[tool_name] = {
            "motion_id": motion_id,
            "motion_name": motion_name,
            "model_type": "image-to-video",
            "description": motion_description,
            "start_end_frame": motion.get("start_end_frame", False)
        }
    
    return tools, metadata_mapping


# Generate tools and metadata mapping
CLAUDE_TOOLS, TOOL_METADATA = generate_claude_tools()
print(f"✓ Generated {len(CLAUDE_TOOLS)} tools for Claude")
print(f"✓ Created metadata mapping for {len(TOOL_METADATA)} tools")


# System prompt for Claude
SYSTEM_PROMPT = """You are an intelligent assistant for video and image generation on the Higgsfield AI platform.

Your main task is to help users choose the right style and model to create visual content.

IMPORTANT WORKFLOW:
1. Analyze user's request carefully
2. Select most relevant styles/effects from available tools
3. For EACH recommended style, you must:
   a) ALWAYS Explain why this style suits the user's request 
   b) IMMEDIATELY call the corresponding tool for that style
   c) The tool will return option_id and message_id

4. Present your recommendations in this format:

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
    """
    Enhances user's prompt using Claude with style description
    """
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
        messages=[
            {
                "role": "user",
                "content": enhancement_prompt
            }
        ]
    )
    
    return message.content[0].text.strip()


async def generate_style_explanation(
    user_request: str,
    style_name: str,
    style_description: str
) -> str:
    """
    Generate explanation why this style was chosen for the user's request
    """
    explanation_prompt = f"""You are explaining to a user why you chose a specific style for their image/video request.

User's request: {user_request}
Style chosen: {style_name}
Style description: {style_description}

Write a brief, friendly advice about why this style fits their request perfectly. 
Focus on:
- How it matches their vision
- Key visual characteristics that align with their needs
- What makes this style special for their use case

Be conversational and helpful. Return ONLY the explanation text, no headers or formatting."""

    message = await claude_client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": explanation_prompt
            }
        ]
    )
    
    return message.content[0].text.strip()


async def create_option_in_background(
    message_id: uuid.UUID,
    style_id: str,
    user_prompt: str,
    model_type: str,
    style_name: str,
    style_description: str,
    db: Session
):
    """
    Background task for creating Option with enhanced prompt (explanation will be added later)
    """
    try:
        # Enhance prompt
        enhanced_prompt = await enhance_prompt_with_claude(user_prompt, style_description)
        
        # Create Option in database WITHOUT explanation (will be updated later)
        option = Option(
            id=uuid.uuid4(),
            message_id=message_id,
            prompt=enhanced_prompt,
            model=model_type,
            style=style_name,
            explanation=None,  # Will be filled later
            result_url=None
        )
        
        db.add(option)
        db.commit()
        
        print(f"✓ Option created: {option.id}")
        print(f"   Enhanced prompt ({len(enhanced_prompt)} chars): {enhanced_prompt}")
        
        return str(option.id)
        
    except Exception as e:
        print(f"Error creating option: {e}")
        db.rollback()
        return None


async def execute_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    message_id: uuid.UUID,
    db: Session
) -> Dict[str, Any]:
    """
    Executes tool call and launches background task
    Uses metadata mapping instead of tool.metadata
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


async def chat_with_claude(
    user_message: str,
    message_id: uuid.UUID,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    db: Session = None
) -> str:
    """
    Main function for communicating with Claude via Anthropic API with tools support
    """
    if chat_history is None:
        chat_history = []
    
    # Build messages for Claude
    messages = chat_history.copy()
    messages.append({
        "role": "user",
        "content": user_message
    })
    
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
            
            print(f"🔧 Executing tool: {tool_name}")
            print(f"   Input: {tool_input}")
            
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
            print(f"🔄 Claude requested more tools (round {current_round + 1})")
            
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
                    
                    print(f"🔧 Executing tool: {tool_name}")
                    print(f"   Input: {tool_input}")
                    
                    # Execute tool
                    tool_result = await execute_tool(tool_name, tool_input, message_id, db)
                    new_tool_results.append(tool_result)
                    
                    if "option_id" in tool_result:
                        print(f"✓ Option created: {tool_result['option_id']}")
                    
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
        print("\n📝 Generating explanations for all options...")
        for result in all_tool_results:
            if "error" not in result and "option_id" in result:
                option_id = uuid.UUID(result['option_id'])  # Convert string to UUID
                
                # Get style/motion info
                if result['model'] == 'text-to-image':
                    style_name = result['style']
                    style_description = result.get('style_description', '')
                else:
                    style_name = result['motion']
                    style_description = result.get('motion_description', '')
                
                # Generate explanation
                explanation = await generate_style_explanation(
                    user_message,  # Original user request
                    style_name,
                    style_description
                )
                
                # Update Option in database with explanation
                option = db.query(Option).filter_by(id=option_id).first()
                if option:
                    option.explanation = explanation
                    db.commit()
                    print(f"✓ Added explanation for {style_name}: {explanation[:100]}...")
                
                # Add explanation to result for JSON output
                result['explanation'] = explanation
        
        # Format the response with IDs
        formatted_response = initial_response
        
        # Add all tool results to the response in JSON format
        if all_tool_results:
            formatted_response += "\n\n---\n**Generated Options:**\n\n```json\n"
            
            # Create JSON structure
            options_json = []
            for result in all_tool_results:
                if "error" not in result:
                    if result['model'] == 'text-to-image':
                        options_json.append({
                            "style": result['style'],
                            "style_id": result['style_id'],
                            "option_id": result['option_id'],
                            "message_id": result['message_id'],
                            "model": result['model'],
                            "explanation": result.get('explanation', '')
                        })
                    else:
                        options_json.append({
                            "motion": result['motion'],
                            "motion_id": result['motion_id'],
                            "option_id": result['option_id'],
                            "message_id": result['message_id'],
                            "model": result['model'],
                            "explanation": result.get('explanation', '')
                        })
            
            # Format as pretty JSON
            formatted_response += json.dumps(options_json, indent=2, ensure_ascii=False)
            formatted_response += "\n```"
        
        # Add final Claude response if there's any additional text
        if final_text and final_text != initial_response:
            formatted_response += f"\n\n{final_text}"
        
        return formatted_response
    
    else:
        # Return regular response without tool calls
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text
        
        return response_text if response_text else "Sorry, couldn't get a response."


# Function to get information about available styles and motions
def get_available_styles_summary() -> str:
    """Returns brief information about available styles"""
    styles_summary = f"Available: {len(IMAGE_STYLES)} image styles and {len(MOTIONS)} video effects.\n\n"
    
    styles_summary += "Example image styles:\n"
    for style in IMAGE_STYLES[:5]:
        styles_summary += f"- {style['name']}: {style['description']}\n"
    
    styles_summary += "\nExample video effects:\n"
    for motion in MOTIONS[:5]:
        styles_summary += f"- {motion['name']}: {motion['description']}\n"
    
    return styles_summary


if __name__ == "__main__":
    # Test run
    print("🤖 Claude Agent started!")
    print(get_available_styles_summary())
    
    # Usage example
    async def test():
        from base import SessionLocal
        
        # Check API key
        if not ANTHROPIC_API_KEY:
            print("❌ Error: ANTHROPIC_API_KEY not found in environment variables")
            print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
            return
        
        db = SessionLocal()
        
        # Create test message
        test_message_id = uuid.uuid4()
        
        user_input = "I want to create a photo in 90s style with retro effect"
        print(f"\n👤 User: {user_input}")
        
        response = await chat_with_claude(
            user_message=user_input,
            message_id=test_message_id,
            db=db
        )
        
        print(f"\n🤖 Claude: {response}")
        
        db.close()
    
    asyncio.run(test())
