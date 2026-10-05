import random
from typing import Dict, Any

class Corruptor:
    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)

    def corrupt_reference(self, ref: Dict[str, Any], corruption_type: str) -> Dict[str, Any]:
        corrupted = ref.copy()
        
        if corruption_type == "title_changed" and corrupted.get("title"):
            words = corrupted["title"].split()
            if len(words) > 1:
                # Swap two random words
                idx1 = self.random.randint(0, len(words) - 1)
                idx2 = self.random.randint(0, len(words) - 1)
                words[idx1], words[idx2] = words[idx2], words[idx1]
                corrupted["title"] = " ".join(words)
            else:
                corrupted["title"] = corrupted["title"] + " Modified"
                
        elif corruption_type == "author_changed" and corrupted.get("authors"):
            authors = corrupted["authors"].split("|")
            if authors:
                authors[0] = "Corrupt, X."
                corrupted["authors"] = "|".join(authors)
                
        elif corruption_type == "year_changed" and corrupted.get("year"):
            corrupted["year"] = str(int(corrupted["year"]) + self.random.randint(1, 10))
            
        elif corruption_type == "venue_changed" and corrupted.get("venue"):
            corrupted["venue"] = "Journal of " + self.random.choice(["Fake Science", "Unknown Things", "Void"])
            
        elif corruption_type == "doi_changed" and corrupted.get("doi"):
            corrupted["doi"] = corrupted["doi"][:-1] + str(self.random.randint(0, 9))
            
        return corrupted

if __name__ == "__main__":
    c = Corruptor(42)
    # Example usage:
    ref = {
        "title": "A study of citation verification",
        "authors": "Smith, J.",
        "year": "2020",
        "venue": "Journal of Testing",
        "doi": "10.1234/test.1"
    }
    print("Original:", ref)
    print("Title Corrupted:", c.corrupt_reference(ref, "title_changed"))
    print("Author Corrupted:", c.corrupt_reference(ref, "author_changed"))
    print("Year Corrupted:", c.corrupt_reference(ref, "year_changed"))
