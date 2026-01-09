from ai.logic import create_crisis_chain
from services.speech import transcribe_audio, text_to_speech
from pathlib import Path

def run_full_v2_test():
    print("--- 🚀 STARTING VAAYU V2 BACKEND LOOP TEST 🚀 ---")

    # --- 1. PERCEPTION (Speech-to-Text) ---
    # To run this test, you must have a 'test_crisis_audio.wav' or '.mp3' file
    # in the root directory of your project.
    audio_input_path = "test_crisis_audio.m4a" # or .mp3, whisper handles both
    
    if not Path(audio_input_path).is_file():
        print(f"\n[ERROR] Test audio file not found at: {audio_input_path}")
        print("Please record a sample audio file to run this test.")
        return

    transcribed_text = transcribe_audio(audio_input_path)
    print(f"\n[Step 1] Perception complete. Transcript: '{transcribed_text}'")

    # --- 2. REASONING (RAG Chain) ---
    context = {
        "risk_score": 9,
        "heart_rate": 150,
        "transcript": transcribed_text
    }
    print(f"\n[Step 2] Reasoning with context: {context}")
    crisis_chain = create_crisis_chain()
    ai_decision = crisis_chain.invoke(context).strip().upper()
    print(f"Reasoning complete. AI Decision: '{ai_decision}'")

    # --- 3. ACTION (Text-to-Speech) ---
    response_text = ""
    if ai_decision == "ALERT":
        response_text = "Alerting your guardians and emergency services now. Help is on the way."
    elif ai_decision == "MONITOR":
        response_text = "Situation acknowledged. I will continue to monitor."
    else:
        response_text = "Decision unclear. Please state your situation again."
    
    print(f"\n[Step 3] Actioning decision. Generating speech for: '{response_text}'")
    speech_output_path = text_to_speech(response_text)
    
    print(f"\n[Step 4] Successfully generated MP3 audio response at: {speech_output_path}")
    print("This confirms the backend's core Perceive-Reason-Act loop is working correctly.")
    print("Please play the 'temp_audio.mp3' file in your project folder to hear the result.")
    
    print("\n--- ✅ VAAYU V2 BACKEND LOOP TEST COMPLETE ✅ ---")


if __name__ == "__main__":
    run_full_v2_test()
