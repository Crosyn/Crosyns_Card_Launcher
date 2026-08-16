'''
Straight forward command line mode implementation of the software,
A good way to understand the fundamentals of the application is to
start here and and walk through the calls.
'''
import subprocess
import sys
from pathlib import Path


def run_script(script_name: str):
    """
    Executes a sub-script using the current Python environment
    and pauses when it returns to ensure the user sees any final messages.
    """
    script_path = Path(script_name)

    if not script_path.exists():
        print(f"\n❌ Error: Cannot find '{script_name}' in this directory.")
        print("Please verify the file name and try again.")
        input("\nPress Enter to return to the main menu...")
        return

    print(f"\n▶️  Launching {script_name}...")
    print("--------------------------------------------------")

    try:
        # sys.executable ensures it uses the exact same Python environment/dependencies
        subprocess.run([sys.executable, str(script_path)])
    except Exception as e:
        print(f"\n❌ An error occurred while running the script: {e}")

    print("--------------------------------------------------")
    print(f"↩️  Returned from {script_name}.")
    input("Press Enter to open the main menu options...")


def display_menu():
    """Main interface loop managing navigation paths."""
    while True:
        # Clear screen styling trick for cleaner terminal viewing
        print("\033[H\033[J", end="")

        print("==================================================")
        print(" 🎮 NFC CARTS CONTROLLER PANEL ")
        print("==================================================")
        print("  [1] Open Card Commands Listener (Run Dashboard)")
        print("  [2] Open Provision Cards (Assign/Overwrite)")
        print("  [0] Exit Application")
        print("==================================================")

        choice = input("👉 Enter menu choice (0-2): ").strip()

        if choice == "1":
            # Call your background listener script
            run_script("card_commands.py")

        elif choice == "2":
            # Call your setup and assignment tool
            run_script("provision_card.py")

        elif choice == "0":
            print("\nShutting down...")
            print("👋 Goodbye!")
            sys.exit(0)

        else:
            print("\n⚠️  Invalid option selection framework. Choose 0, 1, or 2.")
            input("Press Enter to retry...")


if __name__ == "__main__":
    display_menu()