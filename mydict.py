from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker

# ==============================
# データベースの準備
# ==============================

# SQLiteのデータベースを作成（ファイル名: dictionary.db）
DATABASE_URL = "sqlite:///./dictionary.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# テーブル定義
class Word(Base):
    __tablename__ = "words"
    word = Column(String, primary_key=True)
    definition = Column(String)

# テーブルを作成
Base.metadata.create_all(bind=engine)

# ==============================
# FastAPIアプリ本体
# ==============================

app = FastAPI()

class WordItem(BaseModel):
    word: str
    definition: str

@app.get("/")
def read_root():
    return {"message": "Welcome to MyDictionary API with Database!"}

@app.post("/add")
def add_word(item: WordItem):
    session = SessionLocal()
    db_word = session.get(Word, item.word)
    if db_word:
        raise HTTPException(status_code=400, detail="この単語はすでに登録されています。")
    new_word = Word(word=item.word, definition=item.definition)
    session.add(new_word)
    session.commit()
    session.close()
    return {"message": f"{item.word} を追加しました。"}

@app.get("/get/{word}")
def get_word(word: str):
    session = SessionLocal()
    db_word = session.get(Word, word)
    session.close()
    if db_word:
        return {"word": db_word.word, "definition": db_word.definition}
    else:
        raise HTTPException(status_code=404, detail="その単語は登録されていません。")
