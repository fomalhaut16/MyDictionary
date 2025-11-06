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
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./terms.db")
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

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

from fastapi import Query

@app.get("/terms", response_model=List[TermOut])
def list_terms(query: str | None = Query(None)):
    """
    全用語を返す。
    ?query= で検索キーワードが指定された場合は部分一致でフィルタ。
    """
    session = SessionLocal()
    try:
        terms = session.query(Term).all()

        # 検索フィルター
        if query:
            query_lower = query.lower()
            terms = [
                t for t in terms
                if query_lower in (t.word.lower() if t.word else "")
                or query_lower in (t.reading.lower() if t.reading else "")
                or query_lower in (t.description.lower() if t.description else "")
            ]

        # ソート（読み→単語順）
        def sort_key(t: Term):
            key = t.reading if t.reading and t.reading.strip() else t.word
            return key
        terms_sorted = sorted(terms, key=sort_key)

        return [
            TermOut(
                id=t.id,
                word=t.word,
                reading=t.reading,
                description=t.description,
                image_url=t.image_url,
            )
            for t in terms_sorted
        ]
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
def serve_web(request: Request, q: Optional[str] = Query(None)):
    session = SessionLocal()
    try:
        # 全件 or 検索条件で絞り込み
        if q:
            terms = session.query(Term).filter(Term.word.contains(q) | Term.description.contains(q)).all()
        else:
            terms = session.query(Term).all()

        # ソート（読み→単語）
        terms_sorted = sorted(terms, key=lambda t: t.reading or t.word)
        return templates.TemplateResponse("index.html", {"request": request, "terms": terms_sorted, "q": q})
    finally:
        session.close()