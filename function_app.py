import azure.functions as func
import logging
from services.google_sheets import SheetManager
from services.ai_agent import ChaosCoachAgent
from services.discord_bot import DiscordNotifier
from datetime import datetime
import os

app = func.FunctionApp()

# CRON EXPLAINED: "0 0 17,19,21,23,1,3 * * *"
# Runs at minute 0, hour 17, 19, 21, 23 (PM) and 01, 03 (AM)
# This covers your "17:00 to 03:00 every 2h" requirement.
@app.schedule(schedule="0 0 17,19,21,23,1 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def DailyCheckIn(myTimer: func.TimerRequest) -> None:
    logging.info('Chaos Coach triggered.')

    try:
        sheet_manager = SheetManager()
        SHEET_KEY = os.environ.get("SHEET_KEY")
        
        # 1. GET CURRENT DATA & PREVIOUS STATE
        context_data = sheet_manager.get_context_data(SHEET_KEY)
        state = sheet_manager.get_agent_state(SHEET_KEY)
        
        current_daily = context_data.get('today_total', 0.0)
        current_weekly = context_data.get('week_total_hours', 0.0)
        daily_target = context_data.get('daily_target', 2.0)
        weekly_target = context_data.get('weekly_target', 14.0)
        
        now = datetime.now()
        # Tuesday is weekday 1. 3 AM check.
        is_tuesday_morning = (now.weekday() == 1 and now.hour == 1)
        
        # LOGIC FLAGS
        has_progressed = current_daily > state['last_daily']
        goal_just_met = (current_daily >= daily_target) and (not state['goal_achieved'])
        already_done_for_day = state['goal_achieved'] and (not has_progressed) # If done and no new movement

        notif_type = None
        should_send = False

        # --- RULE 1: WEEKLY CHECK (High Priority) ---
        if is_tuesday_morning or (current_weekly >= weekly_target and state['last_weekly'] < weekly_target):
            notif_type = "weekly_summary"
            should_send = True

        # --- RULE 2: DAILY GOAL MET (Stop for day) ---
        elif goal_just_met:
            notif_type = "post_action" # Or a special "goal_met" prompt if you want
            should_send = True
            # Note: We will save 'goal_achieved=True' so next runs stay silent

        # --- RULE 3: POST-ACTION (Progress Detected) ---
        elif has_progressed:
            notif_type = "post_action"
            should_send = True

        # --- RULE 4: PRE-ACTION (No Progress & Not Done Yet) ---
        elif not has_progressed and not state['goal_achieved']:
            notif_type = "pre_action"
            should_send = True

        # --- EXECUTION ---
        if should_send and notif_type:
            # 1. Get History
            history = sheet_manager.get_notification_history(SHEET_KEY, notif_type)
            
            # 2. Generate
            agent = ChaosCoachAgent()
            message = agent.generate_notification(notif_type, context_data, history)
            
            # 3. Send
            notifier = DiscordNotifier()
            notifier.send_notification(message)
            
            # 4. Log Message
            sheet_manager.log_notification(SHEET_KEY, notif_type, message)
            logging.info(f"Sent {notif_type}: {message}")
        else:
            logging.info("Skipping notification (Goal met or no relevant trigger).")

        # --- SAVE NEW STATE ---
        # If we just met the goal, mark True. 
        # Crucial: Reset 'goal_achieved' to False if it's a new day (Current Daily < Last Daily usually implies reset, 
        # but logic is tricky. Simplest: The sheet calculation returns 0 for a new day, so current_daily (0) < target (2) -> False)
        
        new_goal_status = (current_daily >= daily_target)
        sheet_manager.update_agent_state(SHEET_KEY, current_daily, current_weekly, new_goal_status)

    except Exception as e:
        logging.error(f"Workflow failed: {e}")