import google.generativeai as genai
import os
import json
import logging

# --- CONFIGURATION ---
SYSTEM_PROMPT = """
You are "Chaos Coach," a hyper-aware, slightly unhinged AI accountability partner.
Your Goal: Hack the user's dopamine system to maximize English learning.

TONE GUIDELINES:
1. Be unpredictable: Switch between aggressive drill sergeant, supportive best friend, and existential philosopher.
2. Use Internet Slang: (e.g., "no cap," "main character energy," "cooked", "segfault").
3. Be Data-Obsessed: Reference the specific numbers in the context.

FORMATTING RULES (CRITICAL):
- OUTPUT MUST BE A SINGLE TEXT MESSAGE.
- MAX 280 CHARACTERS.
- NO Markdown headers (##).
- NO Bullet points.
- NO "Here is your analysis" intros. Just the message.
- ALWAYS include at least one joke or meme reference to AI or her age or name.
- Be creative and funny and DONT repeat the same joke twice.
"""

PROMPTS = {
    "pre_action": """
    CONTEXT DATA:
    {data_json}

    MISSION:
    The user has done 0 hours today and is behind schedule.
    Generate a single, panic-inducing text message.
    - Mention they only have {days_remaining_until_the_end_of_the_week} days left to hit the {weekly_target}h target.
    - Identify the lowest skill in 'current_practicion'.
    - COMMAND them to do 15 mins of that skill immediately. 
    - Be aggressive but funny.
    """,

    "post_action": """
    CONTEXT DATA:
    {data_json}

    MISSION:
    The user just finished practicing. Generate a specific reaction text.
    - If 'today_total' > 'daily_target': Hype them up ("Main character energy").
    - If 'today_total' < 'daily_target': Tell them exactly how much is left to survive.
    - CRITICAL: Look at 'current_practicion'. If they are ignoring Writing/Speaking, roast them for "farming low-XP mobs" (Reading/Listening).
    - Keep it under 50 words.
    """,

    "weekly_summary": """
    CONTEXT DATA:
    {data_json}

    MISSION:
    Weekly Review. Generate a short, punchy summary.
    - Compare 'current_week' in 'trend_practice_agrage' to previous weeks. If up, say "Evolving." If down, say "Flopped."
    - Call out the 'distribution' IMBALANCE (especially if Speaking is 0%).
    - Give a "Weird Challenge" for next week (e.g., talk to a toaster).
    - Do NOT list stats. Weave them into the roast.
    """
}

class ChaosCoachAgent:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key: raise ValueError("GEMINI_API_KEY missing")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-flash-lite-latest', system_instruction=SYSTEM_PROMPT)

    def generate_notification(self, notif_type, context_data, history_list):
        if notif_type not in PROMPTS:
            return "Error: Invalid notification type requested."

        # Format Data
        data_json = json.dumps(context_data, indent=2)
        
        # Format History (Join the list into a readable string)
        if history_list:
            history_str = "\n".join([f"- {msg}" for msg in history_list])
        else:
            history_str = "(No past messages yet)"

        # Hydrate Prompt
        try:
            user_prompt = PROMPTS[notif_type].format(
                data_json=data_json, 
                history=history_str, 
                **context_data
            )
        except KeyError as e:
            # Fallback if a key is missing
            logging.warning(f"Missing key: {e}")
            user_prompt = PROMPTS[notif_type].replace("{data_json}", data_json).replace("{history}", history_str)

        try:
            response = self.model.generate_content(user_prompt)
            return response.text.strip()
        except Exception as e:
            logging.error(f"Gemini Error: {e}")
            return "Chaos Coach error. Just go study."