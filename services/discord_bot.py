import requests
import os
import logging

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    def send_notification(self, message):
        if not self.webhook_url:
            logging.error("Discord Webhook URL not set.")
            return

        payload = {"content": message}
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logging.info("Notification sent to Discord!")
        except Exception as e:
            logging.error(f"Failed to send Discord message: {e}")