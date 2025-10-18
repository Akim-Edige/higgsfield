"""Prompt enhancement service."""


def enhance_text_to_image(prompt: str, parameters: dict) -> tuple[str, dict]:
    """
    Enhance text-to-image prompt with style and quality keywords.
    
    Returns:
        (enhanced_prompt, updated_parameters)
    """
    # Add quality keywords
    quality_tags = ["high quality", "detailed", "sharp focus"]
    enhanced = f"{prompt}, {', '.join(quality_tags)}"
    
    # Add default negative prompt if not present
    if "negative_prompt" not in parameters:
        parameters["negative_prompt"] = "blurry, low quality, distorted, artifacts"
    
    # Ensure we have steps and cfg
    if "steps" not in parameters:
        parameters["steps"] = 20
    if "cfg" not in parameters:
        parameters["cfg"] = 7.0
    
    return enhanced, parameters


def enhance_text_to_video(prompt: str, parameters: dict) -> tuple[str, dict]:
    """
    Enhance text-to-video prompt with cinematic cues.
    
    Returns:
        (enhanced_prompt, updated_parameters)
    """
    # Add cinematic keywords
    cinematic_tags = ["cinematic", "smooth motion", "professional"]
    enhanced = f"{prompt}, {', '.join(cinematic_tags)}"
    
    # Add camera/motion hints if not present
    if "camera_motion" not in parameters:
        parameters["camera_motion"] = "static"
    
    # Ensure duration and fps
    if "duration_s" not in parameters:
        parameters["duration_s"] = 5
    if "fps" not in parameters:
        parameters["fps"] = 24
    
    return enhanced, parameters


def enhance_image_to_video(prompt: str, parameters: dict) -> tuple[str, dict]:
    """
    Enhance image-to-video prompt with motion cues.
    
    Returns:
        (enhanced_prompt, updated_parameters)
    """
    # Add motion keywords
    motion_tags = ["natural motion", "smooth animation"]
    enhanced = f"{prompt}, {', '.join(motion_tags)}" if prompt else ", ".join(motion_tags)
    
    # Ensure motion strength, duration
    if "motion_strength" not in parameters:
        parameters["motion_strength"] = 0.5
    if "duration_s" not in parameters:
        parameters["duration_s"] = 5
    if "fps" not in parameters:
        parameters["fps"] = 24
    
    return enhanced, parameters


def enhance_prompt(tool_type: str, prompt: str, parameters: dict) -> tuple[str, dict]:
    """
    Enhance prompt based on tool type.
    
    Args:
        tool_type: One of 'text_to_image', 'text_to_video', 'image_to_video', 'speak'
        prompt: Original prompt
        parameters: Original parameters dict
    
    Returns:
        (enhanced_prompt, updated_parameters)
    """
    if tool_type == "text_to_image":
        return enhance_text_to_image(prompt, parameters)
    elif tool_type == "text_to_video":
        return enhance_text_to_video(prompt, parameters)
    elif tool_type == "image_to_video":
        return enhance_image_to_video(prompt, parameters)
    else:
        # For 'speak' or unknown, return as-is
        return prompt, parameters

