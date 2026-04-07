import os
import re
from collections import defaultdict


class ChatBot:
    def __init__(self, checkboxes=None):
        self.checkboxes = checkboxes if checkboxes else []
        self.memory = {
            "last_intent": None
        }
        self.update_data(self.checkboxes)

    def update_checkboxes(self, checkboxes):
        self.checkboxes = checkboxes
        self.update_data(checkboxes)

    # -------------------------------
    # 📊 DATA PROCESSING
    # -------------------------------
    def update_data(self, checkboxes):
        self.files_info = []
        self.total_size = 0
        self.type_count = defaultdict(int)
        self.folder_sizes = defaultdict(int)

        for cb, f in checkboxes:
            try:
                size = os.path.getsize(f)
                ext = os.path.splitext(f)[1].lower()
                folder = os.path.dirname(f)

                info = {
                    "path": f,
                    "size": size,
                    "ext": ext,
                    "folder": folder,
                    "is_image": ext in [".png", ".jpg", ".jpeg"]
                }

                self.files_info.append(info)
                self.total_size += size
                self.type_count[ext] += 1
                self.folder_sizes[folder] += size

            except:
                continue

    # -------------------------------
    # 📏 SIZE FORMAT
    # -------------------------------
    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    # -------------------------------
    # 🧠 INTENT DETECTION
    # -------------------------------
    def detect_intent(self, query):
        patterns = {
            "largest": [r"largest|biggest|max"],
            "smallest": [r"smallest|tiny|min"],
            "count": [r"how many|count|total files"],
            "total_size": [r"total size|space used"],
            "images": [r"images|photos|pictures"],
            "types": [r"types|extensions|formats"],
            "folders": [r"folders|directories"],
            "list": [r"list|show files"],
            "delete": [r"delete|remove|suggest"],
            "help": [r"help|what can you do"],
        }

        scores = defaultdict(int)

        for intent, regs in patterns.items():
            for pattern in regs:
                if re.search(pattern, query):
                    scores[intent] += 1

        if not scores:
            return None

        return max(scores, key=scores.get)

    # -------------------------------
    # 🧠 FOLLOW-UP HANDLING
    # -------------------------------
    def resolve_followup(self, query, intent):
        if intent:
            return intent

        if self.memory["last_intent"]:
            if "image" in query:
                return "images"
            if "folder" in query:
                return "folders"
            if "size" in query:
                return "total_size"

        return None

    # -------------------------------
    # 💬 RESPONSE ENGINE
    # -------------------------------
    def respond(self, query: str) -> str:
        query = query.lower()

        if not self.files_info:
            return "⚠️ Please scan duplicate files first."

        intent = self.detect_intent(query)
        intent = self.resolve_followup(query, intent)

        # Save memory
        self.memory["last_intent"] = intent

        # Pre-calc
        largest = max(self.files_info, key=lambda x: x['size'])
        smallest = min(self.files_info, key=lambda x: x['size'])

        # ---------------- RESPONSES ----------------
        if intent == "largest":
            return f"📦 Largest file:\n{largest['path']}\nSize: {self._format_size(largest['size'])}"

        elif intent == "smallest":
            return f"📦 Smallest file:\n{smallest['path']}\nSize: {self._format_size(smallest['size'])}"

        elif intent == "count":
            return f"📊 Total duplicate files: {len(self.files_info)}"

        elif intent == "total_size":
            return f"💾 Total duplicate size: {self._format_size(self.total_size)}"

        elif intent == "images":
            images = [f for f in self.files_info if f['is_image']]
            total_img_size = sum(f['size'] for f in images)
            return (
                f"🖼️ Image duplicates: {len(images)}\n"
                f"Total size: {self._format_size(total_img_size)}"
            )

        elif intent == "types":
            result = "📂 File types:\n"
            for ext, count in self.type_count.items():
                result += f"{ext or 'no_ext'}: {count}\n"
            return result

        elif intent == "folders":
            result = "📁 Top folders:\n"
            sorted_folders = sorted(self.folder_sizes.items(), key=lambda x: x[1], reverse=True)
            for folder, size in sorted_folders[:5]:
                result += f"{folder}: {self._format_size(size)}\n"
            return result

        elif intent == "list":
            paths = [f['path'] for f in self.files_info]
            return "📄 Files:\n" + "\n".join(paths[:10])

        elif intent == "delete":
            sorted_files = sorted(self.files_info, key=lambda x: x['size'], reverse=True)
            result = "🧹 Suggested deletions:\n"
            for f in sorted_files[:5]:
                result += f"{f['path']} ({self._format_size(f['size'])})\n"
            return result

        elif intent == "help":
            return (
                "💡 You can ask:\n"
                "- Largest file\n"
                "- Total size\n"
                "- Image duplicates\n"
                "- Folder usage\n"
                "- Suggest deletions\n"
            )

        else:
            return "🤖 I didn’t understand. Try 'help'."