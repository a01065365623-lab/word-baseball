from ..extensions import db


class Word(db.Model):
    __tablename__ = "words"

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    meaning = db.Column(db.String(200), nullable=False)   # Korean meaning
    difficulty = db.Column(db.Integer, default=1)          # 1=easy 2=medium 3=hard
    category = db.Column(db.String(50), default="general")

    def to_dict(self):
        return {
            "id": self.id,
            "word": self.word,
            "meaning": self.meaning,
            "difficulty": self.difficulty,
            "category": self.category,
        }
