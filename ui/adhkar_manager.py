import os
import json
import random
from PyQt6.QtWidgets import QMessageBox

class AdhkarManager:
    def __init__(self, settings_manager, localization_manager, base_path):
        self.settings_manager = settings_manager
        self.lm = localization_manager
        self.base_path = base_path
        self.adhkar_data = {}
        self.load_adhkar_data()

    def load_adhkar_data(self):
        try:
            # محاولة تحميل الأذكار من المسار المخصص
            adhkar_file = os.path.join(self.base_path, "resources", "adhkar", "ar.json")
            if not os.path.exists(adhkar_file):
                # إذا لم يكن الملف موجوداً، قم بإنشاء ملف افتراضي
                default_adhkar = {
                    "morning": [
                        {
                            "id": "morn001",
                            "text": "أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللهُ وَحْدَهُ لَا شَرِيكَ لَهُ",
                            "count": 1,
                            "benefit": "حَسَنَاتٌ بِعَدَدِ مَنْ فِي السَّمَاوَاتِ وَالأَرْضِ"
                        },
                        {
                            "id": "morn002",
                            "text": "اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ",
                            "count": 1,
                            "benefit": "حِفْظٌ مِنَ اللَّهِ تَعَالَى"
                        }
                    ],
                    "evening": [
                        {
                            "id": "even001",
                            "text": "أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللهُ وَحْدَهُ لَا شَرِيكَ لَهُ",
                            "count": 1,
                            "benefit": "حَسَنَاتٌ بِعَدَدِ مَنْ فِي السَّمَاوَاتِ وَالأَرْضِ"
                        },
                        {
                            "id": "even002",
                            "text": "اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ",
                            "count": 1,
                            "benefit": "حِفْظٌ مِنَ اللَّهِ تَعَالَى"
                        }
                    ],
                    "sleep": [
                        {
                            "id": "sleep001",
                            "text": "بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا",
                            "count": 1,
                            "benefit": "حِفْظٌ مِنَ اللَّهِ تَعَالَى"
                        },
                        {
                            "id": "sleep002",
                            "text": "اللَّهُمَّ قِنِي عَذَابَكَ يَوْمَ تَبْعَثُ عِبَادَكَ",
                            "count": 3,
                            "benefit": "حِفْظٌ مِنَ اللَّهِ تَعَالَى"
                        }
                    ]
                }
                os.makedirs(os.path.dirname(adhkar_file), exist_ok=True)
                with open(adhkar_file, 'w', encoding='utf-8') as f:
                    json.dump(default_adhkar, f, ensure_ascii=False, indent=4)
                self.adhkar_data = default_adhkar
            else:
                with open(adhkar_file, 'r', encoding='utf-8') as f:
                    self.adhkar_data = json.load(f)
            print(f"INFO: Successfully loaded {len(self.adhkar_data)} adhkar categories")
        except Exception as e:
            print(f"ERROR: Failed to load adhkar data: {e}")
            QMessageBox.critical(None, "Error", f"Failed to load adhkar data: {e}")

    def get_adhkar(self, category):
        """الحصول على الأذكار لفئة معينة بتنسيق HTML"""
        if category not in self.adhkar_data:
            return None
        
        html = """
        <div style='font-family: Arial; font-size: 14px; line-height: 1.6; background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px;'>
            <h2 style='color: #2c3e50; text-align: center; margin-bottom: 20px;'>أذكار {}</h2>
        """.format(self.lm.get_string(f"{category}_adhkar", f"أذكار {category}"))
        
        for dhikr in self.adhkar_data[category]:
            html += """
            <div style='margin-bottom: 30px; padding: 15px; background-color: rgba(255, 255, 255, 0.7); border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <p style='font-size: 20px; color: #2c3e50; text-align: right; margin-bottom: 10px;'>{}</p>
            """.format(dhikr['text'])
            
            if 'count' in dhikr and dhikr['count'] > 1:
                html += """
                <p style='color: #7f8c8d; text-align: right; margin: 5px 0;'>
                    <span style='font-weight: bold;'>التكرار:</span> {} مرات
                </p>
                """.format(dhikr['count'])
            
            if 'benefit' in dhikr:
                html += """
                <p style='color: #27ae60; font-style: italic; text-align: right; margin: 5px 0;'>
                    <span style='font-weight: bold;'>الفضل:</span> {}
                </p>
                """.format(dhikr['benefit'])
            
            html += "</div>"
        
        html += "</div>"
        return html

    def get_categories(self):
        return list(self.adhkar_data.keys())

    def get_random_dhikr(self):
        all_adhkar = []
        for category in self.adhkar_data.values():
            all_adhkar.extend(category)
        if all_adhkar:
            return random.choice(all_adhkar)
        return None

    def get_category_dhikr(self, category):
        adhkar = self.adhkar_data.get(category, [])
        if adhkar:
            return random.choice(adhkar)
        return None 