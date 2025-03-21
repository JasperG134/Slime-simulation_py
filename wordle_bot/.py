import json
import os

def read_words_from_file(filepath):
    """Lees alle regels uit het bestand en retourneer als lijst."""
    with open(filepath, 'r', encoding='utf-8') as file:
        return file.read().splitlines()

def filter_four_letter_words(words):
    """Filter de lijst zodat alleen woorden met exact 4 karakters overblijven."""
    return [word for word in words if len(word) == 4]

def main():
    # Lijst met bestanden die de woordenlijsten bevatten
    bestanden = [
        r"C:\Users\jaspe\Downloads\OpenTaal-210G-woordenlijsten\OpenTaal-210G-basis-gekeurd.txt",
        r"C:\Users\jaspe\Downloads\OpenTaal-210G-woordenlijsten\OpenTaal-210G-basis-ongekeurd.txt",
        r"C:\Users\jaspe\Downloads\OpenTaal-210G-woordenlijsten\OpenTaal-210G-flexievormen.txt",
        r"C:\Users\jaspe\Downloads\OpenTaal-210G-woordenlijsten\OpenTaal-210G-verwarrend.txt"
    ]

    # Gebruik een set om dubbele woorden te vermijden
    alle_four_letter_words = set()

    for bestand in bestanden:
        if os.path.exists(bestand):
            woorden = read_words_from_file(bestand)
            gefilterd = filter_four_letter_words(woorden)
            alle_four_letter_words.update(gefilterd)
        else:
            print(f"Bestand '{bestand}' niet gevonden.")

    # Sorteer de woorden (optioneel)
    sorted_words = sorted(list(alle_four_letter_words))

    # Zet de data in een dictionary voor JSON export
    data = {
        "four_letter_words": sorted_words
    }

    # Schrijf naar het JSON-bestand
    output_file = "combined_four_letter_words.json"
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)

    print(f"JSON bestand is aangemaakt: {output_file}")

if __name__ == '__main__':
    main()
