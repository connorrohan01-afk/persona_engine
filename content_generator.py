import json
import os
from datetime import datetime
from openai import OpenAI

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = None

def get_openai_client():
    global openai_client
    if openai_client is None and OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return openai_client


class ContentGenerator:
    def __init__(self):
        self.client = get_openai_client()
        if self.client is None:
            print("Warning: OpenAI API key not set. Content generation will not work.")
            self.client = None
    
    def generate_content(self, template, platform, topic=None, tone=None, length=None):
        """
        Generate content based on template and parameters
        """
        try:
            # Build the prompt based on template and parameters
            prompt = self._build_prompt(template, platform, topic, tone, length)
            
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional content creator specializing in social media and marketing content. "
                                 "Generate engaging, platform-appropriate content based on the given template and parameters. "
                                 "Respond with JSON in this format: {'title': 'string', 'content': 'string', 'hashtags': ['array of strings']}"
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "title": result.get("title", "Generated Content"),
                "content": result.get("content", ""),
                "hashtags": result.get("hashtags", []),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Failed to generate content: {str(e)}")
    
    def _build_prompt(self, template, platform, topic=None, tone=None, length=None):
        """
        Build the generation prompt based on parameters
        """
        prompt = f"Create content for {platform} using this template: {template}\n\n"
        
        if topic:
            prompt += f"Topic/Subject: {topic}\n"
        
        if tone:
            prompt += f"Tone: {tone}\n"
        
        if length:
            prompt += f"Desired length: {length}\n"
        
        prompt += f"\nPlatform-specific requirements for {platform}:\n"
        
        # Platform-specific guidelines
        platform_guidelines = {
            "twitter": "Keep it concise (under 280 characters), use relevant hashtags, engaging and shareable",
            "facebook": "Engaging and conversational, can be longer form, encourage interaction",
            "instagram": "Visual-friendly, use emojis, include relevant hashtags, storytelling approach",
            "linkedin": "Professional tone, industry insights, thought leadership, networking focus",
            "blog": "Comprehensive, informative, well-structured with headings and subheadings"
        }
        
        prompt += platform_guidelines.get(platform.lower(), "Create engaging, platform-appropriate content")
        
        return prompt
    
    def improve_content(self, existing_content, improvement_type="general"):
        """
        Improve existing content based on improvement type
        """
        try:
            improvement_prompts = {
                "engagement": "Make this content more engaging and interactive",
                "seo": "Optimize this content for SEO and searchability",
                "tone": "Improve the tone and voice of this content",
                "clarity": "Make this content clearer and more concise",
                "general": "Improve this content overall for better performance"
            }
            
            prompt = f"{improvement_prompts.get(improvement_type, improvement_prompts['general'])}:\n\n{existing_content}"
            
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a content optimization expert. Improve the given content while maintaining its core message. "
                                 "Respond with JSON in this format: {'improved_content': 'string', 'changes_made': ['array of improvements']}"
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            raise Exception(f"Failed to improve content: {str(e)}")
    
    def generate_hashtags(self, content, platform, count=5):
        """
        Generate relevant hashtags for content
        """
        try:
            prompt = f"Generate {count} relevant and trending hashtags for this {platform} content:\n\n{content}"
            
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a social media hashtag expert. Generate relevant, trending hashtags. "
                                 "Respond with JSON in this format: {'hashtags': ['array of hashtag strings without # symbol']}"
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("hashtags", [])
            
        except Exception as e:
            return []


# Initialize global content generator lazily
content_generator = None

def get_content_generator():
    global content_generator
    if content_generator is None:
        content_generator = ContentGenerator()
    return content_generator
