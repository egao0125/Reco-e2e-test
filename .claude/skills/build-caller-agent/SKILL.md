# Skill: Build Caller Agent

## Purpose
Build a Caller Agent (偽顧客AI) that calls Reco via Twilio Media Streams for E2E testing.

## Steps

1. **Read Reco's implementation first**
   - Look at `../voice-fullduplex/` for the existing Pipecat + Twilio Media Streams code
   - Understand how Twilio WebSocket connection is established
   - Understand the audio format (8kHz mulaw)
   - Understand how Pipecat pipeline is configured

2. **Build the Caller Agent as a mirror**
   - Same Pipecat framework
   - Same Twilio Media Streams connection method
   - Different role: Caller Agent is the "customer", Reco is the "agent"
   - Different LLM prompt: customer persona instead of business agent

3. **Twilio call flow**
   - Caller Agent uses Twilio REST API to initiate outbound call
   - From: test Twilio number → To: Reco's test Twilio number
   - Both sides connect via Twilio Media Streams (WebSocket)

4. **Output**
   - `caller/caller_agent.py` — Main Pipecat pipeline (customer role)
   - `caller/twilio_caller.py` — Twilio REST API call initiation + Media Streams
   - `caller/scenarios/` — JSON scenario files

## Key Constraint
- The Caller Agent must go through the EXACT same Twilio path as a real phone call
- No shortcuts (no direct WebSocket to Reco, no bypassing Twilio)
- This ensures the test covers the full production path including telephony latency
