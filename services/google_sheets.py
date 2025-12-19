import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
import logging
import traceback
from datetime import datetime, timedelta

class SheetManager:
    def __init__(self):
        creds_input = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not creds_input: raise ValueError("GOOGLE_CREDENTIALS_JSON missing")
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if os.path.exists(creds_input):
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_input, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_input), scope)
        self.client = gspread.authorize(creds)

    def parse_french_date(self, date_str):
        months = {'janv.':'01', 'févr.':'02', 'mars':'03', 'avr.':'04', 'mai':'05', 'juin':'06',
                  'juil.':'07', 'août':'08', 'sept.':'09', 'oct.':'10', 'nov.':'11', 'déc.':'12',
                  'janvier': '01', 'février': '02', 'avril': '04', 'juillet': '07', 'septembre': '09', 
                  'octobre': '10', 'novembre': '11', 'décembre': '12'}
        try:
            clean_str = str(date_str).lower().strip()
            if not clean_str: return None
            for fr, en in months.items():
                if fr in clean_str: clean_str = clean_str.replace(fr, en); break
            
            clean_str = clean_str.replace(',', '').replace('.', '/').replace('//', '/')
            return datetime.strptime(clean_str, "%d/%m/%Y")
        except: return None

    def get_context_data(self, sheet_key, worksheet_name=None):
        try:
            # 1. Fetch Data
            sh = self.client.open_by_key(sheet_key)
            try:
                ws = sh.worksheet("file")
            except:
                ws = sh.get_worksheet(0)

            all_values = ws.get_all_values()
            if not all_values: return {}

            # 2. Clean Headers
            headers = [str(h).strip() for h in all_values[0]]
            df = pd.DataFrame(all_values[1:], columns=headers)

            if "Date" not in df.columns:
                found_col = next((c for c in df.columns if c.lower() == 'date'), None)
                if found_col: df.rename(columns={found_col: 'Date'}, inplace=True)
                else: raise KeyError("Date column not found")

            # 3. Process Data
            df = df.replace(r'^\s*$', 0, regex=True).fillna(0)
            df['ParsedDate'] = df['Date'].apply(lambda x: self.parse_french_date(x))
            df = df.dropna(subset=['ParsedDate'])

            # --- VAMPIRE LOGIC (00:00 - 03:00 belongs to Yesterday) ---
            now = datetime.now()
            if now.hour < 3:
                # If it's 1 AM, 'today' is effectively yesterday
                today = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                logging.info(f"Vampire Logic active: Treating {now.strftime('%H:%M')} as {today.strftime('%Y-%m-%d')}")
            else:
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Filter Future Dates (Stop at the shifted 'today')
            df = df[df['ParsedDate'] <= today]

            # Numeric conversion
            skills = ['Listening', 'Speaking Practice', 'Reading', 'Writing']
            available_skills = [s for s in skills if s in df.columns]
            for col in available_skills:
                df[col] = df[col].astype(str).str.replace(',', '.').apply(lambda x: float(x) if x.replace('.','',1).isdigit() else 0)

            df['Total'] = df[available_skills].sum(axis=1)

            # --- WEEK LOGIC (Wednesday Start) ---
            # Python Weekday: Mon=0, Tue=1, Wed=2...
            # We shift so Wed=0.
            days_passed_since_wednesday = (today.weekday() - 2) % 7
            start_of_current_cycle = today - timedelta(days=days_passed_since_wednesday)
            
            # Week Totals (From Start of Cycle -> Shifted Today)
            week_df = df[df['ParsedDate'] >= start_of_current_cycle]
            week_total = week_df['Total'].sum()
            days_remaining = 6 - days_passed_since_wednesday

            # --- TREND LOGIC (Sum & Nice Labels) ---
            # 1. Shift Date (Wed -> Mon alignment for ISO grouping)
            df['ShiftedDate'] = df['ParsedDate'] - timedelta(days=2)
            
            # 2. Group by Year-Week
            grouped = df.sort_values('ParsedDate').groupby(
                [df['ShiftedDate'].dt.isocalendar().year, df['ShiftedDate'].dt.isocalendar().week]
            )['Total']

            # 3. Calculate SUM (Total hours) and get last 4
            last_4_weeks_data = grouped.sum().tail(4).values 
            
            # 4. Create nice labels
            trend_parts = []
            count = len(last_4_weeks_data)
            
            for i, val in enumerate(last_4_weeks_data):
                if i == count - 1:
                    label = "Current Week"
                else:
                    label = f"Week {i+1}"
                trend_parts.append(f"{label}: {val:.1f}h")
            
            trend_str = ", ".join(trend_parts)

            # D. DISTRIBUTION
            dist_total = week_df[available_skills].sum().sum()
            if dist_total > 0:
                dist_str = ", ".join([f"{s.split()[0]}:{int((week_df[s].sum()/dist_total)*100)}%" for s in available_skills])
            else:
                dist_str = "0%"

            # Return Dictionary
            today_row = df[df['ParsedDate'] == today]
            
            return {
                "current_time": now.strftime("%H:%M"), # Display actual wall time
                "today_total": float(today_row['Total'].sum()) if not today_row.empty else 0.0,
                "weekly_target": 14.0,
                "daily_target": 2.0,
                "days_remaining_until_the_end_of_the_week": days_remaining,
                "current_practicion": ", ".join([f"{s.split()[0]}:{today_row.iloc[0][s]}" for s in available_skills]) if not today_row.empty else "No practice yet",
                "week_total_hours": float(week_total),
                "weekly_average": float(week_total / (days_passed_since_wednesday + 1)),
                "distribution_percentages_of_last_week": dist_str,
                "trend_practice_agrage_of_last_4_weeks": trend_str
            }

        except Exception as e:
            logging.error(f"Sheet Error: {traceback.format_exc()}")
            raise e


    # --- NEW: HISTORY MANAGEMENT ---
    def _get_or_create_log_tab(self, sh):
        try:
            return sh.worksheet("logs")
        except:
            # Create if it doesn't exist
            ws = sh.add_worksheet(title="logs", rows="1000", cols="3")
            ws.append_row(["Timestamp", "Type", "Message"])
            return ws

    def get_notification_history(self, sheet_key, notif_type, limit=4):
        try:
            sh = self.client.open_by_key(sheet_key)
            ws = self._get_or_create_log_tab(sh)
            
            # Get all logs
            all_logs = ws.get_all_records() # Returns list of dicts: [{'Type': '...', 'Message': '...'}]
            
            # Filter by specific type (e.g. 'post_action')
            filtered = [row['Message'] for row in all_logs if row.get('Type') == notif_type]
            
            # Return last N messages
            return filtered[-limit:]
        except Exception as e:
            logging.error(f"History Fetch Error: {e}")
            return []

    def log_notification(self, sheet_key, notif_type, message):
        try:
            sh = self.client.open_by_key(sheet_key)
            ws = self._get_or_create_log_tab(sh)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws.append_row([timestamp, notif_type, message])
            logging.info("Notification logged to Sheet.")
        except Exception as e:
            logging.error(f"Logging Error: {e}")

            

    def get_agent_state(self, sheet_key):
        """Reads the last known state of the user's progress."""
        try:
            sh = self.client.open_by_key(sheet_key)
            try:
                ws = sh.worksheet("agent_state")
            except:
                # Create if missing
                ws = sh.add_worksheet(title="agent_state", rows="10", cols="5")
                ws.append_row(["LastRunTime", "LastDailyTotal", "LastWeeklyTotal", "DailyGoalAchieved"])
                ws.append_row(["2024-01-01 00:00:00", 0, 0, "False"])
                return {"last_daily": 0.0, "last_weekly": 0.0, "goal_achieved": False}

            # Read the second row (where data lives)
            row = ws.row_values(2)
            if not row: return {"last_daily": 0.0, "last_weekly": 0.0, "goal_achieved": False}
            
            return {
                "last_daily": float(row[1]) if len(row) > 1 else 0.0,
                "last_weekly": float(row[2]) if len(row) > 2 else 0.0,
                "goal_achieved": (str(row[3]).lower() == "true") if len(row) > 3 else False
            }
        except Exception as e:
            logging.error(f"State Read Error: {e}")
            return {"last_daily": 0.0, "last_weekly": 0.0, "goal_achieved": False}

    def update_agent_state(self, sheet_key, daily_total, weekly_total, goal_achieved):
        """Updates the state after a run."""
        try:
            sh = self.client.open_by_key(sheet_key)
            ws = sh.worksheet("agent_state")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Update row 2
            ws.update('A2:D2', [[timestamp, daily_total, weekly_total, str(goal_achieved)]])
        except Exception as e:
            logging.error(f"State Write Error: {e}")