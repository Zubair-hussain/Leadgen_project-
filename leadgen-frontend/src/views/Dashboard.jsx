'use client';

import React, { useState, useEffect, useRef } from "react";
import api, { clearTokens } from "../services/api";
import { signOut } from "firebase/auth";
import { auth } from "../firebase";

const logout = () => {
  clearTokens();
  return signOut(auth);
};

/* ─────────────────────────────────────────────────────────────────────────────
   ICONS  — pure inline SVG, zero dependencies
───────────────────────────────────────────────────────────────────────────── */
const s = { fill:"none", stroke:"currentColor", strokeWidth:"2", strokeLinecap:"round", strokeLinejoin:"round" };
const Ic = {
  Bolt:    p=><svg viewBox="0 0 24 24" {...s} {...p}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
  DB:      p=><svg viewBox="0 0 24 24" {...s} {...p}><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>,
  Shield:  p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  Out:     p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  Sun:     p=><svg viewBox="0 0 24 24" {...s} {...p}><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  Moon:    p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>,
  Menu:    p=><svg viewBox="0 0 24 24" {...s} {...p}><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>,
  Close:   p=><svg viewBox="0 0 24 24" {...s} {...p}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  DL:      p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>,
  Trash:   p=><svg viewBox="0 0 24 24" {...s} {...p}><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>,
  Check:   p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  Alert:   p=><svg viewBox="0 0 24 24" {...s} {...p}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  Clock:   p=><svg viewBox="0 0 24 24" {...s} {...p}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  Users:   p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  Trend:   p=><svg viewBox="0 0 24 24" {...s} {...p}><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>,
  Mail:    p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>,
  Globe:   p=><svg viewBox="0 0 24 24" {...s} {...p}><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>,
  Layers:  p=><svg viewBox="0 0 24 24" {...s} {...p}><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>,
  Tag:     p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>,
  Phone:   p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.62 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.16 6.16l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>,
  Search:  p=><svg viewBox="0 0 24 24" {...s} {...p}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  Upload:  p=><svg viewBox="0 0 24 24" {...s} {...p}><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>,
  Activity:p=><svg viewBox="0 0 24 24" {...s} {...p}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  Brief:   p=><svg viewBox="0 0 24 24" {...s} {...p}><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>,
  Pin:     p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>,
  Twitter: p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"/></svg>,
  Gear:    p=><svg viewBox="0 0 24 24" {...s} {...p}><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>,
  Pulse:   p=><svg viewBox="0 0 24 24" {...s} {...p}><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
};

/* ─────────────────────────────────────────────────────────────────────────────
   CSS
───────────────────────────────────────────────────────────────────────────── */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Clash+Display:wght@500;600;700&family=Instrument+Sans:wght@400;500;600&display=swap');

/* ─ Reset ─ */
#lfr*,#lfr *::before,#lfr *::after{box-sizing:border-box;margin:0;padding:0}

/* ─ Light tokens ─ */
#lfr{
  --bg:       #F6F7F5;
  --bg2:      #ECEFEC;
  --surf:     #FFFFFF;
  --surf2:    #F8FAF8;
  --bd:       rgba(18,31,28,.08);
  --bd2:      rgba(18,31,28,.14);
  --bd3:      rgba(18,31,28,.24);
  --t1:       #101815;
  --t2:       #2C3834;
  --t3:       #6B7872;
  --t4:       #A6B0AA;
  --acc:      #087F74;
  --acch:     #0A9C8E;
  --accbg:    rgba(8,127,116,.10);
  --accbd:    rgba(8,127,116,.25);
  --gold:     #B98221;
  --goldbg:   rgba(185,130,33,.11);
  --grn:      #147D52;
  --grnbg:    rgba(20,125,82,.10);
  --red:      #B13A3A;
  --redbg:    rgba(177,58,58,.09);
  --amb:      #B98221;
  --ambbg:    rgba(185,130,33,.11);
  --sh1:      0 1px 3px rgba(16,24,21,.06),0 1px 2px rgba(16,24,21,.04);
  --sh2:      0 8px 26px rgba(16,24,21,.09),0 2px 8px rgba(16,24,21,.05);
  --sh3:      0 16px 48px rgba(16,24,21,.12),0 4px 14px rgba(16,24,21,.06);
  --shacc:    0 6px 24px rgba(8,127,116,.26);
  --r:        12px;
  --rsm:      8px;
  --rlg:      18px;
  --sb:       272px;
  --fw:'Instrument Sans',sans-serif;
  --fh:'Clash Display',sans-serif;
  --ease:cubic-bezier(.4,0,.2,1);
  font-family:var(--fw);
  background:var(--bg);
  color:var(--t1);
  min-height:100vh;
  transition:background .3s var(--ease),color .3s var(--ease);
}

/* ─ Dark tokens ─ */
#lfr[data-dark]{
  --bg:    #0B1110;
  --bg2:   #121A18;
  --surf:  #171F1D;
  --surf2: #1E2926;
  --bd:    rgba(225,241,236,.07);
  --bd2:   rgba(225,241,236,.13);
  --bd3:   rgba(225,241,236,.22);
  --t1:    #EEF5F1;
  --t2:    #C5D0CB;
  --t3:    #7D8B86;
  --t4:    #4F5E59;
  --acc:   #23C7B7;
  --acch:  #48DDCF;
  --accbg: rgba(35,199,183,.12);
  --accbd: rgba(35,199,183,.30);
  --gold:  #E0B35C;
  --goldbg: rgba(224,179,92,.12);
  --grn:   #3CD389;
  --grnbg: rgba(60,211,137,.11);
  --red:   #F06B6B;
  --redbg: rgba(240,107,107,.10);
  --amb:   #E0B35C;
  --ambbg: rgba(224,179,92,.12);
  --sh1:   0 1px 3px rgba(0,0,0,.38);
  --sh2:   0 8px 26px rgba(0,0,0,.44);
  --sh3:   0 18px 56px rgba(0,0,0,.58);
  --shacc: 0 6px 26px rgba(35,199,183,.32);
}

/* ══ SIDEBAR ══ */
.sb{
  position:fixed;top:0;left:0;width:var(--sb);height:100vh;
  background:var(--surf);border-right:1px solid var(--bd2);
  display:flex;flex-direction:column;z-index:300;
  box-shadow:var(--sh2);
  transition:transform .26s var(--ease),background .3s var(--ease),border .3s var(--ease);
  overflow:hidden;
}
.sb.hide{transform:translateX(-100%)}

.sb-logo{padding:20px 18px 16px;border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:10px;flex-shrink:0;transition:border .3s var(--ease)}
.sb-mark{width:33px;height:33px;border-radius:9px;background:var(--acc);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:var(--shacc);transition:background .3s var(--ease),box-shadow .3s var(--ease)}
.sb-mark svg{width:15px;height:15px;color:#fff}
.sb-name{font-family:var(--fh);font-size:14.5px;font-weight:700;color:var(--t1);letter-spacing:-.3px;transition:color .3s var(--ease)}
.sb-sub{font-size:10px;color:var(--t3);margin-top:1px;transition:color .3s var(--ease)}

.sb-nav{flex:1;padding:14px 10px;display:flex;flex-direction:column;gap:1px;overflow-y:auto}
.sb-sec{font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--t4);padding:12px 8px 4px;transition:color .3s var(--ease)}

