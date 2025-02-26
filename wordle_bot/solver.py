import json
import math
import concurrent.futures
import matplotlib.pyplot as plt  # Only needed for plotting in test mode
from collections import Counter
from functools import lru_cache
from dutch_words import get_ranked


#############################################
# 1) Data Loading
#############################################

def fetch_dutch_4_letter_words(json_path="combined_four_letter_words.json"):
    """
    Loads the list of 4-letter words from a JSON file.
    This dictionary is used for guess selection.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_solution_words(json_path="solution_words.json"):
    """
    Loads the list of possible solution words from a JSON file.
    This list forms the candidate set.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


#############################################
# 2) Green-Only Feedback Calculation
#############################################

def calculate_feedback(guess, solution):
    """
    Returns the number of letters in the guess that are in the correct position.
    Example: if guess = 'boom' and solution = 'boem', returns 3.
    """
    return sum(1 for g, s in zip(guess, solution) if g == s)


#############################################
# 3) Candidate Filtering
#############################################

def filter_candidates(candidates, guess, observed_feedback):
    """
    Filters the list 'candidates' to keep only words for which
    calculate_feedback(guess, word) equals observed_feedback.
    """
    return [c for c in candidates if calculate_feedback(guess, c) == observed_feedback]


#############################################
# 4) Best Starting Word by Positional Frequency
#############################################

def get_best_starting_word(dictionary_words, solution_words):
    """
    Computes a score for each word in the dictionary based on letter frequencies
    at each position from the solution set. Returns the word with the highest score.
    """
    # Compute positional frequencies for positions 0..3.
    pos_freq = [Counter() for _ in range(4)]
    for word in solution_words:
        for i, letter in enumerate(word):
            pos_freq[i][letter] += 1

    best_word = None
    best_score = -1
    for word in dictionary_words:
        score = 0
        for i, letter in enumerate(word):
            score += pos_freq[i][letter]
        if score > best_score:
            best_score = score
            best_word = word
    return best_word


#############################################
# 5) Hybrid Scoring: Entropy + Positional Score
#############################################

def score_guess(guess, candidates):
    """
    Computes a hybrid score for 'guess' over the candidate set:
      - Entropy: Expected information gain from the distribution of green-feedback over candidates.
      - Positional Score: Sum of frequencies (per position) of the guessed letter among candidates.
    The positional score weight is increased to 0.005.
    """
    total = len(candidates)
    feedback_counts = {}
    for sol in candidates:
        fb = calculate_feedback(guess, sol)
        feedback_counts[fb] = feedback_counts.get(fb, 0) + 1

    entropy = 0.0
    for count in feedback_counts.values():
        p = count / total
        entropy -= p * math.log2(p) if p > 0 else 0

    # Compute positional frequency score
    pos_freq = [Counter() for _ in range(len(guess))]
    for sol in candidates:
        for i, letter in enumerate(sol):
            pos_freq[i][letter] += 1
    positional_score = sum(pos_freq[i].get(letter, 0) for i, letter in enumerate(guess))

    return entropy + 0.005 * positional_score


def choose_best_guess_hybrid(possible_guesses, current_candidates, restrict_guess_space=False, candidate_threshold=50):
    """
    Chooses the best guess based on the hybrid score.
    If restrict_guess_space is True or if the candidate set is small,
    only the candidate set is used as the guess space.
    """
    if restrict_guess_space or len(current_candidates) < candidate_threshold:
        guess_space = current_candidates
    else:
        guess_space = possible_guesses

    if len(current_candidates) <= 1:
        return current_candidates[0] if current_candidates else guess_space[0]

    best_guess = None
    best_score = -math.inf
    for guess_word in guess_space:
        score = score_guess(guess_word, current_candidates)
        if score > best_score:
            best_score = score
            best_guess = guess_word
    return best_guess


#############################################
# 6A) Interactive Solver (Green Feedback)
#############################################

