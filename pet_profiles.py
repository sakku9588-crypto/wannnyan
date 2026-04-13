# pet_profiles.py - ケイくん＆ジェミ猫のプロフィール

class PetProfile:
    def __init__(self, name, pet_type, breed, age, favorite_things):
        self.name = name
        self.pet_type = pet_type
        self.breed = breed
        self.age = age
        self.favorite_things = favorite_things
        self.mood_history = []
        self.conversation_log = []
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.pet_type,
            "breed": self.breed,
            "age": self.age,
            "favorites": self.favorite_things
        }

# ケイくん（ポメラニアン×スピッツ）
KEI_KUN = PetProfile(
    name="ケイくん",
    pet_type="dog",
    breed="ポメラニアン × スピッツ（ポメスピ）",
    age="3歳",
    favorite_things=["おやつ", "お散歩", "ボール遊び", "飼い主の膝"]
)

# ジェミ猫
GEMI_NYAN = PetProfile(
    name="ジェミ猫",
    pet_type="cat",
    breed="ミックス（黒猫っぽい）",
    age="2歳",
    favorite_things=["キャットタワー", "お昼寝", "鳥観察", "段ボール"]
)

# 会話テンプレート
CONVERSATION_TEMPLATES = {
    "dog_happy": "🐶 {name}: 「わんわん！{phrase}」",
    "dog_sad": "🐶 {name}: 「くぅ〜ん...{phrase}」",
    "cat_purr": "🐱 {name}: 「ゴロゴロ...{phrase}」",
    "cat_meow": "🐱 {name}: 「にゃ〜ん！{phrase}」"
}