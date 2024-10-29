http://127.0.0.1:8000/docs


.\venv\Scripts\activate

python -m uvicorn main:app --reload
python -m uvicorn app:app --reload

Start Command uvicorn app:app --host 0.0.0.0 --port 8000
