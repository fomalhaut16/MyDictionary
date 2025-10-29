from fastapi import FastAPI

app = FastAPI()

dictionary = {}

@app.get("/")
def read_root():
    return {"message": "Welcome to MyDictionary API"}

@app.post("/add")
def add_word(word: str, definition: str):
    dictionary[word] = definition
    return {"message": f"{word} を追加しました"}

@app.get("/get")
def get_word(word: str):
    if word in dictionary:
        return {"word": word, "definition": dictionary[word]}
    else:
        return {"error": "その単語は登録されていません"}
