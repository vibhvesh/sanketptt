import os, re, json, asyncio
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
import psycopg
from psycopg.rows import dict_row

APP_NAME = "Sanket AI Database Copilot"
DATABASE_URL = os.getenv("DATABASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "*").split(",") if x.strip()]
app = FastAPI(title=APP_NAME, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type","Authorization"])
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []

def require_config():
    if not DATABASE_URL:
        raise HTTPException(503, "DATABASE_URL is not configured on the VPS. Create a temporary Prisma Postgres database and set it in the service environment.")
    if not client:
        raise HTTPException(503, "OPENAI_API_KEY is not configured on the VPS.")

def db_connect():
    require_config()
    try:
        return psycopg.connect(DATABASE_URL, connect_timeout=12, sslmode="require", row_factory=dict_row)
    except Exception as e:
        raise HTTPException(502, f"Database connection failed: {str(e)[:300]}")

def schema_snapshot():
    with db_connect() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        tables = conn.execute("""
          SELECT n.nspname AS schema_name, c.relname AS table_name, c.relkind
          FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE c.relkind IN ('r','v','m','p') AND n.nspname NOT IN ('pg_catalog','information_schema')
          ORDER BY n.nspname,c.relname
        """).fetchall()
        cols = conn.execute("""
          SELECT table_schema,table_name,column_name,data_type,is_nullable,column_default,ordinal_position
          FROM information_schema.columns
          WHERE table_schema NOT IN ('pg_catalog','information_schema')
          ORDER BY table_schema,table_name,ordinal_position
        """).fetchall()
        fks = conn.execute("""
          SELECT tc.table_schema,tc.table_name,kcu.column_name,
                 ccu.table_schema AS foreign_table_schema,ccu.table_name AS foreign_table_name,ccu.column_name AS foreign_column_name
          FROM information_schema.table_constraints tc
          JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name AND tc.constraint_schema=kcu.constraint_schema
          JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name AND ccu.constraint_schema=tc.constraint_schema
          WHERE tc.constraint_type='FOREIGN KEY'
          ORDER BY tc.table_schema,tc.table_name,kcu.ordinal_position
        """).fetchall()
    return {"tables":tables,"columns":cols,"relationships":fks}

@app.get("/health")
def health():
    return {"ok":True,"service":APP_NAME,"database_configured":bool(DATABASE_URL),"ai_configured":bool(client),"model":OPENAI_MODEL}

@app.get("/api/schema")
def get_schema():
    snap=schema_snapshot()
    counts={}
    with db_connect() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        for t in snap["tables"]:
            if t["relkind"] not in ("r","p"): continue
            s, name=t["schema_name"],t["table_name"]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",s+name): continue
            try:
                row=conn.execute(f'SELECT COUNT(*) AS n FROM "{s}"."{name}"').fetchone()
                counts[f'{s}.{name}']=row["n"]
            except Exception: counts[f'{s}.{name}']=None
    return {**snap,"row_counts":counts}

def safe_sql(sql: str) -> str:
    q=sql.strip()
    q=re.sub(r"^\s*\`\`\`(?:sql)?\s*|\s*\`\`\`\s*$","",q,flags=re.I)
    if not q: raise HTTPException(400,"No SQL was generated.")
    if ";" in q.rstrip(";"): raise HTTPException(400,"Only one SQL statement is allowed.")
    q=q.rstrip(";").strip()
    if not re.match(r"^(SELECT|WITH|EXPLAIN)\b",q,re.I): raise HTTPException(400,"Only SELECT, WITH and EXPLAIN queries are allowed.")
    forbidden=r"\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|VACUUM|ANALYZE|REFRESH|SET|RESET|DISCARD|LOAD|ATTACH|DETACH|LOCK)\b"
    if re.search(forbidden,q,re.I): raise HTTPException(400,"Read-only mode blocked a modifying or administrative SQL command.")
    if re.search(r"\b(pg_read_file|pg_write_file|lo_import|lo_export|dblink|pg_sleep)\s*\(",q,re.I): raise HTTPException(400,"This function is blocked by the safety policy.")
    return q

def execute_readonly(sql: str):
    q=safe_sql(sql)
    with db_connect() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '8000ms'")
        cur=conn.execute(q)
        if cur.description is None: return {"columns":[],"rows":[],"row_count":0,"sql":q}
        rows=cur.fetchmany(501)
        cols=[d.name for d in cur.description]
    clipped=len(rows)>500
    rows=rows[:500]
    def clean(v):
        if hasattr(v,"isoformat"): return v.isoformat()
        if isinstance(v,(dict,list)): return v
        return v
    return {"columns":cols,"rows":[{k:clean(v) for k,v in r.items()} for r in rows],"row_count":len(rows),"truncated":clipped,"sql":q}

@app.post("/api/query")
def query(payload: dict[str,Any]):
    return execute_readonly(str(payload.get("sql","")))

@app.post("/api/chat")
async def chat(req: ChatRequest):
    require_config()
    if not req.message.strip(): raise HTTPException(400,"Please enter a question.")
    snap=schema_snapshot()
    schema_text=json.dumps(snap,default=str)[:45000]
    recent=[{"role":m["role"],"content":m["content"][:3000]} for m in req.history[-8:] if m.get("role") in ("user","assistant")]
    system=f"""You are Sanket AI Database Copilot, a careful PostgreSQL analyst and SQL tutor.
The user is exploring a disposable temporary PostgreSQL learning database. Database schema metadata follows:
{schema_text}
Rules:
- Answer in clear, helpful language. Infer nothing that schema/data do not support.
- If the user asks for data analysis, generate exactly one read-only PostgreSQL SELECT or WITH query.
- Never generate writes, DDL, multiple statements, privileged functions, or destructive operations.
- Use only tables and columns present in the supplied schema. Quote identifiers when needed.
- Add a LIMIT 100 unless aggregation or a smaller limit is more appropriate.
- Return valid JSON only with keys: message (natural-language response), sql (string or null), chart (object or null), suggestions (array of 3 short follow-up questions).
- chart may be null or {{"type":"bar"|"line"|"pie","x":"column","y":"column","title":"short title"}} and only refer to returned result columns.
- For schema-learning questions, explain available tables and suggest useful analyses. Do not invent query results.
"""
    messages=[{"role":"system","content":system},*recent,{"role":"user","content":req.message}]
    try:
        completion=await client.chat.completions.create(model=OPENAI_MODEL,messages=messages,response_format={"type":"json_object"},temperature=0.2)
        data=json.loads(completion.choices[0].message.content or "{}")
    except Exception as e:
        raise HTTPException(502,f"AI request failed: {str(e)[:250]}")
    sql=data.get("sql")
    result=None
    if sql:
        try:
            result=execute_readonly(sql)
        except HTTPException as e:
            data["message"]=(data.get("message","") + "\n\nI generated SQL, but the safety/validation layer did not execute it: "+str(e.detail)).strip()
            sql=None
    return {"message":data.get("message",""),"sql":sql,"result":result,"chart":data.get("chart"),"suggestions":data.get("suggestions",[])}

@app.get("/api/suggestions")
async def suggestions():
    require_config()
    snap=schema_snapshot()
    prompt="Given this PostgreSQL schema, suggest 8 useful beginner-to-advanced questions users can ask. Return JSON {suggestions:[...]}. Schema: "+json.dumps(snap,default=str)[:35000]
    try:
        r=await client.chat.completions.create(model=OPENAI_MODEL,messages=[{"role":"user","content":prompt}],response_format={"type":"json_object"},temperature=0.3)
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as e: raise HTTPException(502,str(e)[:250])
