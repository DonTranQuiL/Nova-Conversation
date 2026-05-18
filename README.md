<div align="center">

# 🌌 Nova Conversation (2026 Edition)
**The high-performance bridge for Local & Cloud AI in Home Assistant.**
</div>
<p align="center">
  <!-- Release / License -->
  <a href="https://github.com/DonTranQuiL/Nova-Conversation/releases">
    <img src="https://img.shields.io/github/v/release/DonTranQuiL/Nova-Conversation?style=for-the-badge&color=007ec6" alt="Latest Release">
  </a>
  <a href="https://github.com/DonTranQuiL/Nova-Conversation/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/DonTranQuiL/Nova-Conversation?style=for-the-badge&color=007ec6" alt="License">
  </a>

  <!-- CI / Quality -->
  <a href="https://github.com/DonTranQuiL/Nova-Conversation/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/DonTranQuiL/Nova-Conversation/codechecker.yml?style=for-the-badge&label=CODE%20CHECKS&color=5dbb0f" alt="Code Checks">
  </a>
  <a href="https://github.com/DonTranQuiL/Nova-Conversation/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/DonTranQuiL/Nova-Conversation/pytest.yml?style=for-the-badge&label=TESTS&color=5dbb0f" alt="Tests">
  </a>
  <a href="https://github.com/DonTranQuiL/Nova-Conversation/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/DonTranQuiL/Nova-Conversation/hacs.yaml?style=for-the-badge&label=HACS%20VALIDATION&color=5dbb0f" alt="HACS Validation">
  </a>

  <!-- Code Quality -->
  <a href="https://github.com/pre-commit/pre-commit">
    <img src="https://img.shields.io/badge/pre--commit-enabled-5dbb0f?style=for-the-badge" alt="pre-commit">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/badge/code%20style-ruff-000000?style=for-the-badge" alt="Ruff">
  </a>
  <a href="https://codecov.io/gh/DonTranQuiL/Nova-Conversation">
  <img 
    src="https://codecov.io/gh/DonTranQuiL/Nova-Conversation/branch/main/graph/badge.svg"
    alt="Coverage"
    style="height:28px;"
  >
</a>

  <!-- Ecosystem -->
  <a href="https://hacs.xyz/">
    <img src="https://img.shields.io/badge/HACS-CUSTOM-ff6e27?style=for-the-badge" alt="HACS">
  </a>
  <a href="https://www.home-assistant.io/">
    <img src="https://img.shields.io/badge/Home%20Assistant-2024.5%2B-007ec6?style=for-the-badge" alt="Home Assistant">
  </a>

  <!-- Social / Support -->
  <a href="https://github.com/DonTranQuiL">
    <img src="https://img.shields.io/badge/maintainer-%40DonTranQuiL-007ec6?style=for-the-badge" alt="Maintainer">
  </a>
  <a href="https://ko-fi.com/DonTranQuiL">
    <img src="https://img.shields.io/badge/buy%20me%20a%20coffee-donate-ffdd00?style=for-the-badge" alt="Donate">
  </a>
  <a href="https://community.home-assistant.io/">
    <img src="https://img.shields.io/badge/community-forum-007ec6?style=for-the-badge" alt="Community">
  </a>
</p>

</div>

### 🚀 A Community Revival 
Huge thanks to [Michelle Avery](https://github.com/michelle-avery) for the original project. Since the original repo has been inactive, I have fully rewritten the core architecture to bring it up to 2026.1+ standards, focusing on speed, reliability, and native streaming.



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
