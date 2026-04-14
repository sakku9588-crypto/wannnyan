🐾 Sakuneko Pet Translator (Dog & Cat Emotion Engine)
Developed by Sakku at Sakuramori Lab, this tool uses real-time audio analysis and a specialized "Emotion Engine" to translate pet vocalizations (barks, meows, purrs) into human-understandable emotions and messages.
🐱 Overview
This project is currently making waves in tech communities (like Reddit) for its unique approach to pet-human interaction. It combines Digital Signal Processing (DSP) with behavioral heuristic models to decode the frequency and intensity of pet sounds.
🐕 Meet the Profiles
The translator comes pre-configured with two primary profiles:
• Kei-kun (Dog): Optimized for Golden Retrievers and similar breeds. Focused on high-energy vocalization patterns.
• Gemi-nyan (Cat): Optimized for feline subtleness. Detects everything from hungry meows to affectionate purrs.
🛠️ Key Features
• Real-time Audio Engine: High-fidelity capture of pet vocalizations using a 22,050Hz sample rate.
• Dual-Mode Emotion Engine: - Dog Mode: Interprets barks, whines, and growls based on duration and pitch.
• Cat Mode: Specialized in detecting "hidden" purr frequencies and varied meow intonations.
• Interactive GUI: A playful, user-friendly interface that displays the "translated" text and emotional state in real-time.
• Hardware Agnostic: Supports various external microphones and input devices.
🏗️ Tech Stack
• Language: Python 3.x
• Audio Processing: SoundFile, NumPy, SciPy
• Logic: Heuristic-based Emotion Engine
• Interface: GUI module (via gui.py)
🚀 Getting Started
📋 Configuration
You can fine-tune the detection sensitivity in config.py.
• DOG_CONFIG: Adjust thresholds for "Playful" vs. "Alert" barks.
• CAT_CONFIG: Sensitivity settings for low-frequency purring.
“Connecting hearts across species.” 👉 Developed by Sakku at Sakuramori Lab
Note: This tool is intended for entertainment and behavioral study. Always trust your pet's body language first!
