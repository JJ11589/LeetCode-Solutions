"""
config.py
---------
Central place for mappings and tunables. Edit this file to change folder
naming, language preferences, or output paths — no other script needs to be
touched for those kinds of changes.
"""

import os

# --------------------------------------------------------------------- #
# Repo layout
# --------------------------------------------------------------------- #
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
STATS_DIR = os.path.join(REPO_ROOT, "stats")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets")
ROOT_README = os.path.join(REPO_ROOT, "README.md")

# --------------------------------------------------------------------- #
# Default / preferred language
# --------------------------------------------------------------------- #
DEFAULT_LANG = "cpp"

LANG_EXT = {
    "cpp": "cpp",
    "c": "c",
    "java": "java",
    "python": "py",
    "python3": "py",
    "javascript": "js",
    "typescript": "ts",
    "csharp": "cs",
    "golang": "go",
    "kotlin": "kt",
    "swift": "swift",
    "rust": "rs",
    "ruby": "rb",
    "scala": "scala",
    "php": "php",
}

LANG_MARKDOWN_FENCE = {
    "cpp": "cpp",
    "c": "c",
    "java": "java",
    "python": "python",
    "python3": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "csharp": "csharp",
    "golang": "go",
    "kotlin": "kotlin",
    "swift": "swift",
    "rust": "rust",
    "ruby": "ruby",
    "scala": "scala",
    "php": "php",
}

# --------------------------------------------------------------------- #
# Topic -> folder name. LeetCode's own topicTags are used as the source of
# truth; this just controls how the tag name is turned into a folder name.
# Add overrides here for tags whose auto-generated folder name you don't like.
# --------------------------------------------------------------------- #
TOPIC_FOLDER_OVERRIDES = {
    "Array": "Arrays",
    "String": "Strings",
    "Hash Table": "HashMap",
    "Binary Search": "Binary_Search",
    "Tree": "Trees",
    "Binary Tree": "Trees",
    "Binary Search Tree": "BST",
    "Depth-First Search": "DFS",
    "Breadth-First Search": "BFS",
    "Graph": "Graphs",
    "Greedy": "Greedy",
    "Heap (Priority Queue)": "Heap",
    "Dynamic Programming": "Dynamic_Programming",
    "Bit Manipulation": "Bit_Manipulation",
    "Trie": "Trie",
    "Union Find": "Union_Find",
    "Segment Tree": "Segment_Tree",
    "Backtracking": "Backtracking",
    "Math": "Math",
    "Sliding Window": "Sliding_Window",
    "Two Pointers": "Two_Pointers",
    "Monotonic Stack": "Monotonic_Stack",
    "Stack": "Stack",
    "Queue": "Queue",
    "Linked List": "Linked_List",
    "Matrix": "Matrix",
    "Simulation": "Simulation",
    "Design": "Design",
}

DEFAULT_TOPIC_FOLDER = "Miscellaneous"

DIFFICULTY_EMOJI = {
    "Easy": "🟢",
    "Medium": "🟡",
    "Hard": "🔴",
}

DIFFICULTY_BADGE_COLOR = {
    "Easy": "brightgreen",
    "Medium": "yellow",
    "Hard": "red",
}


def folder_for_topic(tag_name: str) -> str:
    if tag_name in TOPIC_FOLDER_OVERRIDES:
        return TOPIC_FOLDER_OVERRIDES[tag_name]
    return tag_name.replace(" ", "_").replace("-", "_")


def primary_topic_folder(topic_tags: list[dict]) -> str:
    """Pick the first topic tag as the primary folder; fall back to misc."""
    if not topic_tags:
        return DEFAULT_TOPIC_FOLDER
    return folder_for_topic(topic_tags[0]["name"])
