# 🤖 Serverless AI Chaos Coach

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Azure Functions](https://img.shields.io/badge/Azure_Functions-Serverless-0078D4?logo=azure-functions&logoColor=white)
![Gemini AI](https://img.shields.io/badge/AI-Gemini_1.5_Flash-8E75B2?logo=google-gemini&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Database-Google_Sheets-34A853?logo=google-sheets&logoColor=white)

> **"Not just a tracker. An active agent that holds you accountable."**

## 📖 Overview

The **Serverless AI Chaos Coach** is a context-aware notification agent designed to enforce language learning habits. Unlike passive apps that just visualize data, this agent **actively monitors** my daily logs, calculates complex trends in real-time, and uses a Large Language Model (LLM) to send personalized, "Chaos Coach" persona notifications via Discord.

It runs autonomously on **Azure Functions**, handles state persistence via Google Sheets, and features custom "Vampire Mode" logic for late-night study sessions.

---

## 🚀 Key Features

* **🧠 Context-Aware AI:** Uses **Google Gemini** to generate unique, non-repetitive messages. It knows if I'm "farming low-XP mobs" (ignoring difficult skills) or "cooking" (exceeding targets).
* **💾 State Persistence:** The agent remembers the previous run's data. It only notifies me if *new* progress is detected or if a specific "panic" threshold is met.
* **🧛 Vampire Mode Logic:** Custom algorithm that shifts the "day" boundary. Studying at 02:00 AM counts towards "Yesterday's" goal, preventing false panic alerts after midnight.
* **📅 Custom Cycle Support:** Handles non-standard weekly cycles (e.g., Wednesday to Tuesday) for trend calculation.
* **🗣️ Memory:** The agent reads its own past messages to avoid repeating jokes or advice.

---

## 🛠️ Architecture

The system follows an **Event-Driven Serverless Architecture**:

1.  **Trigger:** Azure Timer Trigger wakes up every 2 hours (17:00 - 01:00).
2.  **Data Engine:** Python scripts fetch raw logs from a Google Sheet and calculate live metrics (Sums, Trends, Distributions).
3.  **State Check:** Compares current metrics vs. the stored "Agent State" (hidden sheet tab).
4.  **Decision Engine:**
    * *Has progress made?* -> **Post-Action** (Reward/Roast).
    * *No progress & deadline near?* -> **Pre-Action** (Panic).
    * *Cycle end?* -> **Weekly Review**.
5.  **Generation:** Gemini generates the message based on the specific `context_data`.
6.  **Delivery:** Discord Webhook pushes the notification.

---

## 💻 Tech Stack

* **Runtime:** Python 3.12
* **Cloud:** Azure Functions (Linux Consumption Plan)
* **AI Model:** Google Gemini 1.5 Flash (via `google-genai` SDK)
* **Database:** Google Sheets API (via `gspread` & `pandas`)
* **Notification:** Discord Webhooks

---

## ⚙️ Installation & Setup

### 1. Prerequisites
* Python 3.10+
* Azure CLI & Azure Functions Core Tools
* Google Cloud Service Account (JSON key)

### 2. Local Run
```bash
# Clone the repo
git clone [https://github.com/YOUR_USERNAME/Serverless-AI-Coach.git](https://github.com/YOUR_USERNAME/Serverless-AI-Coach.git)
cd Serverless-AI-Coach

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create local settings (NOT committed to Git)
touch local.settings.json
```

**Content of `local.settings.json`:**
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "GEMINI_API_KEY": "your_gemini_key",
    "DISCORD_WEBHOOK_URL": "your_discord_url",
    "GOOGLE_CREDENTIALS_JSON": "path/to/your/service_account.json",
    "GOOGLE_SHEET_KEY": "your_sheet_id",
    "TZ": "Africa/Tunis"
  }
}
```

### 3. Run
```bash
func start
```

---

## ☁️ Deployment

Deployed to Azure using the CLI:

```bash
# 1. Create Resource Group & Storage
az group create --name MyResourceGroup --location westeurope
az storage account create --name mystorage --resource-group MyResourceGroup ...

# 2. Create Function App
az functionapp create --name MyChaosCoach ... --runtime python --runtime-version 3.12 ...

# 3. Set Secrets (Production)
az functionapp config appsettings set --name MyChaosCoach --settings "GEMINI_API_KEY=..." "TZ=Africa/Tunis" ...

# 4. Deploy
func azure functionapp publish MyChaosCoach --build remote
```

---

## 📈 Future Improvements
* [ ] Add "Streak Freeze" logic.
* [ ] Two-way interaction (Chat with the bot via Discord).
* [ ] Dashboard visualization using Streamlit.

---

**Author:** [Mohamed Amine Ouni]
**License:** MIT
