# 🌌 Nova Conversation (v1.1.0)
**The high-performance bridge for Local & Cloud AI in Home Assistant.**

### 🚀 A Community Revival 
Huge thanks to [Michelle Avery](https://github.com/michelle-avery) for the original project. This fully rewritten architecture brings the integration up to 2026.1+ standards, focusing on speed, reliability, and native multimodal support.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Maintained](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/DonTranQuiL/nova_conversation/commits/main)

Bring the power of advanced Language Models to Home Assistant. Nova doesn't just chat—it physically controls your smart home, generates images, and now **analyzes your camera feeds in real-time**.

---

## 🌟 What's New in v1.1.0: "Nova Vision"
The latest update introduces **Multimodal Image Analysis**. Nova can now "see" your home by analyzing live snapshots from your Home Assistant cameras.

* **`analyze_camera` Service:** Send live camera frames to Vision-capable models (like GPT-4o or Claude 3.5).
* **Contextual Automations:** Use AI descriptions to power smart notifications (e.g., "There is a delivery driver at the door").
* **Modular Multi-Agent Support:** Run a fast local model (like a 20b) for voice commands while keeping a high-end Vision agent on standby for analysis.

---

## 🚀 Installation & Setup

1.  Copy the `nova_conversation` folder into your `custom_components` directory.
2.  Restart Home Assistant.
3.  Go to **Settings > Devices & Services > Add Integration**.
4.  Search for **Nova Conversation**.
5.  Enter your **API Key** and **Base URL** (e.g., `https://openrouter.ai/api/v1`).
6.  Go to the integration **Configure** menu. Uncheck "Recommended" and click submit to reveal advanced options.

---

## 📖 Tutorial: How Nova Vision Works
Nova allows you to pick the right AI for the right job. You can create multiple instances of Nova to balance cost and performance.

### 1. Manual Analysis
To ask Nova about a camera feed right now:
1.  Go to **Developer Tools > Actions (Services)**.
2.  Select `nova_conversation.analyze_camera`.
3.  Choose your **Nova Instance** and a **Camera Entity**.
4.  Enter a prompt: *"Is there a package on the porch?"*
5.  Nova returns a `description` variable with the answer.

### 2. Pro Tip: Using Multiple Instances
You can install Nova **twice** to create a hybrid setup:
* **Instance 1 (Voice/Chat):** Point this to a local model (Ollama/LM Studio) or a cheap model like `gpt-4o-mini`. Use this as your default Assistant.
* **Instance 2 (Vision):** Point this to a powerful model like `openai/gpt-4o`. Use this instance specifically when calling the `analyze_camera` service.

---

## ✨ Core Features
* **Ultra-Low Latency:** Optimized for efficiency. Response times on modest hardware (HP T630) dropped from **50s down to ~10s**.
* **Live Text Streaming:** Tokens type out on your screen in real-time.
* **Smart Home Control:** Full `llm_hass_api` integration to toggle lights, check sensors, and run scripts.
* **Native Tool Buffering:** Custom background buffer safely executes complex tool calls without UI glitches.
* **Safe Chat Toggle:** Instantly sever the LLM's connection to your devices for general chat-only use.
* **Circuit Breaker:** Prevents models from getting stuck in infinite tool-calling loops.

---

## ⚠️ Model Recommendations
* **Vision Tasks:** `openai/gpt-4o` or `anthropic/claude-3.5-sonnet` (via OpenRouter).
* **Daily Chat/Control:** `openai/gpt-4o-mini`, `anthropic/claude-3-haiku`, or local **20B+** models.
* **Local Hosting:** Point the Base URL to your local IP for LM Studio, Ollama, or LocalAI.

---

## 🖼️ Interface
The selector interface auto-populates from your chosen provider:
<img width="753" height="905" alt="Interface Animation" src="https://github.com/user-attachments/assets/fbddb5fc-c8d0-4c38-93f6-d7fbaeefdf08" />

## 📈 Real-World Performance
Experience a massive leap in speed compared to standard OpenAI integrations.
<img width="753" height="905" alt="Performance Question" src="https://github.com/user-attachments/assets/ec07a6bb-1576-4367-a661-960c59f484fa" />
