import sys
from engine.brain import ZeroBrain
from engine.voice import ZeroVoice

def main():
    brain = ZeroBrain()
    voice = ZeroVoice()

    print("\n==================================================")
    print("      ZERO CORE RUNTIME ENGINE INITIALIZED        ")
    print("==================================================")
    print("System: Host Native | Mode: Continuous Token Stream\n")

    while True:
        try:
            user_input = input("Rahul ──> ")
            if user_input.lower() in ['exit', 'quit', 'shutdown']:
                break
            if not user_input.strip():
                continue

            print("ZERO ──> ", end="")
            sys.stdout.flush()
            
            # Pipe tokens straight from the GPU to the screen and the audio line
            for token in brain.generate_streaming_response(user_input):
                # 1. Terminal Output
                sys.stdout.write(token)
                sys.stdout.flush()
                
                # 2. Audio Pipeline Input
                voice.stream_token(token)

            # Signal generation loop completion to wrap up trailing phonemes
            voice.end_of_turn()
            print()

        except (KeyboardInterrupt, EOFError):
            print("\nZERO: Thread safety disengagement initiated.")
            sys.exit(0)

if __name__ == "__main__":
    main()