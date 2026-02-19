"""
Google Imagen API Integration for Golf Bot Image Generation

This module provides functionality to generate custom bot images using Google's Imagen API.
"""

import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Import the official Google GenAI library
try:
    from google import genai
except ImportError:
    print("❌ google-genai library not found. Please install it with: pip install google-genai")
    raise

load_dotenv()

class GoogleImagenAPI:
    """Google Imagen API client for image generation using official google-genai library"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_IMAGEN_API_KEY")

        if not self.api_key:
            raise ValueError("GOOGLE_IMAGEN_API_KEY environment variable is required")

        # Initialize the Google GenAI client
        genai.configure(api_key=self.api_key)
        self.client = genai.Client()

    def generate_image(self, prompt: str, aspect_ratio: str = "1:1", quality: str = "standard") -> Dict[str, Any]:
        """
        Generate an image using Google Imagen API

        Args:
            prompt: Text description of the image to generate
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            quality: Image quality (standard, hd)

        Returns:
            Dict containing the generated image data and metadata
        """
        try:
            # Map aspect ratios to Imagen format
            aspect_ratio_map = {
                "1:1": "1:1",
                "16:9": "16:9",
                "9:16": "9:16",
                "4:3": "4:3",
                "3:4": "3:4"
            }

            # Map quality to Imagen format
            quality_map = {
                "standard": "standard",
                "hd": "hd"
            }

            # Generate the image using the official client
            image = self.client.models.generate_images(
                model="imagen-4.0-generate-preview-06-06",
                prompt=prompt,
                aspect_ratio=aspect_ratio_map.get(aspect_ratio, "1:1"),
                quality=quality_map.get(quality, "standard")
            )

            if image.generated_images:
                generated_image = image.generated_images[0]

                return {
                    "success": True,
                    "data": generated_image.image.image_bytes,
                    "image_data": generated_image.image.image_bytes,
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "quality": quality,
                    "bytes_used": len(generated_image.image.image_bytes)
                }
            else:
                return {
                    "success": False,
                    "error": "No images were generated",
                    "prompt": prompt
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Image generation failed: {str(e)}",
                "prompt": prompt
            }

    def save_image_to_file(self, image_data: Dict[str, Any], filename: str) -> bool:
        """
        Save generated image data to a file

        Args:
            image_data: Image data from generate_image response
            filename: Output filename

        Returns:
            True if successful, False otherwise
        """
        try:
            if not image_data.get("success") or "data" not in image_data:
                print("❌ No image data to save")
                return False

            # Save the image bytes directly
            with open(filename, "wb") as f:
                f.write(image_data["data"])

            print(f"✅ Image saved to {filename} ({image_data.get('bytes_used', 0)} bytes)")
            return True

        except Exception as e:
            print(f"❌ Error saving image: {e}")
            return False


def test_imagen_api_basic():
    """Basic test of Google Imagen API functionality"""
    print("🧪 Testing Google Imagen API - Basic Functionality")
    print("=" * 50)

    try:
        # Initialize API client
        imagen = GoogleImagenAPI()
        print("✅ API client initialized successfully")

        # Test prompt for golf bot
        test_prompt = "A friendly cartoon golfer character with a golf club, wearing a golf hat, digital art style"

        print(f"🎨 Generating image with prompt: '{test_prompt}'")

        # Generate image
        result = imagen.generate_image(
            prompt=test_prompt,
            aspect_ratio="1:1",
            quality="standard"
        )

        if result["success"]:
            print("✅ Image generation successful!")
            print(f"📊 Bytes generated: {result.get('bytes_used', 0)}")

            # Try to save the image
            filename = "test_golf_bot_image.png"
            if imagen.save_image_to_file(result, filename):
                print(f"💾 Image saved as {filename}")
            else:
                print("⚠️ Could not save image to file")

        else:
            print(f"❌ Image generation failed: {result['error']}")

        return result

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return None


def test_imagen_api_multiple_prompts():
    """Test multiple different prompts for variety"""
    print("\n🧪 Testing Google Imagen API - Multiple Prompts")
    print("=" * 50)

    try:
        imagen = GoogleImagenAPI()

        test_prompts = [
            "A professional golfer in a green polo shirt, confident pose, realistic style",
            "A cartoon golf ball with a happy face, simple design, white background",
            "A golf course landscape with rolling hills and trees, watercolor style",
            "A golf club and ball on a green, minimalist design"
        ]

        results = []

        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🎨 Test {i}: {prompt}")

            result = imagen.generate_image(
                prompt=prompt,
                aspect_ratio="1:1",
                quality="standard"
            )

            if result["success"]:
                print(f"✅ Test {i} successful ({result.get('bytes_used', 0)} bytes)")
                filename = f"test_image_{i}.png"
                imagen.save_image_to_file(result, filename)
            else:
                print(f"❌ Test {i} failed: {result['error']}")

            results.append(result)

        return results

    except Exception as e:
        print(f"❌ Multiple prompts test failed: {e}")
        return None


def test_imagen_api_aspect_ratios():
    """Test different aspect ratios"""
    print("\n🧪 Testing Google Imagen API - Different Aspect Ratios")
    print("=" * 50)

    try:
        imagen = GoogleImagenAPI()

        aspect_ratios = ["1:1", "16:9", "9:16", "4:3"]
        prompt = "A golf ball on a green, simple design"

        results = []

        for aspect_ratio in aspect_ratios:
            print(f"\n📐 Testing aspect ratio: {aspect_ratio}")

            result = imagen.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                quality="standard"
            )

            if result["success"]:
                print(f"✅ {aspect_ratio} successful ({result.get('bytes_used', 0)} bytes)")
                filename = f"test_aspect_{aspect_ratio.replace(':', 'x')}.png"
                imagen.save_image_to_file(result, filename)
            else:
                print(f"❌ {aspect_ratio} failed: {result['error']}")

            results.append(result)

        return results

    except Exception as e:
        print(f"❌ Aspect ratios test failed: {e}")
        return None


def test_imagen_api_error_handling():
    """Test error handling with invalid inputs"""
    print("\n🧪 Testing Google Imagen API - Error Handling")
    print("=" * 50)

    try:
        imagen = GoogleImagenAPI()

        # Test with empty prompt
        print("🔍 Testing empty prompt...")
        result = imagen.generate_image("")
        print(f"Empty prompt result: {'Success' if result['success'] else 'Failed'}")

        # Test with very long prompt
        print("🔍 Testing very long prompt...")
        long_prompt = "A " + "very " * 100 + "long prompt that might exceed limits"
        result = imagen.generate_image(long_prompt)
        print(f"Long prompt result: {'Success' if result['success'] else 'Failed'}")

        # Test with invalid aspect ratio
        print("🔍 Testing invalid aspect ratio...")
        result = imagen.generate_image("A golf ball", aspect_ratio="invalid")
        print(f"Invalid aspect ratio result: {'Success' if result['success'] else 'Failed'}")

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")


def generate_bot_image_prompt(bot_name: str, description: str, difficulty: str) -> str:
    """
    Generate an optimized prompt for bot image generation

    Args:
        bot_name: Name of the bot
        description: Bot personality description
        difficulty: Bot difficulty level

    Returns:
        Optimized prompt for image generation
    """
    # Base prompt structure
    base_prompt = f"A character portrait of {bot_name}, "

    # Add personality traits from description
    personality_keywords = []
    description_lower = description.lower()

    if "friendly" in description_lower or "nice" in description_lower:
        personality_keywords.append("friendly expression")
    if "serious" in description_lower or "professional" in description_lower:
        personality_keywords.append("serious expression")
    if "funny" in description_lower or "humorous" in description_lower:
        personality_keywords.append("amused expression")
    if "competitive" in description_lower or "intense" in description_lower:
        personality_keywords.append("determined expression")

    # Add difficulty-based styling
    if difficulty == "easy":
        style = "cartoon style, simple design, bright colors"
    elif difficulty == "medium":
        style = "semi-realistic style, balanced design"
    elif difficulty == "hard":
        style = "realistic style, professional appearance"
    else:
        style = "digital art style"

    # Combine all elements
    prompt = base_prompt + ", ".join(personality_keywords) + f", {style}, golf-themed character, portrait format"

    return prompt


def test_bot_image_generation():
    """Test bot image generation with sample bot data"""
    print("\n🧪 Testing Bot Image Generation")
    print("=" * 50)

    try:
        imagen = GoogleImagenAPI()

        # Sample bot data
        test_bots = [
            {
                "name": "Tiger Woods",
                "description": "Professional golfer with competitive spirit and serious demeanor",
                "difficulty": "hard"
            },
            {
                "name": "Happy Gilmore",
                "description": "Funny and enthusiastic golfer with a big personality",
                "difficulty": "medium"
            },
            {
                "name": "Golf Pro",
                "description": "Friendly and encouraging golf instructor",
                "difficulty": "easy"
            }
        ]

        results = []

        for i, bot in enumerate(test_bots, 1):
            print(f"\n🤖 Generating image for {bot['name']}...")

            # Generate optimized prompt
            prompt = generate_bot_image_prompt(
                bot["name"],
                bot["description"],
                bot["difficulty"]
            )

            print(f"🎨 Prompt: {prompt}")

            # Generate image
            result = imagen.generate_image(
                prompt=prompt,
                aspect_ratio="1:1",
                quality="standard"
            )

            if result["success"]:
                print(f"✅ {bot['name']} image generated successfully ({result.get('bytes_used', 0)} bytes)")
                filename = f"bot_{bot['name'].replace(' ', '_').lower()}.png"
                imagen.save_image_to_file(result, filename)
            else:
                print(f"❌ {bot['name']} failed: {result['error']}")

            results.append(result)

        return results

    except Exception as e:
        print(f"❌ Bot image generation test failed: {e}")
        return None


if __name__ == "__main__":
    """Run all tests when script is executed directly"""
    print("🚀 Starting Google Imagen API Tests")
    print("=" * 60)

    # Check if API key is available
    if not os.getenv("GOOGLE_IMAGEN_API_KEY"):
        print("❌ GOOGLE_IMAGEN_API_KEY environment variable not found!")
        print("Please set your Google Imagen API key in your .env file")
        exit(1)

    # Run tests
    test_imagen_api_basic()
    test_imagen_api_multiple_prompts()
    test_imagen_api_aspect_ratios()
    test_imagen_api_error_handling()
    test_bot_image_generation()

    print("\n🎉 All tests completed!")
