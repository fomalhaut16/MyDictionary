# mydict.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Optional, List
from collections import defaultdict
from fastapi.staticfiles import StaticFiles



# =====================
# DB セットアップ
# =====================
# SQLite ファイルを作成 (relative path: ./dictionary.db)
DATABASE_URL = "sqlite:///./dictionary.db"


# create_engine: DB 接続を表すオブジェクトを作る
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# sessionmaker: DB セッションを作るためのファクトリ
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base: ORM のベースクラス
Base = declarative_base()

# =====================
# モデル定義 (Term)
# =====================
class Term(Base):
    __tablename__ = "terms"
    id = Column(Integer, primary_key=True, index=True)           # 自動採番ID
    word = Column(String, unique=True, index=True, nullable=False)    # 用語（表示名）
    reading = Column(String, index=True, nullable=True)          # カナ読み - 任意（五十音順整列の補助）
    description = Column(Text, nullable=False)                   # 説明文（長文可）
    image_url = Column(String, nullable=True)                    # 画像URL（任意）

# テーブルを作成（無ければ作る）
Base.metadata.create_all(bind=engine)

# =====================
# FastAPI アプリ本体
# =====================
app = FastAPI(title="MyDictionary (Terms)")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic 用のスキーマ（受け取り／返却用）
class TermCreate(BaseModel):
    word: str
    reading: Optional[str] = None
    description: str
    image_url: Optional[str] = None

class TermOut(BaseModel):
    id: int
    word: str
    reading: Optional[str] = None
    description: str
    image_url: Optional[str] = None

# Dependency helper: セッション取得
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# ---------------------
# エンドポイント
# ---------------------

@app.get("/", response_model=dict)
def read_root():
    return {"message": "Welcome to MyDictionary (Terms) API"}

@app.get("/add", response_class=HTMLResponse)
def add_page(request: Request):
    return templates.TemplateResponse("add.html", {"request": request})

@app.post("/add_term", response_model=dict)
def add_term(item: TermCreate):
    """
    新しい用語を追加する。
    JSON ボディで { "word": "...", "reading": "...", "description": "...", "image_url": "..." }
    """
    session = SessionLocal()
    try:
        # 重複チェック（word がユニーク）
        existing = session.query(Term).filter(Term.word == item.word).first()
        if existing:
            raise HTTPException(status_code=400, detail="その用語は既に存在します。")

        term = Term(
            word=item.word,
            reading=item.reading,
            description=item.description,
            image_url=item.image_url,
        )
        session.add(term)
        session.commit()
        session.refresh(term)
        return {"message": f"{term.word} を追加しました。", "id": term.id}
    finally:
        session.close()

@app.get("/terms")
def get_terms():
    """
    全用語を五十音順グループで返す。
    """
    session = SessionLocal()
    try:
        terms = session.query(Term).all()

        grouped = defaultdict(list)
        for term in terms:
            if not term.reading:
                group = "その他"
            else:
                first_char = term.reading[0]
                if first_char in "あいうえお":
                    group = "あ行"
                elif first_char in "かきくけこがぎぐげご":
                    group = "か行"
                elif first_char in "さしすせそざじずぜぞ":
                    group = "さ行"
                elif first_char in "たちつてとだぢづでど":
                    group = "た行"
                elif first_char in "なにぬねの":
                    group = "な行"
                elif first_char in "はひふへほばびぶべぼぱぴぷぺぽ":
                    group = "は行"
                elif first_char in "まみむめも":
                    group = "ま行"
                elif first_char in "やゆよ":
                    group = "や行"
                elif first_char in "らりるれろ":
                    group = "ら行"
                elif first_char in "わをん":
                    group = "わ行"
                else:
                    group = "その他"
            grouped[group].append({
                "word": term.word,
                "reading": term.reading,
                "description": term.description,
                "image_url": term.image_url
            })

        order = ["あ行","か行","さ行","た行","な行","は行","ま行","や行","ら行","わ行","その他"]
        sorted_grouped = {g: grouped[g] for g in order if g in grouped}

        return sorted_grouped
    finally:
        session.close()

@app.get("/term/{term_id}", response_model=TermOut)
def get_term(term_id: int):
    session = SessionLocal()
    try:
        t = session.get(Term, term_id)
        if not t:
            raise HTTPException(status_code=404, detail="Term not found")
        return TermOut(
            id=t.id,
            word=t.word,
            reading=t.reading,
            description=t.description,
            image_url=t.image_url,
        )
    finally:
        session.close()

# ---------------------
# HTML を返すエンドポイント（ブラウザ用）
# ---------------------
@app.get("/web", response_class=HTMLResponse)
def show_terms_page(request: Request):
    """
    用語一覧をHTMLで表示する
    """
    session = SessionLocal()
    terms = session.query(Term).order_by(Term.word).all()
    session.close()
    return templates.TemplateResponse("index.html", {"request": request, "terms": terms})
