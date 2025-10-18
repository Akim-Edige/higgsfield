"""
Generate tools from image_styles.json and motions.json
"""
import json

# Load styles and motions data
with open("image_styles.json", "r", encoding="utf-8") as f:
    IMAGE_STYLES = json.load(f)

with open("motions.json", "r", encoding="utf-8") as f:
    MOTIONS = json.load(f)

print("=" * 80)
print("🔧 GENERATING TOOLS")
print("=" * 80)

tools = []

# Create tools for each image style
print(f"\n📝 Processing {len(IMAGE_STYLES)} image styles...")
for style in IMAGE_STYLES:
    style_id = style["id"]
    style_name = style["name"]
    style_description = style.get("description", "")
    
    tool = {
        "type": "function",
        "function": {
            "name": f"create_image_style_{style_name.lower().replace(' ', '_').replace('-', '_')}",
            "description": f"Creates an image in '{style_name}' style. {style_description}",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "User's image description"
                    }
                },
                "required": ["user_prompt"]
            },
            "metadata": {
                "style_id": style_id,
                "style_name": style_name,
                "model_type": "text-to-image",
                "description": style_description
            }
        }
    }
    tools.append(tool)

# Create tools for each video effect
print(f"📝 Processing {len(MOTIONS)} video motions...")
for motion in MOTIONS:
    motion_id = motion["id"]
    motion_name = motion["name"]
    motion_description = motion.get("description", "")
    
    tool = {
        "type": "function",
        "function": {
            "name": f"create_video_motion_{motion_name.lower().replace(' ', '_').replace('-', '_')}",
            "description": f"Creates a video with '{motion_name}' effect. {motion_description}",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "User's video description"
                    }
                },
                "required": ["user_prompt"]
            },
            "metadata": {
                "motion_id": motion_id,
                "motion_name": motion_name,
                "model_type": "image-to-video",
                "description": motion_description,
                "start_end_frame": motion.get("start_end_frame", False)
            }
        }
    }
    tools.append(tool)

# Save to file
with open("tools_export.json", "w", encoding="utf-8") as f:
    json.dump(tools, f, indent=2, ensure_ascii=False)

print(f"\n✅ SUCCESS!")
print("=" * 80)
print(f"Generated {len(tools)} tools:")
print(f"  - {len(IMAGE_STYLES)} image style tools")
print(f"  - {len(MOTIONS)} video motion tools")
print(f"\n💾 Saved to: tools_export.json")
print("=" * 80)
