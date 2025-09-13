# main.py
"""
Main entry point for the NeuroGrip Ball Maze Game.
This script initializes and runs the main Game object.
"""
from game import Game

def main():
    """Initializes and runs the game application."""
    print("\n==============================")
    print("  NeuroGrip Ball Maze Game  ")
    print("==============================\n")
    
    try:
        neuro_grip_game = Game()
        neuro_grip_game.run()
    except Exception as e:
        print(f"\n[FATAL ERROR] An unexpected error occurred: {e}")
    finally:
        print("[INFO] Game has exited. Goodbye!\n")

if __name__ == '__main__':
    main()