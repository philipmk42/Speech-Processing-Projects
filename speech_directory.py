
import csv
import os
from dataclasses import dataclass
from typing import Dict, List

try:
    import speech_recognition as sr
except ImportError:
    sr = None
    print("Warning: 'speech_recognition' package not found. "
          "Install it with: pip install SpeechRecognition pyaudio")


CSV_PATH = "telephone_directory.csv"


@dataclass
class DirectoryEntry:
    name: str
    phone: str
    email: str


def create_sample_directory(csv_path: str) -> List[DirectoryEntry]:
    """
    Create a sample telephone directory and save it as a CSV file.

    If the CSV already exists, it will NOT be overwritten.
    """
    if os.path.exists(csv_path):
        return load_directory(csv_path)

    entries = [
        DirectoryEntry("Alice", "9876543210", "alice@example.com"),
        DirectoryEntry("Bob", "9123456780", "bob@example.com"),
        DirectoryEntry("Charlie", "9012345678", "charlie@example.com"),
        DirectoryEntry("David", "9988776655", "david@example.com"),
        DirectoryEntry("Philip", "9090909090", "philip@example.com"),
    ]

    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "phone", "email"])
        for e in entries:
            writer.writerow([e.name, e.phone, e.email])

    print(f"Sample directory created and saved to '{csv_path}'.")
    return entries


def load_directory(csv_path: str) -> List[DirectoryEntry]:
    """
    Load the directory from a CSV file.
    """
    entries: List[DirectoryEntry] = []
    if not os.path.exists(csv_path):
        print(f"No CSV file found at '{csv_path}'. Creating a sample directory instead.")
        return create_sample_directory(csv_path)

    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(
                DirectoryEntry(
                    name=row["name"],
                    phone=row["phone"],
                    email=row["email"],
                )
            )

    print(f"Loaded {len(entries)} entries from '{csv_path}'.")
    return entries


def build_name_index(entries: List[DirectoryEntry]) -> Dict[str, DirectoryEntry]:
    """
    Build a dictionary for quick lookup by lowercase name.
    """
    return {e.name.lower(): e for e in entries}


def recognize_spelled_name(timeout: float = 5.0, phrase_time_limit: float = 5.0) -> str:
    """
    Use the microphone and Google Web Speech API to recognize a *spelled* name.

    Example input (spoken):
        "P H I L I P"
    Recognized text might be:
        "p h i l i p"
    We then strip everything except letters and join:
        "philip"
    Finally we title-case:
        "Philip"
    """
    if sr is None:
        print("Speech recognition is not available. Falling back to manual input.")
        return input("Type the name instead: ").strip().title()

    recognizer = sr.Recognizer()

    # Select microphone
    try:
        mic = sr.Microphone()
    except OSError as e:
        print(f"Could not access microphone: {e}")
        print("Falling back to manual text input.")
        return input("Type the name instead: ").strip().title()

    with mic as source:
        print("\nPlease SPELL the name (e.g. 'P H I L I P') after the beep...")
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("No speech detected in time. Falling back to manual input.")
            return input("Type the name instead: ").strip().title()

    try:
        text = recognizer.recognize_google(audio)
        print(f"Recognized raw text: '{text}'")
    except sr.UnknownValueError:
        print("Could not understand audio. Please try typing the name.")
        return input("Type the name instead: ").strip().title()
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        print("Falling back to manual text input.")
        return input("Type the name instead: ").strip().title()

    # Keep only letters and join to form the name
    letters_only = "".join(ch for ch in text if ch.isalpha())
    if not letters_only:
        print("No letters detected in recognized text. Please type the name instead.")
        return input("Type the name instead: ").strip().title()

    name = letters_only.title()
    print(f"Interpreted spelled name as: '{name}'\n")
    return name


def retrieve_entry_by_speech(name_index: Dict[str, DirectoryEntry]) -> None:
    """
    Recognize a spelled name via speech (or manual fallback) and retrieve matching directory entry.
    """
    name = recognize_spelled_name()
    key = name.lower()

    if key in name_index:
        entry = name_index[key]
        print("Directory entry found:")
        print(f"  Name : {entry.name}")
        print(f"  Phone: {entry.phone}")
        print(f"  Email: {entry.email}")
    else:
        print(f"No entry found for '{name}'.")


def list_all_entries(entries: List[DirectoryEntry]) -> None:
    """
    Print all entries in a simple table.
    """
    print("\n--- Telephone Directory ---")
    print(f"{'Name':<15} {'Phone':<15} {'Email'}")
    print("-" * 50)
    for e in entries:
        print(f"{e.name:<15} {e.phone:<15} {e.email}")
    print("-" * 50)
    print(f"Total entries: {len(entries)}\n")


def main() -> None:
    # Step 1: ensure we have a CSV directory file
    entries = load_directory(CSV_PATH)
    name_index = build_name_index(entries)

    # Simple text menu
    while True:
        print("\n==== Speech-Based Telephone Directory ====")
        print("1. Retrieve entry by spoken *spelled* name")
        print("2. List all directory entries")
        print("3. Exit")
        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == "1":
            retrieve_entry_by_speech(name_index)
        elif choice == "2":
            list_all_entries(entries)
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