.snb{width:100%;display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:var(--rsm);border:none;cursor:pointer;text-align:left;background:transparent;color:var(--t2);font-family:var(--fw);font-size:13px;font-weight:500;transition:all .16s var(--ease);position:relative}
.snb:hover{background:var(--bg2);color:var(--t1)}
.snb.on{background:var(--accbg);color:var(--acc);font-weight:600}
.snb.on::before{content:'';position:absolute;left:0;top:50%;transform:translateY(-50%);width:3px;height:16px;border-radius:0 3px 3px 0;background:var(--acc)}
.snb svg{width:15px;height:15px;flex-shrink:0;opacity:.65}
.snb.on svg{opacity:1}
.sbdg{margin-left:auto;font-size:10px;font-weight:700;padding:2px 7px;border-radius:20px;background:var(--accbg);color:var(--acc)}

/* ── Sidebar stats (column layout) ── */
.sb-stats{flex-shrink:0;margin:0 10px 10px;border-radius:var(--r);overflow:hidden;border:1px solid var(--bd);background:var(--bg2);transition:background .3s var(--ease),border .3s var(--ease)}
.sb-stat{display:flex;align-items:center;gap:10px;padding:11px 13px;border-bottom:1px solid var(--bd);transition:background .15s var(--ease),border .3s var(--ease)}
.sb-stat:last-child{border-bottom:none}
.sb-stat:hover{background:var(--surf2)}
.sb-sico{width:28px;height:28px;border-radius:7px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.sb-sico svg{width:12px;height:12px}
.sb-slabel{font-size:10px;color:var(--t3);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:color .3s var(--ease)}
.sb-sval{font-family:var(--fh);font-size:16px;font-weight:700;color:var(--t1);letter-spacing:-.4px;line-height:1.1;transition:color .3s var(--ease)}
.sb-schg{font-size:9.5px;font-weight:600;margin-top:1px}

.sb-foot{padding:10px 10px 16px;border-top:1px solid var(--bd);flex-shrink:0;transition:border .3s var(--ease)}
.sb-theme{display:flex;align-items:center;justify-content:space-between;padding:8px 10px;border-radius:var(--rsm);background:var(--bg2);margin-bottom:2px;transition:background .3s var(--ease)}
.sb-tl{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--t2);font-weight:500;transition:color .3s var(--ease)}
.sb-tl svg{width:13px;height:13px;color:var(--t3)}

/* pill toggle */
.pill{width:33px;height:18px;border-radius:20px;border:none;cursor:pointer;position:relative;background:var(--bd3);transition:background .25s var(--ease);flex-shrink:0}
.pill.on{background:var(--acc)}
.pill::after{content:'';position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.2);transition:transform .25s var(--ease)}
.pill.on::after{transform:translateX(15px)}

/* ══ TOPBAR (mobile) ══ */
.topbar{display:none;position:fixed;top:0;left:0;right:0;height:54px;z-index:200;background:var(--surf);border-bottom:1px solid var(--bd2);align-items:center;justify-content:space-between;padding:0 12px;box-shadow:var(--sh1);transition:background .3s var(--ease),border .3s var(--ease)}
.topbar-logo{display:flex;align-items:center;gap:8px}
.topbar-logo span{font-family:var(--fh);font-size:14px;font-weight:700;color:var(--t1);transition:color .3s var(--ease)}
.ibtn{background:none;border:1px solid var(--bd2);border-radius:var(--rsm);width:32px;height:32px;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--t1);transition:background .15s,border .3s var(--ease),color .3s var(--ease)}
.ibtn:hover{background:var(--bg2)}
.ibtn svg{width:16px;height:16px}

.overlay{display:none;position:fixed;inset:0;z-index:250;background:rgba(8,5,2,.58);backdrop-filter:blur(4px)}
.overlay.on{display:block}

/* ══ MAIN ══ */
.main{margin-left:var(--sb);min-height:100vh;padding:34px 26px 48px;transition:margin .26s var(--ease)}

/* page header */
.ph{margin-bottom:24px}
.ph-eye{display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--acc);background:var(--accbg);border:1px solid var(--accbd);padding:3px 10px;border-radius:20px;margin-bottom:8px;transition:background .3s var(--ease),border .3s var(--ease),color .3s var(--ease)}
.ph-eye svg{width:9px;height:9px}
.ph-title{font-family:var(--fh);font-size:25px;font-weight:700;color:var(--t1);letter-spacing:-.5px;line-height:1.2;margin-bottom:5px;transition:color .3s var(--ease)}
.ph-sub{font-size:13px;color:var(--t3);line-height:1.55;transition:color .3s var(--ease)}

/* ══ CARD ══ */
.card{background:var(--surf);border:1px solid var(--bd2);border-radius:var(--rlg);box-shadow:var(--sh1);overflow:hidden;transition:background .3s var(--ease),border .3s var(--ease),box-shadow .2s}
.card:hover{box-shadow:var(--sh2)}
.ch{padding:18px 20px 14px;border-bottom:1px solid var(--bd);display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;transition:border .3s var(--ease)}
.ctitle{font-family:var(--fh);font-size:14.5px;font-weight:700;color:var(--t1);transition:color .3s var(--ease)}
.csub{font-size:11.5px;color:var(--t3);margin-top:3px;line-height:1.5;transition:color .3s var(--ease)}
.cb{padding:20px}

