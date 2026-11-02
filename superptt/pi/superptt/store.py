import os, sqlite3, threading, time, wave
SCHEMA = """create table if not exists seg(id integer primary key, channel text, speaker_id text,
speaker text, t_start real, t_end real, wav text, status text, engine text, lang text, text text);
create index if not exists seg_t on seg(t_start);"""
class Store:
    def __init__(self, data_dir, rate):
        self.dir, self.rate = data_dir, rate
        os.makedirs(os.path.join(data_dir, "rec"), exist_ok=True)
        self.db = sqlite3.connect(os.path.join(data_dir, "superptt.db"), check_same_thread=False)
        self.db.executescript(SCHEMA); self.lock = threading.Lock()
        for col in ("route text", "cloud_state text", "cloud_reason text", "local_text text", "local_engine text"):
            try: self.db.execute("alter table seg add column " + col)
            except sqlite3.OperationalError: pass
        self.db.commit()
    def save(self, st):
        pcm = st.samples(); dur = len(pcm) / self.rate
        t_end = st.t0 + dur
        day = time.strftime("%Y-%m-%d", time.localtime(st.t0))
        d = os.path.join(self.dir, "rec", day, st.ch); os.makedirs(d, exist_ok=True)
        safe = "".join(ch if ch.isalnum() else "_" for ch in st.name)[:30]
        rel = os.path.join(day, st.ch, time.strftime("%H%M%S", time.localtime(st.t0)) + f"_{safe}.wav")
        with wave.open(os.path.join(self.dir, "rec", rel), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(self.rate); w.writeframes(pcm.tobytes())
        with self.lock:
            cur = self.db.execute("insert into seg(channel,speaker_id,speaker,t_start,t_end,wav,status) values(?,?,?,?,?,?,?)",
                                  (st.ch, st.sid, st.name, st.t0, t_end, rel, "queued"))
            self.db.commit(); return cur.lastrowid, pcm, dur
    def set_text(self, sid, status, engine=None, lang=None, text=None):
        with self.lock:
            self.db.execute("update seg set status=?,engine=?,lang=?,text=?,route=coalesce(route,'local'),"
                            "local_text=?,local_engine=? where id=?", (status, engine, lang, text, text, engine, sid))
            self.db.commit()
    def set_cloud(self, sid, text, lang, engine, reason):
        with self.lock:
            self.db.execute("update seg set status='done',text=?,lang=coalesce(?,lang),engine=?,route='cloud',"
                            "cloud_state='done',cloud_reason=? where id=?", (text, lang, engine, reason, sid))
            self.db.commit()
    def mark_cloud(self, sid, state, reason):
        with self.lock:
            self.db.execute("update seg set cloud_state=?,cloud_reason=? where id=?", (state, reason, sid)); self.db.commit()
    def cloud_pending(self):
        with self.lock:
            return self.db.execute("select id,channel,wav,lang,cloud_reason from seg where cloud_state in ('retry','nokey') and wav is not null "
                                   "and t_start > strftime('%s','now')-86400*3 order by t_start").fetchall()
    def pending(self):
        with self.lock:
            return self.db.execute("select id,channel,wav from seg where status in ('queued','pending') and wav is not null order by t_start").fetchall()
    def counts(self):
        with self.lock:
            a, b, c = self.db.execute("select count(*), sum(wav is not null), min(t_start) from seg").fetchone()
            return a, b or 0, c
    def audio_older(self, t):
        with self.lock: return self.db.execute("select id,wav from seg where wav is not null and t_start<?", (t,)).fetchall()
    def oldest_audio(self, n):
        with self.lock: return self.db.execute("select id,wav from seg where wav is not null order by t_start limit ?", (n,)).fetchall()
    def drop_audio(self, sid):
        with self.lock: self.db.execute("update seg set wav=null where id=?", (sid,)); self.db.commit()
    def delete_older(self, t, rm):
        with self.lock: rows = self.db.execute("select id,wav from seg where t_start<?", (t,)).fetchall()
        for sid, w in rows:
            if w: rm(w)
        with self.lock:
            self.db.execute("delete from seg where t_start<?", (t,)); self.db.commit()
        return len(rows)
    def timeline(self, since=0, channels=None, limit=200):
        q = "select id,channel,speaker,t_start,t_end,wav,status,text,lang,engine,route,cloud_state,cloud_reason,local_text from seg where t_start>=?"
        a = [since]
        if channels:
            q += " and channel in (%s)" % ",".join("?" * len(channels)); a += channels
        q += " order by t_start desc limit ?"; a.append(limit)
        with self.lock: rows = self.db.execute(q, a).fetchall()
        rows = [dict(zip(["id", "channel", "speaker", "t_start", "t_end", "wav", "status", "text", "lang", "engine", "route", "cloud_state", "cloud_reason", "local_text"], r)) for r in rows][::-1]
        # mark overlaps (interval intersection, any channel)
        for i, r in enumerate(rows):
            r["overlaps"] = [o["id"] for o in rows if o is not r and o["t_start"] < r["t_end"] and r["t_start"] < o["t_end"]]
        return rows
