# 🌌 Nova Conversation (2026 Edition)
**The high-performance bridge for Local & Cloud AI in Home Assistant.**

### 🚀 A Community Revival 
Huge thanks to [Michelle Avery](https://github.com/michelle-avery) for the original project. Since the original repo has been inactive, I have fully rewritten the core architecture to bring it up to 2026.1+ standards, focusing on speed, reliability, and native streaming.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Maintained](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/DonTranQuiL/nova_conversation/commits/main)

Bring the power of advanced Language Models to Home Assistant. This integration doesn't just chat—it physically controls your smart home and streams responses in real-time. Because it uses the universal OpenAI API standard, you can point this at **OpenRouter, LM Studio, LocalAI, Groq, Ollama**, or any compatible endpoint.

---

## 🌟 The "Next Level" Updates
This **Community Revived** version supercharges the original vision with modern architectural fixes:

* **Ultra-Low Latency:** Optimized for efficiency. In testing on modest hardware (HP T630 via Proxmox), response times dropped from **~50s down to ~10s**. On high-end systems, it is nearly instant.
* **Live Text Streaming:** Responses type out on your screen token-by-token. 
* **Native Tool Buffering:** Includes a custom background buffer that safely catches and executes fragmented JSON tool calls without breaking the chat UI or causing "vanishing text."
* **2026.1+ Ready:** Fully migrated to the new `LLMContext` and `ChatLog` structures. 
* **Dynamic Model Sync:** The integration automatically connects to your provider (OpenRouter, LM Studio, etc.) and builds a searchable dropdown of every available model.
* **Safe Chat Toggle:** Sever the LLM's connection to your devices with a single UI switch—perfect for using smaller models for general chat without risking hallucinations.
* **Circuit Breaker:** Built-in loop protection prevents models from getting stuck in endless tool-calling loops, saving your API credits and system resources.

---

## ✨ Core Features
* **Smart Home Control:** Fully integrated with Home Assistant's `llm_hass_api`. The AI can toggle lights, check sensors, and run scripts via natural language.
* **Custom Base URLs:** Running a local model on an old gaming PC? Just point the Base URL to your local IP.
* **Wide Compatibility:** Continues to support `max_tokens` for maximum compatibility with older or open-source local model providers.

---

## 🚀 Installation & Setup

1.  Copy the `nova_conversation` folder into your `custom_components` directory.
2.  Restart Home Assistant.
3.  Go to **Settings > Devices & Services > Add Integration**.
4.  Search for **Nova Conversation**.
5.  Enter your **API Key** and **Base URL** (defaults to `https://api.openai.com/v1`).
6.  Go to the integration **Configure** menu. Uncheck "Recommended" and click submit to reveal the advanced options, including the dynamic model dropdown!

---

## ⚠️ Model Recommendations
* **Local Models:** For reliable house control, use at least a **20B+ parameter** model. Smaller models (2B - 8B) are great for chat but may struggle with JSON tool formatting.
* **Cloud Models:** `openai/gpt-4o-mini` or `anthropic/claude-3-haiku` provide exceptional speed and accuracy.

---

## 🖼️ Interface
The selector interface auto-populates from your chosen provider (Example using OpenRouter):
<img width="753" height="905" alt="Interface Animation" src="https://github.com/user-attachments/assets/fbddb5fc-c8d0-4c38-93f6-d7fbaeefdf08" />

---

## 📈 Real-World Performance
Experience a massive leap in speed.
<img width="753" height="905" alt="Performance Question" src="https://github.com/user-attachments/assets/ec07a6bb-1576-4367-a661-960c59f484fa" />