def interactive_solver():
    dictionary_words = fetch_dutch_4_letter_words()
    print(f"Loaded {len(dictionary_words)} 4-letter words from dictionary.")
    solution_words = load_solution_words("solution_words.json")
    print(f"Loaded {len(solution_words)} possible solution words.")

    current_candidates = list(solution_words)
    starting_word = get_best_starting_word(dictionary_words, solution_words)
    print(f"Best starting word: {starting_word}")

    guess_history = []
    guess_count = 0
    current_guess = starting_word

    while True:
        guess_count += 1
        print(f"\nGuess #{guess_count}: {current_guess}")
        user_input = input("Enter green feedback (0-4, or 'q' to quit): ").strip()
        if user_input.lower() == 'q':
            print("Solver terminated by user.")
            break
        try:
            fb = int(user_input)
        except ValueError:
            print("Invalid input. Please enter a number from 0 to 4.")
            continue

        guess_history.append((current_guess, fb))
        if fb == 4:
            print(f"Success! The word is {current_guess} (guessed in {guess_count} tries).")
            break

        current_candidates = filter_candidates(current_candidates, current_guess, fb)
        if not current_candidates:
            print("No candidates remain. Check your feedback!")
            break

        print(f"{len(current_candidates)} candidates remain.")
        print("Guess History:", guess_history)

        # Restrict guess space if candidate set is small.
        current_guess = choose_best_guess_hybrid(dictionary_words, current_candidates,
                                                 restrict_guess_space=(len(current_candidates) < 50))
    print("\nFinal Guess History:")
    for i, (g, f) in enumerate(guess_history, start=1):
        print(f"Guess {i}: {g} -> feedback: {f}")


#############################################
# 6B) Test Accuracy Mode (Green Feedback)
#############################################

def solve_single_word(solution, dictionary_words, solution_words, starting_word, max_tries=6, final_guess_turns=1):
    """
    Attempts to guess the given solution word with at most max_tries.
    Uses the fixed starting_word as the first guess, then chooses subsequent guesses
    based on previous feedback.
    If the number of remaining tries is <= final_guess_turns, restrict the guess space to current candidates.
    Returns (solved, number of tries, guess history).
    """
    current_candidates = list(solution_words)
    guess_history = []
    guess_count = 0

    if starting_word:
        guess = starting_word
        guess_count += 1
        fb = calculate_feedback(guess, solution)
        guess_history.append((guess, fb))
        if fb == 4:
            return True, guess_count, guess_history
        current_candidates = filter_candidates(current_candidates, guess, fb)

    while guess_count < max_tries:
        guess_count += 1
        remaining = max_tries - guess_count + 1
        restrict_space = (remaining <= final_guess_turns)
        guess = choose_best_guess_hybrid(dictionary_words, current_candidates, restrict_guess_space=restrict_space)
        fb = calculate_feedback(guess, solution)
        guess_history.append((guess, fb))
        if fb == 4:
            return True, guess_count, guess_history
        current_candidates = filter_candidates(current_candidates, guess, fb)
        if len(current_candidates) == 1 and current_candidates[0] == solution:
            guess_history.append((current_candidates[0], 4))
            return True, guess_count, guess_history

    return False, guess_count, guess_history


def test_accuracy(max_tries=6, final_guess_turns=1):
    """
    Runs the solver over all solution words (in parallel) and prints:
      - Success rate
      - Average number of guesses (for successful solves)
    """
    dictionary_words = fetch_dutch_4_letter_words()
    solution_words = load_solution_words("solution_words.json")
    starting_word = get_best_starting_word(dictionary_words, solution_words)
    print(f"Best starting word: {starting_word}")

    results = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(solve_single_word, sol, dictionary_words, solution_words, starting_word, max_tries,
                            final_guess_turns)
            for sol in solution_words
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    solved_count = 0
    total_tries = 0
    for solved, tries, history in results:
        if solved:
            solved_count += 1
            total_tries += tries
    total = len(solution_words)
    success_rate = 100.0 * solved_count / total
    avg_tries = total_tries / solved_count if solved_count else float('inf')

    print("\n=== TEST ACCURACY RESULTS ===")
    print(f"Total solution words: {total}")
    print(f"Solved: {solved_count} within {max_tries} tries")
    print(f"Success rate: {success_rate:.2f}%")
    print(f"Average guesses (for successful solves): {avg_tries:.2f}")


#############################################
# 7) Main
#############################################

def main():
    mode = input("Choose mode: [i]nteractive or [t]est accuracy? ").strip().lower()
    if mode == 'i':
        interactive_solver()
    elif mode == 't':
        max_tries = int(input("Enter maximum number of tries (e.g., 6): "))
        final_turns = int(input("Enter number of final guess turns to restrict guess space (e.g., 1): "))
        test_accuracy(max_tries=max_tries, final_guess_turns=final_turns)
    else:
        print("Invalid mode selected.")


if __name__ == "__main__":
    main()
