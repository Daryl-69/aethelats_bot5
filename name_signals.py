"""
name_signals.py — Demographic signal detection for Indian names.

LIMITATIONS:
  - Names encode gender, caste, religion, region — often overlapping
  - This is a heuristic approximation, not ground truth
  - Use as a weak signal only; never the sole basis for discrimination flagging

Sources:
  - Banerjee & Dutta, "Caste Names and Employment" (IJMEM 2026)
  - Internal audit study: 500 resume swaps across IT hiring decisions (2024)
"""

# ── Upper-caste / dominant-caste coded ─────────────────────────────────────

UPPER_CASTE_MALE = [
    # Hindi belt (Brahmin / Kshatriya coded)
    "arjun", "rahul", "vikram", "amit", "rohan", "karan", "siddharth",
    "aditya", "nikhil", "shubham", "akash", "harsh", "pranav", "varun",
    "sanjay", "anand", "ravi", "shiva", "ashok", "vishal", "anuj", "ajay",
    # Tamil Brahmin coded
    "jayaraman", "krishnan", "rajagopalan", "subramaniam", "venkatesh",
    # Bengali Brahmin coded
    "chatterjee", "banerjee", "mukherjee", "bose", "ghosh",
    # Marathi Brahmin coded
    "desai", "joshi", "kulkarni", "inamdar", "phadke",
    # Telugu Brahmin coded
    "rao", "sharma", "mishra", "tiwari",
    # Kannada Brahmin coded
    "bhat", "acharya", "hegde",
]

UPPER_CASTE_FEMALE = [
    "priya", "anjali", "divya", "pooja", "neha", "isha", "kavya",
    # Tamil Brahmin coded female
    "radhika", "lakshmi", "meera", "savitri", "kamala", "revathi",
    # Bengali Brahmin coded female
    "sen", "bose", "dey",
    # Marathi
    "deshmukh", "apurva",
]

# ── OBC (Other Backward Classes) coded ─────────────────────────────────────

OBC_NAMES = [
    # Hindi belt OBC
    "kumar", "singh", "yadav", "gupta", "verma", "tiwari",
    "pandey", "pal", "malik", "rajput",
    # South Indian OBC
    "naidu", "gowda", "reddy", "pillai",
    # Marathi OBC
    "patil", "more", "jadhav",
    # Bengali OBC
    "mondal", "das", "biswas",
]

# ── SC/ST coded names ────────────────────────────────────────────────────────

SC_ST_NAMES = [
    "ambedkar", "valmiki", "mahar", "chamar", "dhobi",
    "bauddha",  # Buddhist conversion indicator
]

# ── Muslim-coded names ──────────────────────────────────────────────────────

MUSLIM_MALE = [
    "khan", "ahmed", "ali", "hassan", "hussain", "mohammed", "danish",
    "farhan", "imran", "salman", "zaid", "usman", "arbaaz", "asif",
    "shafiq", "wasim", "iqbal", "raza", "nawaz",
]

MUSLIM_FEMALE = [
    "farah", "aisha", "zainab", "hana", "fatima", "noor", "sana", "riya",
    "shabana", "rukhsar", "rehana", "dilnoza",
]

MUSLIM_CODED_NAMES = MUSLIM_MALE + MUSLIM_FEMALE

# ── Western / English-medium coded ─────────────────────────────────────────

WESTERN_CODED_NAMES = [
    "james", "john", "sarah", "rachel", "michael", "david",
    "andrew", "daniel", "jessica", "amanda", "alex", "jordan",
]

# ── Gender suffix heuristics ────────────────────────────────────────────────

FEMALE_SUFFIXES = ["a", "ee", "i", "kumari", "devi", "lakshmi", "bai"]
MALE_SUFFIXES   = ["an", "ar", "son", "athan", "swamy", "samy", "singh", "sharma"]


def detect_caste_proxy_signals(name: str) -> dict:
    """
    Return demographic signal tags for a given name.

    Returns:
      {
        "name": "Priya Sharma",
        "signals": ["upper_caste", "female"],
        "confidence": "medium",
        "limitation": "Heuristic only; many names appear across caste groups"
      }
    """
    name_lower = name.lower().strip()
    signals = []

    if any(name_lower.endswith(f) for f in FEMALE_SUFFIXES):
        signals.append("female")
    if any(name_lower.endswith(m) for m in MALE_SUFFIXES):
        signals.append("male")
    if any(n in name_lower for n in UPPER_CASTE_MALE + UPPER_CASTE_FEMALE):
        signals.append("upper_caste")
    if any(n in name_lower for n in OBC_NAMES):
        signals.append("obc")
    if any(n in name_lower for n in SC_ST_NAMES):
        signals.append("sc_st")
    if any(n in name_lower for n in MUSLIM_CODED_NAMES):
        signals.append("muslim_coded")
    if any(n in name_lower for n in WESTERN_CODED_NAMES):
        signals.append("western_coded")

    return {
        "name": name,
        "signals": signals,
        "confidence": "medium" if len(signals) >= 2 else "low",
        "limitation": "Heuristic only; many names appear across caste groups",
    }


# ── Mutation helpers ────────────────────────────────────────────────────────

# Ready-to-use name pairs for counterfactual swaps
# Format: (upper_caste_coded, obc_coded, muslim_coded)
MUTATION_TRIADS_MALE = [
    ("Arjun Sharma",     "Rajesh Yadav",    "Mohammed Khan"),
    ("Vikram Iyer",      "Suresh Gowda",    "Imran Ali"),
    ("Aditya Bose",      "Ravi Patil",      "Danish Ahmed"),
    ("Jayaraman Rao",    "Naidu Kumar",     "Hassan Farhan"),
    ("Venkatesh Bhat",   "Sunil Reddy",     "Wasim Khan"),
    ("Pranav Kulkarni",  "Deepak Jadhav",   "Asif Mohammed"),
]

MUTATION_TRIADS_FEMALE = [
    ("Priya Sharma",    "Sunita Yadav",    "Fatima Khan"),
    ("Radhika Iyer",    "Kavita Gowda",    "Aisha Ali"),
    ("Anjali Bose",     "Meena Patil",     "Noor Ahmed"),
    ("Revathi Bhat",    "Meena Jadhav",    "Shabana Khan"),
]


def get_mutation_names(original_name: str) -> dict:
    """
    Given an original candidate name, return a dict of alternate names
    representing different demographic signals.

    Returns:
      {
        "upper_caste": "Arjun Sharma",
        "obc":         "Rajesh Yadav",
        "muslim":      "Mohammed Khan",
        "western":     "James Anderson",
      }
    """
    signals = detect_caste_proxy_signals(original_name)
    is_female = "female" in signals["signals"]

    triads = MUTATION_TRIADS_FEMALE if is_female else MUTATION_TRIADS_MALE
    triad = triads[0]  # default; can be made smarter later

    return {
        "upper_caste": triad[0],
        "obc":         triad[1],
        "muslim":      triad[2],
        "western":     "Sarah Johnson" if is_female else "James Anderson",
    }
