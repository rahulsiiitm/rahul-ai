"""gui.py — Jarvis HUD Desktop Interface  (Iron Man aesthetic)"""
from __future__ import annotations
import sys, io, threading, json, time, math
from queue import Queue, Empty
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import tkinter as tk
import customtkinter as ctk
from jarvis.ui.hud import HudCanvas

ctk.set_appearance_mode("dark")

BG="#050810"; SURF="#080d18"; CARD="#0c1220"; CARD2="#101828"
SKY="#00BFFF"; SKY2="#87CEEB"; GLOW="#1E90FF"
WHITE="#f0f0f0"; DIM="#445566"; GREEN="#00e676"; RED="#ff5252"; YELLOW="#ffb300"
USR="#0a1e35"; JAR="#0c1220"; TOOL="#061812"
F=("Segoe UI",13); FB=("Segoe UI",13,"bold"); FS=("Segoe UI",11)
FM=("Consolas",11); FT=("Segoe UI",17,"bold"); FC=("Consolas",12,"bold")


class JarvisGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("JARVIS — AI Co-pilot")
        self.root.geometry("1340x780")
        self.root.minsize(1000,640)
        self.root.configure(fg_color=BG)
        self.root.wm_attributes("-alpha", 0.96)

        self._q       = Queue()
        self._running = False
        self._history: list = []
        self._tool_card     = None
        self._recording     = False
        self._voice_on      = True

        self._build()
        self.root.after(100, self._poll)
        self.root.after(400, self._status_check)
        self._clock()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self._topbar()
        body = tk.Frame(self.root, bg=BG); body.pack(fill="both", expand=True)
        self._chat_panel(body)
        self._hud_panel(body)
        self._sidebar(body)
        self._inputbar()

    def _topbar(self):
        bar = ctk.CTkFrame(self.root, fg_color=SURF, height=52, corner_radius=0)
        bar.pack(fill="x"); bar.pack_propagate(False)
        # Left: brand
        ctk.CTkLabel(bar, text="◈  JARVIS", font=("Consolas",18,"bold"), text_color=SKY).pack(side="left",padx=18)
        ctk.CTkLabel(bar, text="Private AI Co-pilot", font=FS, text_color=DIM).pack(side="left")
        # Right: clock + status + clear
        right = ctk.CTkFrame(bar, fg_color="transparent"); right.pack(side="right", padx=14)
        ctk.CTkButton(right, text="Clear", width=58, height=26, font=FS,
                      fg_color=CARD2, hover_color=CARD, text_color=DIM,
                      command=self._clear).pack(side="right", padx=(8,0))
        self._dot_email = ctk.CTkLabel(right, text="● Email", font=FS, text_color=DIM)
        self._dot_email.pack(side="right", padx=6)
        self._dot_llm   = ctk.CTkLabel(right, text="● Mistral", font=FS, text_color=DIM)
        self._dot_llm.pack(side="right", padx=6)
        self._clock_lbl = ctk.CTkLabel(right, text="00:00:00", font=FC, text_color=SKY2)
        self._clock_lbl.pack(side="right", padx=16)

    def _chat_panel(self, parent):
        frame = tk.Frame(parent, bg=SURF, width=320); frame.pack(side="left",fill="y")
        frame.pack_propagate(False)
        hdr = tk.Frame(frame, bg=SURF); hdr.pack(fill="x", padx=12, pady=(10,4))
        tk.Label(hdr, text="CONVERSATION LOG", bg=SURF, fg=SKY,
                 font=("Consolas",10,"bold")).pack(side="left")
        # Horizontal rule
        tk.Frame(frame, bg=GLOW, height=1).pack(fill="x", padx=12)
        # Scrollable chat
        self._chat_canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(frame, orient="vertical", command=self._chat_canvas.yview)
        self._chat_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._chat_canvas.pack(fill="both", expand=True)
        self._chat_inner = tk.Frame(self._chat_canvas, bg=BG)
        self._chat_window = self._chat_canvas.create_window((0,0), window=self._chat_inner, anchor="nw")
        self._chat_inner.bind("<Configure>", self._on_resize)
        self._chat_canvas.bind("<Configure>",
            lambda e: self._chat_canvas.itemconfig(self._chat_window, width=e.width))
        # Welcome
        self._add_jarvis("Online. What do you need, Rahul?")

    def _on_resize(self, e):
        self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))
        self._chat_canvas.yview_moveto(1.0)

    def _hud_panel(self, parent):
        frame = tk.Frame(parent, bg=BG); frame.pack(side="left", fill="both", expand=True)
        top = tk.Frame(frame, bg=BG); top.pack(fill="both", expand=True)
        # HUD canvas centered
        self._hud = HudCanvas(top, size=360)
        self._hud.place(relx=0.5, rely=0.5, anchor="center")
        # Below HUD: stats strip
        stats = tk.Frame(frame, bg=SURF, height=60); stats.pack(fill="x", side="bottom")
        stats.pack_propagate(False)
        self._stat_lbl = tk.Label(stats, text="SYSTEM NOMINAL  ·  LOCAL MODEL  ·  PRIVATE",
                                   bg=SURF, fg=DIM, font=("Consolas",10))
        self._stat_lbl.pack(expand=True)

    def _sidebar(self, parent):
        sb = ctk.CTkFrame(parent, fg_color=SURF, width=255, corner_radius=0)
        sb.pack(side="right", fill="y"); sb.pack_propagate(False)
        # Inbox
        ctk.CTkLabel(sb, text="[ INBOX ]", font=("Consolas",11,"bold"), text_color=SKY
                     ).pack(anchor="w", padx=12, pady=(14,4))
        tk.Frame(sb, bg=GLOW, height=1).pack(fill="x", padx=12)
        self._email_list = ctk.CTkScrollableFrame(sb, fg_color="transparent", height=195)
        self._email_list.pack(fill="x", padx=6, pady=4)
        ctk.CTkButton(sb, text="↻  Refresh Inbox", height=26, font=FS,
                      fg_color=CARD2, hover_color=CARD, text_color=DIM,
                      command=lambda: self._quick("Check my emails for job opportunities")
                      ).pack(fill="x", padx=10, pady=(2,10))
        tk.Frame(sb, bg=CARD2, height=1).pack(fill="x", padx=10)
        # Jobs
        ctk.CTkLabel(sb, text="[ JOB LISTINGS ]", font=("Consolas",11,"bold"), text_color=SKY2
                     ).pack(anchor="w", padx=12, pady=(10,4))
        tk.Frame(sb, bg="#1a2a3a", height=1).pack(fill="x", padx=12)
        self._job_list = ctk.CTkScrollableFrame(sb, fg_color="transparent", height=195)
        self._job_list.pack(fill="x", padx=6, pady=4)
        ctk.CTkLabel(sb, text="Ask Jarvis to scrape jobs", font=FS, text_color=DIM
                     ).pack(anchor="w", padx=12, pady=4)

    def _inputbar(self):
        bot = ctk.CTkFrame(self.root, fg_color=SURF, corner_radius=0)
        bot.pack(fill="x", side="bottom")
        # Quick actions row
        qa = tk.Frame(bot, bg=SURF); qa.pack(fill="x", padx=12, pady=(6,2))
        for label, msg in [("📬 Emails","Check my emails for job opportunities"),
                           ("🔍 Internshala","Scrape ML internships on internshala"),
                           ("🚀 YC Jobs","Scrape jobs on ycombinator"),
                           ("🌐 Wellfound","Scrape ML jobs on wellfound"),
                           ("📄 Score Job","Score this job description:")]:
            ctk.CTkButton(qa, text=label, height=26, font=FS, width=0,
                          fg_color=CARD2, hover_color=CARD, text_color=WHITE,
                          command=lambda m=msg: self._quick(m)
                          ).pack(side="left", padx=(0,6))
        # Input row
        row = tk.Frame(bot, bg=SURF); row.pack(fill="x", padx=12, pady=(2,10))
        self._mic_btn = ctk.CTkButton(row, text="🎤", width=46, height=46,
                                       fg_color=CARD2, hover_color=CARD, text_color=WHITE,
                                       corner_radius=8, font=("Segoe UI",18),
                                       command=self._toggle_mic)
        self._mic_btn.pack(side="left", padx=(0,6))
        self._spk_btn = ctk.CTkButton(row, text="🔊", width=46, height=46,
                                       fg_color=CARD2, hover_color=CARD, text_color=SKY,
                                       corner_radius=8, font=("Segoe UI",18),
                                       command=self._toggle_voice)
        self._spk_btn.pack(side="left", padx=(0,8))
        self._input = ctk.CTkTextbox(row, height=46, font=F, fg_color=CARD,
                                      text_color=WHITE, border_color=SKY, border_width=1,
                                      corner_radius=8, wrap="word")
        self._input.pack(side="left", fill="x", expand=True)
        self._input.bind("<Return>", self._enter)
        self._send_btn = ctk.CTkButton(row, text="SEND ▶", width=90, height=46,
                                        fg_color=SKY, text_color="#000",
                                        hover_color=SKY2, corner_radius=8,
                                        font=("Consolas",12,"bold"), command=self._send)
        self._send_btn.pack(side="right", padx=(8,0))

    # ── Bubbles ───────────────────────────────────────────────────────────────

    def _add_user(self, text: str):
        f = tk.Frame(self._chat_inner, bg=BG); f.pack(fill="x", padx=8, pady=(5,2))
        bub = tk.Frame(f, bg=USR, bd=0); bub.pack(anchor="e")
        tk.Label(bub, text="YOU", bg=USR, fg=SKY,
                 font=("Consolas",9,"bold")).pack(anchor="e", padx=10, pady=(5,0))
        tk.Label(bub, text=text, bg=USR, fg=WHITE, font=F,
                 wraplength=260, justify="left").pack(padx=12, pady=(2,8), anchor="w")
        tk.Frame(f, bg=SKY+"44", height=1).pack(fill="x")
        self._scroll()

    def _add_jarvis(self, text: str):
        f = tk.Frame(self._chat_inner, bg=BG); f.pack(fill="x", padx=8, pady=(5,2))
        row = tk.Frame(f, bg=BG); row.pack(anchor="w")
        av = tk.Frame(row, bg=SKY, width=28, height=28); av.pack(side="left", anchor="n", pady=4)
        av.pack_propagate(False)
        tk.Label(av, text="J", bg=SKY, fg="#000", font=("Consolas",12,"bold")).pack(expand=True)
        bub = tk.Frame(row, bg=JAR, bd=0); bub.pack(side="left", padx=(6,0))
        tk.Label(bub, text="JARVIS", bg=JAR, fg=GLOW,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=10, pady=(5,0))
        tk.Label(bub, text=text, bg=JAR, fg=WHITE, font=F,
                 wraplength=255, justify="left").pack(padx=12, pady=(2,8), anchor="w")
        self._scroll()

    def _add_thought(self, text: str):
        f = tk.Frame(self._chat_inner, bg=BG); f.pack(fill="x", padx=30, pady=1)
        tk.Label(f, text=f"  💭 {text[:100]}", bg=BG, fg=DIM, font=("Consolas",9)).pack(anchor="w")
        self._scroll()

    def _add_tool_card(self, tool: str, args: dict) -> tk.Frame:
        f = tk.Frame(self._chat_inner, bg=BG); f.pack(fill="x", padx=30, pady=(2,1))
        card = tk.Frame(f, bg=TOOL, bd=0); card.pack(anchor="w", fill="x")
        tk.Label(card, text=f"⚙  {tool}", bg=TOOL, fg=GREEN,
                 font=FM).pack(anchor="w", padx=10, pady=(5,0))
        tk.Label(card, text=json.dumps(args)[:85], bg=TOOL, fg=DIM,
                 font=FM).pack(anchor="w", padx=12, pady=(0,5))
        self._scroll(); return card

    def _update_tool(self, card: tk.Frame, result):
        if not card: return
        s = (f"→ {len(result)} result(s)" if isinstance(result,list)
             else f"→ {list(result.keys())[:3]}" if isinstance(result,dict)
             else f"→ {str(result)[:75]}")
        tk.Label(card, text=s, bg=TOOL, fg=SKY, font=FM).pack(anchor="w", padx=12, pady=(0,5))
        self._scroll()

    def _scroll(self):
        self._chat_inner.update_idletasks()
        self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))
        self._chat_canvas.yview_moveto(1.0)

    # ── Agent ─────────────────────────────────────────────────────────────────

    def _send(self):
        text = self._input.get("1.0","end").strip()
        if not text or self._running: return
        self._input.delete("1.0","end"); self._dispatch(text)

    def _quick(self, m: str):
        if self._running: return
        self._dispatch(m)

    def _enter(self, e):
        if not (e.state & 0x1): self._send(); return "break"

    def _dispatch(self, text: str):
        self._add_user(text)
        self._running = True
        self._send_btn.configure(state="disabled", text="...")
        self._hud.set_status("THINKING")
        self._stat_lbl.configure(text="Processing request...")
        def run():
            from jarvis.agent.server_agent import run_agent
            run_agent(text, self._history, self._q)
        threading.Thread(target=run, daemon=True).start()

    def _poll(self):
        try:
            while True: self._handle(self._q.get_nowait())
        except Empty: pass
        self.root.after(80, self._poll)

    def _handle(self, ev: dict):
        t = ev.get("type")
        if   t == "thought":    self._add_thought(ev["content"])
        elif t == "tool_start":
            self._tool_card = self._add_tool_card(ev["tool"], ev.get("args",{}))
            self._hud.set_status("RUNNING")
        elif t == "tool_result":
            self._update_tool(self._tool_card, ev.get("result"))
            r = ev.get("result")
            if ev["tool"]=="read_emails" and isinstance(r,list): self._fill_emails(r)
            if ev["tool"]=="scrape_jobs" and isinstance(r,list): self._fill_jobs(r)
            self._tool_card = None; self._hud.set_status("THINKING")
        elif t == "draft_ready":
            d = ev.get("draft",{})
            self._add_jarvis(f"Draft ready — {d.get('to','?')}\nSubject: {d.get('subject','?')}")
            self._draft_dialog(d)
        elif t == "message":
            msg = ev["content"]; self._add_jarvis(msg)
            self._history.append({"role":"user",      "content":self._last_user()})
            self._history.append({"role":"assistant", "content":msg})
            if len(self._history)>40: self._history=self._history[-40:]
            if self._voice_on:
                from jarvis.voice.tts import speak
                threading.Thread(target=speak, args=(msg,), daemon=True).start()
                self._hud.set_status("SPEAKING")
        elif t == "error":
            f = tk.Frame(self._chat_inner, bg=BG); f.pack(fill="x",padx=12,pady=4)
            tk.Label(f,text=f"⚠  {ev['content']}",bg=BG,fg=RED,font=FS).pack(anchor="w")
            self._scroll()
        elif t == "done":
            self._running=False; self._send_btn.configure(state="normal",text="SEND ▶")
            self._hud.set_status("STANDBY")
            self._stat_lbl.configure(text="SYSTEM NOMINAL  ·  LOCAL MODEL  ·  PRIVATE")

    def _last_user(self)->str:
        for m in reversed(self._history):
            if m.get("role")=="user": return m["content"]
        return ""

    # ── Voice ─────────────────────────────────────────────────────────────────

    def _toggle_mic(self):
        if self._recording:
            self._recording=False
            self._mic_btn.configure(text="🎤", fg_color=CARD2, text_color=WHITE)
            self._hud.set_status("PROCESSING")
            def _trans():
                from jarvis.voice.stt import stop_and_transcribe
                text=stop_and_transcribe()
                if text: self.root.after(0,lambda:self._fill_input(text))
                else: self.root.after(0,lambda:self._hud.set_status("STANDBY"))
            threading.Thread(target=_trans,daemon=True).start()
        else:
            self._recording=True
            self._mic_btn.configure(text="⏹",fg_color=RED,text_color=WHITE)
            self._hud.set_status("LISTENING")
            from jarvis.voice.stt import start_recording
            threading.Thread(target=start_recording,daemon=True).start()

    def _fill_input(self, text:str):
        self._input.delete("1.0","end"); self._input.insert("1.0",text)
        self._hud.set_status("STANDBY")

    def _toggle_voice(self):
        self._voice_on=not self._voice_on
        self._spk_btn.configure(text="🔊" if self._voice_on else "🔇",
                                 text_color=SKY if self._voice_on else DIM)
        if not self._voice_on:
            try:
                from jarvis.voice.tts import stop; stop()
            except: pass

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _fill_emails(self, emails:list):
        for w in self._email_list.winfo_children(): w.destroy()
        for e in emails[:10]:
            if e.get("error"): continue
            c=ctk.CTkFrame(self._email_list,fg_color=CARD,corner_radius=6); c.pack(fill="x",pady=2,padx=2)
            ctk.CTkLabel(c,text=e.get("subject","")[:36],font=FS,text_color=WHITE,
                         wraplength=210,justify="left").pack(anchor="w",padx=8,pady=(4,0))
            ctk.CTkLabel(c,text=e.get("from","")[:30],font=("Segoe UI",10),text_color=DIM
                         ).pack(anchor="w",padx=8,pady=(0,4))

    def _fill_jobs(self, jobs:list):
        for w in self._job_list.winfo_children(): w.destroy()
        for j in jobs[:10]:
            if j.get("error"): continue
            c=ctk.CTkFrame(self._job_list,fg_color=CARD,corner_radius=6); c.pack(fill="x",pady=2,padx=2)
            ctk.CTkLabel(c,text=j.get("title","")[:36],font=FS,text_color=WHITE,
                         wraplength=210,justify="left").pack(anchor="w",padx=8,pady=(4,0))
            ctk.CTkLabel(c,text=f"{j.get('company','')[:20]}  ·  {j.get('source','')}",
                         font=("Segoe UI",10),text_color=SKY2).pack(anchor="w",padx=8,pady=(0,4))

    # ── Draft dialog ──────────────────────────────────────────────────────────

    def _draft_dialog(self, draft:dict):
        dlg=ctk.CTkToplevel(self.root); dlg.title("Draft Email")
        dlg.geometry("640x520"); dlg.configure(fg_color=SURF); dlg.grab_set()
        dlg.wm_attributes("-alpha",0.96)
        ctk.CTkLabel(dlg,text="[ DRAFT EMAIL ]",font=("Consolas",16,"bold"),text_color=SKY).pack(pady=(18,8))
        for lbl,key in [("To:","to"),("Subject:","subject")]:
            row=ctk.CTkFrame(dlg,fg_color="transparent"); row.pack(fill="x",padx=24,pady=2)
            ctk.CTkLabel(row,text=lbl,font=FB,text_color=DIM,width=74).pack(side="left")
            ctk.CTkLabel(row,text=draft.get(key,""),font=F,text_color=WHITE).pack(side="left")
        tk.Frame(dlg,bg=GLOW,height=1).pack(fill="x",padx=24,pady=8)
        body=ctk.CTkTextbox(dlg,font=FS,fg_color=CARD,text_color=WHITE,corner_radius=8,border_width=0)
        body.pack(fill="both",expand=True,padx=24)
        body.insert("1.0",draft.get("body","")); body.configure(state="disabled")
        btns=ctk.CTkFrame(dlg,fg_color="transparent"); btns.pack(pady=14)
        def do_send():
            from jarvis.tools.email_sender import send_pending_draft
            r=send_pending_draft(); dlg.destroy()
            self._add_jarvis("Sent." if r.get("status")=="sent" else f"Failed: {r.get('error')}")
        def do_discard():
            from jarvis.tools.email_sender import discard_draft
            discard_draft(); dlg.destroy(); self._add_jarvis("Draft discarded.")
        ctk.CTkButton(btns,text="SEND",width=130,height=40,font=("Consolas",12,"bold"),
                      fg_color=GREEN,hover_color="#00c060",text_color="#000",command=do_send).pack(side="left",padx=8)
        ctk.CTkButton(btns,text="DISCARD",width=110,height=40,font=("Consolas",12,"bold"),
                      fg_color=CARD2,hover_color=CARD,text_color=RED,command=do_discard).pack(side="left",padx=8)

    # ── Misc ─────────────────────────────────────────────────────────────────

    def _clear(self):
        self._history.clear()
        for w in self._chat_inner.winfo_children(): w.destroy()
        self._add_jarvis("Cleared.")

    def _clock(self):
        import datetime
        self._clock_lbl.configure(text=datetime.datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._clock)

    def _status_check(self):
        def run():
            from jarvis.llm import ping
            from jarvis.config import EMAIL_CONFIGURED
            ok_l,ok_e=ping(),EMAIL_CONFIGURED
            self.root.after(0,lambda:(
                self._dot_llm.configure(text_color=GREEN if ok_l else RED),
                self._dot_email.configure(text_color=GREEN if ok_e else YELLOW)
            ))
            if not ok_l:
                self.root.after(0,lambda:self._add_thought("Ollama offline — run: ollama serve"))
            if not ok_e:
                self.root.after(0,lambda:self._add_thought("Email not set — copy .env.example → .env"))
        threading.Thread(target=run,daemon=True).start()

    def run(self): self.root.mainloop()


if __name__=="__main__":
    JarvisGUI().run()