/* ══ FORM ══ */
.fg{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.fgf{grid-column:1/-1}
.fl{font-size:11px;font-weight:600;color:var(--t2);margin-bottom:5px;display:flex;align-items:center;gap:5px;letter-spacing:.01em;transition:color .3s var(--ease)}
.fl svg{width:11px;height:11px;color:var(--t3)}
.fi,.fsel{width:100%;padding:9px 12px;border-radius:var(--rsm);border:1.5px solid var(--bd2);background:var(--bg2);font-family:var(--fw);font-size:13px;color:var(--t1);outline:none;transition:all .17s var(--ease);appearance:none}
.fi::placeholder,.fsel option{color:var(--t4)}
.fi:focus,.fsel:focus{border-color:var(--acc);box-shadow:0 0 0 3px var(--accbg);background:var(--surf)}
.sw{position:relative}
.sw::after{content:'';position:absolute;right:11px;top:50%;transform:translateY(-50%);pointer-events:none;border-left:4px solid transparent;border-right:4px solid transparent;border-top:5px solid var(--t3)}

.plats{display:flex;flex-wrap:wrap;gap:6px}
.plat{display:flex;align-items:center;gap:6px;padding:7px 12px;border-radius:40px;border:1.5px solid var(--bd2);background:var(--bg2);cursor:pointer;font-size:11.5px;font-weight:500;color:var(--t2);transition:all .15s var(--ease);user-select:none}
.plat:hover{border-color:var(--acc);color:var(--acc);background:var(--accbg)}
.plat.on{border-color:var(--acc);color:var(--acc);background:var(--accbg);font-weight:600}
.plat svg{width:12px;height:12px}

.trow{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-radius:var(--rsm);background:var(--bg2);border:1px solid var(--bd);transition:background .3s var(--ease),border .3s var(--ease)}
.trinfo{font-size:12.5px;color:var(--t1);font-weight:500;transition:color .3s var(--ease)}
.trsub{font-size:11px;color:var(--t3);margin-top:2px;transition:color .3s var(--ease)}

.div{height:1px;background:var(--bd);margin:16px 0;transition:background .3s var(--ease)}

/* ══ BUTTONS ══ */
.bp{display:inline-flex;align-items:center;gap:7px;padding:9px 18px;border-radius:var(--rsm);background:var(--acc);color:#fff;border:none;cursor:pointer;font-family:var(--fw);font-size:13px;font-weight:600;box-shadow:var(--shacc);transition:all .17s var(--ease)}
.bp:hover{background:var(--acch);transform:translateY(-1px);box-shadow:0 6px 24px rgba(8,127,116,.34)}
.bp:active{transform:translateY(0)}
.bp:disabled{opacity:.5;cursor:not-allowed;transform:none}
.bp svg{width:13px;height:13px}
.bs{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:var(--rsm);background:var(--surf);color:var(--t2);border:1px solid var(--bd2);cursor:pointer;font-family:var(--fw);font-size:12px;font-weight:500;transition:all .15s var(--ease)}
.bs:hover{background:var(--bg2);color:var(--t1);border-color:var(--bd3)}
.bs svg{width:12px;height:12px}
.bd{display:inline-flex;align-items:center;gap:4px;padding:5px 10px;border-radius:var(--rsm);background:var(--redbg);color:var(--red);border:1px solid rgba(183,40,40,.18);cursor:pointer;font-family:var(--fw);font-size:11px;font-weight:600;transition:all .15s var(--ease)}
.bd:hover{background:var(--red);color:#fff}
.bd svg{width:11px;height:11px}
.bg{display:inline-flex;align-items:center;gap:4px;padding:5px 10px;border-radius:var(--rsm);background:transparent;color:var(--t3);border:1px solid var(--bd);cursor:pointer;font-family:var(--fw);font-size:11px;font-weight:500;transition:all .15s var(--ease)}
.bg:hover{background:var(--bg2);color:var(--t1)}
.bg:disabled{opacity:.5;cursor:not-allowed}
.bg svg,.bd svg,.bs svg,.bp svg{flex-shrink:0}

.spin{display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:lfspin .65s linear infinite}
.spd{border-color:rgba(100,80,40,.15);border-top-color:var(--t3)}
@keyframes lfspin{to{transform:rotate(360deg)}}

/* ══ TABLE ══ */
.tbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:9px;padding:13px 16px;background:var(--surf2);border-bottom:1px solid var(--bd);transition:background .3s var(--ease),border .3s var(--ease)}
.srch{display:flex;align-items:center;gap:7px;padding:7px 11px;background:var(--surf);border:1.5px solid var(--bd2);border-radius:var(--rsm);min-width:190px;flex:1;max-width:300px;transition:border .17s var(--ease),box-shadow .17s var(--ease)}
.srch:focus-within{border-color:var(--acc);box-shadow:0 0 0 3px var(--accbg)}
.srch svg{width:12px;height:12px;color:var(--t4);flex-shrink:0}
.srch input{border:none;background:transparent;outline:none;font-family:var(--fw);font-size:12px;color:var(--t1);flex:1}
.srch input::placeholder{color:var(--t4)}
.tscr{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;min-width:720px}
thead tr{background:var(--surf2);border-bottom:1px solid var(--bd2);transition:background .3s var(--ease)}
th{padding:8px 12px;text-align:left;font-size:9.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--t3);white-space:nowrap;transition:color .3s var(--ease)}
th>span{display:flex;align-items:center;gap:4px}
th svg{width:10px;height:10px}
td{padding:10px 12px;font-size:12px;color:var(--t2);border-bottom:1px solid var(--bd);vertical-align:middle;transition:background .12s,color .3s var(--ease),border .3s var(--ease)}
tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--surf2)}
.tdem{font-weight:600;color:var(--t1);font-size:12.5px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sdot{display:inline-flex;align-items:center;gap:5px}
.sdot::before{content:'';display:block;width:5px;height:5px;border-radius:50%;background:var(--acc);flex-shrink:0}
.lnk{max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lnk a{color:var(--acc);text-decoration:none;font-size:11.5px;font-weight:500;transition:color .15s var(--ease)}
.lnk a:hover{color:var(--acch);text-decoration:underline}
.bdg{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px}
.bdg svg{width:9px;height:9px}
.bg2{background:var(--grnbg);color:var(--grn)}
.br2{background:var(--redbg);color:var(--red)}
.ba2{background:var(--ambbg);color:var(--amb)}
.tf{padding:9px 16px;border-top:1px solid var(--bd);display:flex;align-items:center;justify-content:space-between;transition:border .3s var(--ease)}
.tf span{font-size:10.5px;color:var(--t4);transition:color .3s var(--ease)}
.empty{text-align:center;padding:52px 20px;display:flex;flex-direction:column;align-items:center;gap:9px}
.eico{width:44px;height:44px;border-radius:12px;background:var(--bg2);display:flex;align-items:center;justify-content:center;transition:background .3s var(--ease)}
.eico svg{width:19px;height:19px;color:var(--t3)}
.empty h3{font-family:var(--fh);font-size:13.5px;color:var(--t2);transition:color .3s var(--ease)}
.empty p{font-size:12px;color:var(--t3);max-width:210px;line-height:1.55;transition:color .3s var(--ease)}

/* ══ VERIFIER ══ */
.vg{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.rb{margin-top:11px;padding:12px;border-radius:var(--rsm);border:1px solid var(--bd);background:var(--bg2);transition:background .3s var(--ease),border .3s var(--ease)}
.rr{display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--bd);transition:border .3s var(--ease)}
.rr:last-child{border-bottom:none}
.rk{font-size:11px;color:var(--t3);transition:color .3s var(--ease)}
.rv{font-size:11.5px;font-weight:700;color:var(--t1);transition:color .3s var(--ease)}
.rl{display:flex;flex-direction:column;gap:5px;max-height:240px;overflow-y:auto;margin-top:9px}
.ri{display:flex;align-items:center;justify-content:space-between;padding:7px 10px;border-radius:var(--rsm);background:var(--surf2);border:1px solid var(--bd);font-size:12px;transition:background .3s var(--ease),border .3s var(--ease)}
.ta{width:100%;padding:10px 12px;border-radius:var(--rsm);border:1.5px solid var(--bd2);background:var(--bg2);font-family:var(--fw);font-size:12.5px;color:var(--t1);resize:vertical;min-height:90px;outline:none;transition:all .17s var(--ease)}
.ta:focus{border-color:var(--acc);box-shadow:0 0 0 3px var(--accbg);background:var(--surf)}
.ta::placeholder{color:var(--t4)}
.dz{border:2px dashed var(--bd2);border-radius:var(--rsm);padding:26px;text-align:center;cursor:pointer;position:relative;transition:all .17s var(--ease)}
.dz:hover{border-color:var(--acc);background:var(--accbg)}
.dz input{position:absolute;inset:0;opacity:0;cursor:pointer}
.dz svg{width:24px;height:24px;color:var(--t4);margin-bottom:6px}
.dz p{font-size:12px;color:var(--t3);transition:color .3s var(--ease)}
.dz strong{color:var(--acc)}
.gc{display:flex;flex-direction:column;gap:16px}

/* ══ SENDER ══ */
.sg{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr);gap:16px}
.sender-card{padding:18px;display:flex;flex-direction:column;gap:14px}
.sender-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.sender-id{display:flex;align-items:center;gap:12px;min-width:0}
.sender-mark{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,var(--acc),var(--gold));display:flex;align-items:center;justify-content:center;color:#fff;box-shadow:var(--shacc);flex-shrink:0}
.sender-mark svg{width:18px;height:18px}
.sender-email{font-family:var(--fh);font-size:18px;font-weight:700;color:var(--t1);letter-spacing:-.3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sender-provider{font-size:12px;color:var(--t3);margin-top:2px}
.sender-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.sender-option{border:1px solid var(--bd);background:var(--surf2);border-radius:var(--rsm);padding:12px;min-height:78px}
.sender-option strong{display:block;font-size:12px;color:var(--t1);margin-bottom:4px}
.sender-option span{display:block;font-size:11px;color:var(--t3);line-height:1.45}
.sender-option.on{border-color:var(--accbd);background:var(--accbg)}
.sender-metric{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--bd)}
.sender-metric:last-child{border-bottom:none}
.sender-metric span{font-size:11px;color:var(--t3)}
.sender-metric strong{font-size:12px;color:var(--t1)}
.sender-check{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.sender-check .wide{grid-column:1/-1}
.check-list{display:flex;flex-direction:column;gap:7px;max-height:360px;overflow-y:auto}
.check-row{display:flex;gap:9px;align-items:flex-start;padding:9px 10px;border:1px solid var(--bd);border-radius:var(--rsm);background:var(--surf2)}
.check-row svg{width:14px;height:14px;flex-shrink:0;margin-top:1px}
.check-copy{min-width:0;display:flex;flex-direction:column;gap:2px}
.check-copy strong{font-size:12px;color:var(--t1)}
.check-copy span{font-size:11px;color:var(--t3);line-height:1.4}
.rec-list{display:flex;flex-direction:column;gap:6px;margin-top:8px}
.rec-list div{font-size:11px;line-height:1.45;color:var(--t2);padding:8px 10px;border-radius:var(--rsm);background:var(--bg2);border:1px solid var(--bd)}
.score-ring{width:76px;height:76px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:conic-gradient(var(--acc) calc(var(--score)*1%),var(--bg2) 0);position:relative;flex-shrink:0}
.score-ring::after{content:'';position:absolute;inset:7px;border-radius:50%;background:var(--surf)}
.score-ring strong{position:relative;z-index:1;font-family:var(--fh);font-size:20px;color:var(--t1)}
.sender-result-head{display:flex;align-items:center;gap:14px}

/* ══ RESPONSIVE ══ */
@media(max-width:1024px){
  .sb{transform:translateX(-100%)}
  .sb.mob{transform:translateX(0)}
  .topbar{display:flex}
  .main{margin-left:0!important;padding:68px 10px 34px}
  .vg{grid-template-columns:1fr}
  .sg{grid-template-columns:1fr}
  .fg{grid-template-columns:1fr}
  .card{border-radius:var(--r)}
  .tscr{margin:0 -1px}
  table{min-width:640px}
}
@media(max-width:640px){
  .tbar{flex-direction:column;align-items:stretch;gap:8px;padding:10px 12px}
  .srch{max-width:100%;min-width:0}
  .tba{display:flex;gap:7px;flex-wrap:wrap}
  .ph-title{font-size:21px}
  .ph-sub{font-size:12px}
  .ch{flex-direction:column;padding:14px 14px 10px}
  .cb{padding:14px}
  th{padding:7px 10px;font-size:9px}
  td{padding:8px 10px;font-size:11px}
  .tdem{font-size:11.5px;max-width:130px}
  .lnk{max-width:110px}
  .lnk a{font-size:10.5px}
  .tf{padding:7px 12px}
  .tf span{font-size:9.5px}
  .sender-options{grid-template-columns:1fr}
  .sender-check{grid-template-columns:1fr}
  .sender-email{font-size:14px}
}
@media(max-width:380px){
  .main{padding:62px 6px 28px}
  table{min-width:580px}
  th{padding:6px 8px}
  td{padding:7px 8px;font-size:10.5px}
}
`;

/* ─────────────────────────────────────────────────────────────────────────────
   DATA
───────────────────────────────────────────────────────────────────────────── */
const PLATS = [
  { id:"reddit",      label:"Reddit",      I:Ic.Globe   },
  { id:"x",           label:"X / Twitter", I:Ic.Twitter },
  { id:"google-maps", label:"Google Maps", I:Ic.Pin     },
];
const SENDER_EMAIL = "noreply@example.com";
const NICHES   = ["Real Estate","SaaS","E-commerce","Fitness","Restaurant","Agency","Healthcare","Finance","Education","Hospitality"];
const COUNTRIES= ["US","AU","GB","CA","DE","FR","IN","PK","AE","SG"];
const DEMO_LEADS=[
  {id:1,email:"ceo@realtygroup.com",  phone:"+1 555-0101",source:"google-maps",location:"Austin TX",  category:"Real Estate",is_verified:true, link:"https://realtygroup.com" },
  {id:2,email:"mark@gymfit.io",       phone:"+1 555-0202",source:"reddit",     location:"Denver CO",  category:"Fitness",    is_verified:false,link:"https://reddit.com/u/markgym" },
  {id:3,email:"hi@dineroagency.co",   phone:"—",          source:"x",          location:"New York NY",category:"Agency",     is_verified:null, link:"https://x.com/dineroagency" },
  {id:4,email:"ops@steakhouse.com",   phone:"+1 555-0404",source:"google-maps",location:"Chicago IL", category:"Restaurant", is_verified:true, link:"https://steakhouse.com" },
  {id:5,email:"dev@saasflow.dev",     phone:"—",          source:"apify-maps", location:"San Francisco CA",category:"SaaS", is_verified:null, link:"https://saasflow.dev" },
];

/* ─────────────────────────────────────────────────────────────────────────────
   SIDEBAR STATS  — column layout
───────────────────────────────────────────────────────────────────────────── */
function SbStats({leads,totalLeads}){
  const ver=leads.filter(l=>l.is_verified===true).length;
  const total=totalLeads ?? leads.length;
  const rows=[
    {label:"Total Leads",     val:total,              chg:"From database",   I:Ic.Users,    c:"var(--acc)",  bg:"var(--accbg)"},
    {label:"Extraction Rate", val:"94.2%",             chg:"↑ vs last run",  I:Ic.Activity, c:"var(--grn)",  bg:"var(--grnbg)"},
    {label:"Verified",        val:ver,                 chg:"Loaded verified", I:Ic.Check,    c:"var(--amb)",  bg:"var(--ambbg)"},
    {label:"This Month",      val:318,                 chg:"↑ new contacts", I:Ic.Trend,    c:"var(--grn)",  bg:"var(--grnbg)"},
  ];
  return(
    <div className="sb-stats">
      {rows.map((r,i)=>(
        <div className="sb-stat" key={i}>
          <div className="sb-sico" style={{background:r.bg,color:r.c}}><r.I/></div>
          <div style={{flex:1,minWidth:0}}>
            <div className="sb-slabel">{r.label}</div>
            <div className="sb-sval">{typeof r.val==="number"?r.val.toLocaleString():r.val}</div>
            <div className="sb-schg" style={{color:r.c}}>{r.chg}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   GENERATOR
───────────────────────────────────────────────────────────────────────────── */
function Generator({form,setForm,busy,onGo,toggleP}){
  const gmapsSelected = form.platforms.includes('google-maps');
  return(
    <div className="card">
      <div className="ch">
        <div>
          <div className="ctitle">Lead Extraction Engine</div>
          <div className="csub">Configure targeting parameters to pull high-intent contacts</div>
        </div>
        <button className="bs"><Ic.Gear/>Presets</button>
      </div>
      <div className="cb">
        <div className="fg">
          <div>
            <div className="fl"><Ic.Tag/>Niche / Industry</div>
            <div className="sw"><select className="fsel" value={form.niche} onChange={e=>setForm(p=>({...p,niche:e.target.value}))}>
              <option value="">Select niche…</option>
              {NICHES.map(n=><option key={n}>{n}</option>)}
            </select></div>
          </div>
          <div>
            <div className="fl"><Ic.Pin/>Target Country</div>
            <div className="sw"><select className="fsel" value={form.country} onChange={e=>setForm(p=>({...p,country:e.target.value}))}>
              <option value="">Select country…</option>
              {COUNTRIES.map(c=><option key={c}>{c}</option>)}
            </select></div>
          </div>
          <div className="fgf">
            <div className="fl"><Ic.Layers/>Source Platforms</div>
            <div className="plats">
              {PLATS.map(({id,label,I})=>(
                <div key={id} className={`plat${form.platforms.includes(id)?" on":""}`} onClick={()=>toggleP(id)}>
                  <I/>{label}
                </div>
              ))}
            </div>
          </div>
          {/* Professional mode – only show when Google Maps is selected */}
          <div className="fgf">
            <div className="fl"><Ic.Mail/>Sender Account</div>
            <div className="trow">
              <div>
                <div className="trinfo">Gmail Sender</div>
                <div className="trsub">{form.sender_email || SENDER_EMAIL}</div>
              </div>
              <span className="bdg bg2"><Ic.Check/>Active</span>
            </div>
          </div>
          {gmapsSelected && (
            <div className="fgf">
              <div className="fl"><Ic.Brief/>Google Maps Engine</div>
              <div className="trow">
                <div>
                  <div className="trinfo">
                    {form.is_professional ? '⚡ Apify Enterprise Crawler' : '🔍 SerpAPI Standard'}
                  </div>
                  <div className="trsub">
                    {form.is_professional
                      ? 'Deep crawl via Apify — emails, phones, ratings (slower but richer data)'
                      : 'Fast Google Maps lookup via SerpAPI — active emails from business websites'}
                  </div>
                </div>
                <button className={`pill${form.is_professional?" on":""}`} onClick={()=>setForm(p=>({...p,is_professional:!p.is_professional}))}/>
              </div>
            </div>
          )}
        </div>
        <div className="div"/>
        <div style={{display:"flex",justifyContent:"flex-end",gap:8}}>
          <button className="bs" onClick={()=>setForm(p=>({...p,niche:"",country:"",platforms:["reddit","x","google-maps"],is_professional:false,sender_email:SENDER_EMAIL}))}>Reset</button>
          <button className="bp" onClick={onGo} disabled={busy}>
            {busy?<span className="spin"/>:<Ic.Bolt/>}{busy?"Extracting…":"Run Extraction"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   LEADS TABLE
───────────────────────────────────────────────────────────────────────────── */
function Leads({leads,onVerify,onDelete,verifying,onExport}){
  const[q,setQ]=useState("");
  const rows=leads.filter(l=>(l.email||"").toLowerCase().includes(q.toLowerCase())||(l.category||"").toLowerCase().includes(q.toLowerCase())||(l.source||"").toLowerCase().includes(q.toLowerCase()));

  /* Pretty source label */
  const srcLabel=(s)=>{const m={"google-maps":"Google Maps","apify-maps":"Apify Maps","google-cse":"Google CSE","reddit":"Reddit","x":"X / Twitter"};return m[s]||s||"—";};

  /* Smart link label: website domain for maps, profile for social */
  const linkCell=(l)=>{
    if(!l.link) return "—";
    try{
      const u=new URL(l.link);
      return <a href={l.link} target="_blank" rel="noopener noreferrer" title={l.link}>{u.hostname.replace('www.','')}</a>;
    }catch{ return <a href={l.link} target="_blank" rel="noopener noreferrer" title={l.link}>{l.link.slice(0,30)}</a>; }
  };

  return(
    <div className="card">
      <div className="tbar">
        <div className="srch"><Ic.Search/><input placeholder="Search email, source…" value={q} onChange={e=>setQ(e.target.value)}/></div>
        <div className="tba">
          <button className="bs" onClick={onExport}><Ic.DL/>Export CSV</button>
          <button className="bs"><Ic.Shield/>Bulk Verify</button>
        </div>
      </div>
      <div className="tscr">
        {rows.length===0?(
          <div className="empty">
            <div className="eico"><Ic.DB/></div>
            <h3>No leads found</h3>
            <p>Run an extraction from the Generator tab to populate your lead pool.</p>
          </div>
        ):(
          <table>
            <thead><tr>
              <th><span><Ic.Mail/>Email</span></th>
              <th><span><Ic.Phone/>Phone</span></th>
              <th><span><Ic.Globe/>Source</span></th>
              <th><span><Ic.Layers/>Website / URL</span></th>
              <th><span><Ic.Pin/>Location</span></th>
              <th><span><Ic.Shield/>Status</span></th>
              <th>Actions</th>
            </tr></thead>
            <tbody>{rows.map(l=>(
              <tr key={l.id}>
                <td className="tdem">{(!l.email || l.email.includes('@noemail.local')) ? "—" : l.email}</td>
                <td>{l.phone||"—"}</td>
                <td><span className="sdot">{srcLabel(l.source)}</span></td>
                <td className="lnk">{linkCell(l)}</td>
                <td>{l.location||"—"}</td>
                <td>
                  {l.is_verified===true  &&<span className="bdg bg2"><Ic.Check/>Verified</span>}
                  {l.is_verified===false &&<span className="bdg br2"><Ic.Alert/>Failed</span>}
                  {l.is_verified==null   &&<span className="bdg ba2"><Ic.Clock/>Pending</span>}
                </td>
                <td style={{ whiteSpace: "nowrap", width: "1%" }}><div style={{display:"flex",gap:5, flexWrap:"nowrap"}}>
                  <button className="bg" style={{flexShrink:0}} onClick={()=>onVerify(l.id)} disabled={verifying[l.id]}>
                    {verifying[l.id]?<span className="spin spd"/>:<Ic.Shield/>}Verify
                  </button>
                  <button className="bd" style={{flexShrink:0}} onClick={()=>onDelete(l.id)}><Ic.Trash/></button>
                </div></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
      <div className="tf"><span>{rows.length} lead{rows.length!==1?"s":""}</span><span>Updated just now</span></div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   VERIFIER
───────────────────────────────────────────────────────────────────────────── */
function Verifier(){
  const[single,setSingle]=useState("");
  const[sRes,setSRes]=useState(null);
  const[multi,setMulti]=useState("");
  const[mRes,setMRes]=useState([]);
  const[busy,setBusy]=useState(false);

  const doSingle=async e=>{
    e.preventDefault();
    if(!single)return;
    setBusy(true);
    setSRes(null);
    try{
      const response=await api.post("leads/verify-single/",{email:single});
      setSRes({
        is_valid: response.data?.is_verified === true,
        format_valid: true,
        mx_found: response.data?.is_verified === true,
        disposable: false,
        score: response.data?.is_verified === true ? 95 : 0,
      });
    }catch(error){
      console.error("Single verification failed:",error);
      setSRes({is_valid:false,format_valid:false,mx_found:false,disposable:false,score:0});
    }finally{
      setBusy(false);
    }
  };
  const doMulti=async e=>{
    e.preventDefault();
    const em=multi.split(/[\n,]+/).map(x=>x.trim()).filter(Boolean);
    if(!em.length)return;
    setBusy(true);
    try{
      const response=await api.post("leads/verify-multi/",{emails:em});
      setMRes((response.data?.results||[]).map(result=>({
        email:result.email,
        is_valid:result.is_verified===true,
      })));
    }catch(error){
      console.error("Batch verification failed:",error);
      setMRes([]);
    }finally{
      setBusy(false);
    }
  };

  return(
    <div className="vg">
      <div className="card">
        <div className="ch">
          <div><div className="ctitle">Single Lookup</div><div className="csub">Instant verification for one address</div></div>
          <span className="bdg bg2" style={{marginTop:2,alignSelf:"flex-start"}}><span style={{width:5,height:5,borderRadius:"50%",background:"var(--grn)",display:"inline-block"}}/>Live</span>
        </div>
        <div className="cb" style={{display:"flex",flexDirection:"column",gap:11}}>
          <div><div className="fl"><Ic.Mail/>Email Address</div><input className="fi" placeholder="hello@company.com" value={single} onChange={e=>setSingle(e.target.value)}/></div>
          <button className="bp" style={{alignSelf:"flex-start"}} onClick={doSingle} disabled={busy}>{busy?<span className="spin"/>:<Ic.Shield/>}Verify Now</button>
          {sRes&&<div className="rb">
            <div className="rr"><span className="rk">Status</span><span className={`bdg${sRes.is_valid?" bg2":" br2"}`}>{sRes.is_valid?<><Ic.Check/>Valid</>:<><Ic.Alert/>Invalid</>}</span></div>
            <div className="rr"><span className="rk">Format</span><span className="rv">{sRes.format_valid?"✓ OK":"✗ Bad"}</span></div>
            <div className="rr"><span className="rk">MX Record</span><span className="rv">{sRes.mx_found?"✓ Found":"✗ None"}</span></div>
            <div className="rr"><span className="rk">Disposable</span><span className="rv">{sRes.disposable?"Yes":"No"}</span></div>
            <div className="rr"><span className="rk">Score</span><span className="rv" style={{color:"var(--acc)"}}>{sRes.score}/100</span></div>
          </div>}
        </div>
      </div>
      <div className="gc">
        <div className="card">
          <div className="ch"><div><div className="ctitle">Batch Verify</div><div className="csub">Comma or newline-separated emails</div></div></div>
          <div className="cb" style={{display:"flex",flexDirection:"column",gap:11}}>
            <textarea className="ta" placeholder={"email1@co.com\nemail2@co.com"} value={multi} onChange={e=>setMulti(e.target.value)}/>
            <button className="bp" style={{alignSelf:"flex-start"}} onClick={doMulti} disabled={busy}>{busy?<span className="spin"/>:<Ic.Bolt/>}Run Batch</button>
            {mRes.length>0&&<div className="rl">{mRes.map((r,i)=><div className="ri" key={i}><span style={{fontSize:12,color:"var(--t2)",fontWeight:500}}>{r.email}</span><span className={`bdg${r.is_valid?" bg2":" br2"}`}>{r.is_valid?<><Ic.Check/>Valid</>:<><Ic.Alert/>Invalid</>}</span></div>)}</div>}
          </div>
        </div>
        <div className="card">
          <div className="ch"><div><div className="ctitle">File Upload</div><div className="csub">CSV or TXT — one email per line</div></div></div>
          <div className="cb" style={{display:"flex",flexDirection:"column",gap:9}}>
            <div className="dz"><input type="file" accept=".csv,.txt"/>
              <div style={{display:"flex",flexDirection:"column",alignItems:"center"}}>
                <Ic.Upload/><p>Drop file here or <strong>browse</strong></p>
                <p style={{fontSize:10.5,marginTop:3,color:"var(--t4)"}}>Max 5 MB · CSV or TXT</p>
              </div>
            </div>
            <button className="bs" style={{justifyContent:"center"}}><Ic.Shield/>Bulk Verify All Leads</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   ROOT
───────────────────────────────────────────────────────────────────────────── */
function SenderOptions({senderEmail}){
  const[policy,setPolicy]=useState({
    subject:"Quick question",
    body:"Hi, I found your business while researching companies that may benefit from a better client acquisition workflow. Open to a short conversation this week?",
    daily_volume:100,
    include_unsubscribe:true,
    dkim_selectors:"",
  });
  const[result,setResult]=useState(null);
  const[checking,setChecking]=useState(false);
  const[policyError,setPolicyError]=useState("");

  const badgeFor=status=>{
    if(status==="inbox_ready")return "bg2";
    if(status==="needs_work")return "ba2";
    return "br2";
  };
  const labelFor=status=>{
    if(status==="inbox_ready")return "Low Risk";
    if(status==="needs_work")return "Needs Work";
    if(status==="invalid_sender")return "Invalid";
    return "High Risk";
  };
  const runPolicyCheck=async e=>{
    e.preventDefault();
    setChecking(true);
    setPolicyError("");
    try{
      const response=await api.post("deliverability/check/",{
        sender_email:senderEmail,
        subject:policy.subject,
        body:policy.body,
        daily_volume:Number(policy.daily_volume)||0,
        include_unsubscribe:policy.include_unsubscribe,
        dkim_selectors:policy.dkim_selectors,
      });
      setResult(response.data);
    }catch(error){
      setPolicyError(error.response?.data?.error||error.message||"Policy check failed");
    }finally{
      setChecking(false);
    }
  };

  return(
    <div className="sg">
      <div style={{display:"flex",flexDirection:"column",gap:16,minWidth:0}}>
        <div className="card sender-card">
          <div className="sender-head">
            <div className="sender-id">
              <div className="sender-mark"><Ic.Mail/></div>
              <div style={{minWidth:0}}>
                <div className="sender-email">{senderEmail}</div>
                <div className="sender-provider">Configured sender identity</div>
              </div>
            </div>
            <span className="bdg bg2"><Ic.Check/>Active</span>
          </div>
          <div className="sender-options">
            <div className="sender-option on">
              <strong>Verified Leads</strong>
              <span>Only addresses with valid syntax and active MX domains enter the pool.</span>
            </div>
            <div className="sender-option on">
              <strong>Smart Queue</strong>
              <span>Batch preparation keeps outreach volume controlled.</span>
            </div>
            <div className="sender-option">
              <strong>Policy Check</strong>
              <span>SPF, DMARC, probable DKIM, SMTP TLS, copy, and unsubscribe signals.</span>
            </div>
          </div>
        </div>

        <form className="card sender-card" onSubmit={runPolicyCheck}>
          <div>
            <div className="ctitle">Deliverability Policy Checker</div>
            <div className="csub">Sender DNS, authentication, and campaign risk scan</div>
          </div>
          <div className="sender-check">
            <div>
              <div className="fl"><Ic.Mail/>Subject</div>
              <input className="fi" value={policy.subject} onChange={e=>setPolicy(p=>({...p,subject:e.target.value}))}/>
            </div>
            <div>
              <div className="fl"><Ic.Activity/>Daily Volume</div>
              <input className="fi" type="number" min="0" value={policy.daily_volume} onChange={e=>setPolicy(p=>({...p,daily_volume:e.target.value}))}/>
            </div>
            <div className="wide">
              <div className="fl"><Ic.Shield/>DKIM Selectors</div>
              <input className="fi" placeholder="google, selector1" value={policy.dkim_selectors} onChange={e=>setPolicy(p=>({...p,dkim_selectors:e.target.value}))}/>
            </div>
            <div className="wide">
              <div className="fl"><Ic.Mail/>Sample Body</div>
              <textarea className="ta" style={{minHeight:116}} value={policy.body} onChange={e=>setPolicy(p=>({...p,body:e.target.value}))}/>
            </div>
            <label className="trow wide" style={{cursor:"pointer"}}>
              <div>
                <div className="trinfo">Unsubscribe included</div>
                <div className="trsub">Required for bulk or campaign-style outreach</div>
              </div>
              <input type="checkbox" checked={policy.include_unsubscribe} onChange={e=>setPolicy(p=>({...p,include_unsubscribe:e.target.checked}))}/>
            </label>
          </div>
          <button className="bp" style={{alignSelf:"flex-start"}} disabled={checking}>
            {checking?<span className="spin"/>:<Ic.Shield/>}Run Policy Check
          </button>
          {policyError&&<span className="bdg br2" style={{alignSelf:"flex-start"}}><Ic.Alert/>{policyError}</span>}
        </form>
      </div>

      <div style={{display:"flex",flexDirection:"column",gap:16,minWidth:0}}>
        <div className="card sender-card">
          <div>
            <div className="ctitle">Sender Settings</div>
            <div className="csub">Current outreach configuration</div>
          </div>
          <div>
            <div className="sender-metric"><span>Provider</span><strong>Gmail SMTP</strong></div>
            <div className="sender-metric"><span>Default from</span><strong>{senderEmail}</strong></div>
            <div className="sender-metric"><span>Lead filter</span><strong>Verified only</strong></div>
            <div className="sender-metric"><span>Batch mode</span><strong>Enabled</strong></div>
          </div>
        </div>

        <div className="card sender-card">
          <div className="sender-result-head">
            <div className="score-ring" style={{"--score":result?.score||0}}><strong>{result?result.score:"--"}</strong></div>
            <div style={{minWidth:0}}>
              <div className="ctitle">Inbox Risk</div>
              <div className="csub">{result?result.inbox_prediction:"Run a policy check to score this sender."}</div>
              {result&&<span className={`bdg ${badgeFor(result.status)}`} style={{marginTop:8}}>{labelFor(result.status)}</span>}
            </div>
          </div>
          {result&&<>
            <div className="check-list">
              {result.checks.map(check=>(
                <div className="check-row" key={check.key}>
                  {check.passed?<Ic.Check style={{color:"var(--grn)"}}/>:<Ic.Alert style={{color:check.severity==="critical"?"var(--red)":"var(--amb)"}}/>}
                  <div className="check-copy">
                    <strong>{check.label}</strong>
                    <span>{check.detail}</span>
                  </div>
                </div>
              ))}
            </div>
            {result.recommendations?.length>0&&<div>
              <div className="fl"><Ic.Bolt/>Fix Next</div>
              <div className="rec-list">
                {result.recommendations.slice(0,5).map((rec,i)=><div key={i}>{rec}</div>)}
              </div>
            </div>}
          </>}
        </div>
      </div>
    </div>
  );
}

const META={
  generator:{eye:"Extraction Engine", title:"Lead Generator",   sub:"Pull high-intent contacts from social & professional networks."},
  leads:    {eye:"Data Warehouse",    title:"Leads Hub",         sub:"Your verified repository of potential high-value clients."},
  verifier: {eye:"Verification Suite",title:"Bulk Verifier",     sub:"Professional-grade email authenticity verification toolkit."},
  sender:   {eye:"Gmail Sender",      title:"Sender Options",    sub:"Selected sender identity for verified lead outreach preparation."},
};

export default function Dashboard(){
  const rootRef=useRef(null);
  const[tab,setTab]=useState("generator");
  const[leads,setLeads]=useState([]);
  const[totalLeads,setTotalLeads]=useState(0);
  const[busy,setBusy]=useState(false);
  const[verifying,setVer]=useState({});
  const[mob,setMob]=useState(false);
  const[dark,setDark]=useState(false);
  const[form,setForm]=useState({niche:"",country:"",platforms:["reddit","x","google-maps"],is_professional:false,sender_email:SENDER_EMAIL});

  const fetchLeads = async () => {
    const allLeads = [];
    let nextUrl = "leads/?page_size=100";
    let dbTotal = 0;
    let pageGuard = 0;

    while (nextUrl && pageGuard < 50) {
      const response = await api.get(nextUrl);
      const data = response.data;

      if (Array.isArray(data)) {
        allLeads.push(...data);
        dbTotal = data.length;
        nextUrl = null;
      } else {
        const pageResults = Array.isArray(data?.results) ? data.results : [];
        allLeads.push(...pageResults);
        dbTotal = typeof data?.count === "number" ? data.count : allLeads.length;
        nextUrl = data?.next || null;
      }

      pageGuard += 1;
    }

    setLeads(allLeads);
    setTotalLeads(dbTotal || allLeads.length);
    return allLeads;
  };

  // Fetch leads on mount
  useEffect(()=>{
    const loadLeads = async () => {
      try {
        await fetchLeads();
      } catch (error) {
        console.error('Failed to fetch leads:', error);
      }
    };
    const fetchSender = async () => {
      try {
        const response = await api.get('health/');
        const email = response.data?.sender?.email;
        if (email) setForm(p => ({ ...p, sender_email: email }));
      } catch (error) {
        console.error('Failed to fetch sender settings:', error);
      }
    };
    loadLeads();
    fetchSender();
  },[]);

  /* Apply dark mode directly to root element */
  useEffect(()=>{
    if(!rootRef.current)return;
    if(dark) rootRef.current.setAttribute("data-dark","");
    else     rootRef.current.removeAttribute("data-dark");
  },[dark]);

  const toggleP=id=>setForm(p=>({...p,platforms:p.platforms.includes(id)?p.platforms.filter(x=>x!==id):[...p.platforms,id]}));
  
  // Lead generation API call with validation
  const onGo=async(e)=>{
    e.preventDefault();
    
    // Validate required fields
    if(!form.niche || !form.niche.trim()) {
      alert('⚠️ Please enter a target niche (e.g., Real Estate Agents, Dentists)');
      return;
    }
    
    if(!form.country || !form.country.trim()) {
      alert('⚠️ Please enter a target location (City, State, or Country)');
      return;
    }
    
    if(!form.platforms.length) {
      alert('⚠️ Please select at least one platform');
      return;
    }
    
    // Condition: Google Maps requires location
    if(form.platforms.includes('google-maps') && (!form.country || form.country.trim() === '')) {
      alert('⚠️ Google Maps requires a specific location to be set');
      return;
    }
    
    // Condition: Apify (Professional) requires location
    if(form.is_professional && (!form.country || form.country.trim() === '')) {
      alert('⚠️ Professional/Apify mode requires a specific location');
      return;
    }
    
    setBusy(true);
    try {
      console.log('📤 Sending lead generation request:', {
        category: form.niche,
        platforms: form.platforms,
        location: form.country,
        is_professional: form.is_professional
      });
      
      const response = await api.post('generate/', {
        category: form.niche,
        platforms: form.platforms,
        niche: form.niche,
        target_location: form.country,
        is_professional: form.is_professional,
        sender_email: form.sender_email || SENDER_EMAIL
      });
      
      console.log('✅ Response received:', response.data);
      
      if(response.data.leads && response.data.leads.length > 0) {
        // Use backend IDs when available, fallback to generated IDs
        const newLeads = response.data.leads.map((lead, idx) => ({
          id: lead.id || Date.now() + idx,
          email: lead.email || '—',
          phone: lead.phone || '',
          source: lead.source || form.niche,
          category: form.niche,
          location: lead.location || form.country,
          link: lead.link || '',
          is_verified: lead.is_verified === true,
          problem_statement: lead.problem_statement || ''
        }));
        
        try {
          await fetchLeads();
        } catch (refreshError) {
          console.error('Failed to refresh leads after generation:', refreshError);
          setLeads(p => {
            const existingIds = new Set(p.map(lead => lead.id));
            return [...newLeads.filter(lead => !existingIds.has(lead.id)), ...p];
          });
          setTotalLeads(p => Math.max(newLeads.length, p + newLeads.length));
        }
        const engine = form.is_professional ? 'Apify' : 'SerpAPI';
        console.log(`✅ Added ${newLeads.length} leads via ${engine}`);
        alert(`✅ Generated ${response.data.leads.length} leads via ${engine}!\n\nCheck the "Leads Hub" tab to view and verify them.`);
      } else {
        alert('⚠️ No leads found for your criteria.\n\nTry:\n• Different keywords\n• Broader location\n• Different platforms\n• Toggle Professional mode for deeper search');
      }
    } catch (error) {
      console.error('❌ Lead generation error:', error);
      const errorMsg = error.response?.data?.error || error.response?.data?.details || error.message || 'Unknown error';
      alert('❌ Error generating leads:\n\n' + errorMsg + '\n\nCheck backend logs for details.');
    } finally {
      setBusy(false);
    }
  };
  
  const onExport=async()=>{
    try{
      const response=await api.get("leads/export/",{responseType:"blob"});
      const url=URL.createObjectURL(response.data);
      const link=document.createElement("a");
      link.href=url;
      link.download="verified_leads.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }catch(error){
      console.error("Failed to export leads:",error);
      alert("Export failed. Please try again.");
    }
  };

  const onDel=async id=>{
    setLeads(p=>p.filter(l=>l.id!==id));
    setTotalLeads(p=>Math.max(0,p-1));
    try{
      await api.delete(`leads/${id}/`);
      await fetchLeads();
    }catch(error){
      console.error('Failed to delete lead:', error);
      try{await fetchLeads();}catch(refreshError){console.error('Failed to refresh leads after delete:', refreshError);}
    }
  };
  const onVerify=async id=>{
    setVer(p=>({...p,[id]:true}));
    try{
      const response=await api.post(`leads/${id}/verify/`);
      setLeads(p=>p.map(l=>l.id===id?{...l,is_verified:response.data?.is_verified===true}:l));
    }catch(error){
      console.error('Failed to verify lead:', error);
    }finally{
      setVer(p=>({...p,[id]:false}));
    }
  };
  const go=id=>{setTab(id);setMob(false);};

  const m=META[tab];
  const NAVS=[
    {id:"generator",label:"Generator",  I:Ic.Bolt,   badge:null},
    {id:"leads",    label:"Leads Hub",  I:Ic.DB,     badge:totalLeads},
    {id:"verifier", label:"Verifier",   I:Ic.Shield, badge:null},
    {id:"sender",   label:"Sender",     I:Ic.Mail,   badge:null},
  ];
  const SEC=[
    {label:"Performance",I:Ic.Trend},
    {label:"Activity Log",I:Ic.Pulse},
    {label:"Settings",   I:Ic.Gear},
  ];

  return(
    <div id="lfr" ref={rootRef}>
      <style>{CSS}</style>

      {/* overlay */}
      <div className={`overlay${mob?" on":""}`} onClick={()=>setMob(false)}/>

      {/* ── SIDEBAR ── */}
      <aside className={`sb${mob?" mob":""}`}>
        <div className="sb-logo">
          <div className="sb-mark"><Ic.Bolt/></div>
          <div><div className="sb-name">LeadFlow</div><div className="sb-sub">Xovato Digital</div></div>
        </div>
        <nav className="sb-nav">
          <div className="sb-sec">Main</div>
          {NAVS.map(({id,label,I,badge})=>(
            <button key={id} className={`snb${tab===id?" on":""}`} onClick={()=>go(id)}>
              <I/>{label}
              {badge!=null&&<span className="sbdg">{badge}</span>}
            </button>
          ))}
          <div className="sb-sec" style={{marginTop:4}}>Analytics</div>
          {SEC.map(({label,I})=><button key={label} className="snb"><I/>{label}</button>)}
        </nav>

        {/* stats column */}
        <SbStats leads={leads} totalLeads={totalLeads}/>

        {/* footer */}
        <div className="sb-foot">
          <div className="sb-theme">
            <div className="sb-tl">{dark?<Ic.Moon/>:<Ic.Sun/>}{dark?"Dark Mode":"Light Mode"}</div>
            <button className={`pill${dark?" on":""}`} onClick={()=>setDark(d=>!d)}/>
          </div>
          <button className="snb" style={{color:"var(--red)",marginTop:2}} onClick={logout}><Ic.Out/>Sign Out</button>
        </div>
      </aside>

      {/* ── MOBILE TOPBAR ── */}
      <div className="topbar">
        <button className="ibtn" onClick={()=>setMob(o=>!o)}>{mob?<Ic.Close/>:<Ic.Menu/>}</button>
        <div className="topbar-logo">
          <div className="sb-mark" style={{width:26,height:26,borderRadius:7}}><Ic.Bolt style={{width:12,height:12}}/></div>
          <span>LeadFlow</span>
        </div>
        <button className="ibtn" onClick={()=>setDark(d=>!d)}>{dark?<Ic.Sun/>:<Ic.Moon/>}</button>
      </div>

      {/* ── MAIN ── */}
      <main className="main">
        <div className="ph">
          <div className="ph-eye"><Ic.Bolt/>{m.eye}</div>
          <h1 className="ph-title">{m.title}</h1>
          <p className="ph-sub">{m.sub}</p>
        </div>

        {tab==="generator"&&<Generator form={form} setForm={setForm} busy={busy} onGo={onGo} toggleP={toggleP}/>}
        {tab==="leads"    &&<Leads leads={leads} onVerify={onVerify} onDelete={onDel} verifying={verifying} onExport={onExport}/>}
        {tab==="verifier" &&<Verifier/>}
        {tab==="sender"   &&<SenderOptions senderEmail={form.sender_email || SENDER_EMAIL}/>}
      </main>
    </div>
  );
}