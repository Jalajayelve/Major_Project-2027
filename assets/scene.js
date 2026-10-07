/* MERIDIAN motion layer. Progressive enhancement only: every page is complete without it.
 *  - Three.js dotted globes (hero / dashboard / agents / landing band), lazy loaded
 *  - scroll reveal, bar grow, count-up numbers, scroll progress line, section index
 *  - 3D card tilt and hero parallax
 * Respects prefers-reduced-motion. Colours come from CSS variables defined in theme.py.
 */
(function () {
  var OS_REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var PREF = null; try { PREF = localStorage.getItem("meridian-motion"); } catch (e) {}
  // Motion is ON unless the visitor chose off, or their system asks for reduced motion and they have not chosen on.
  var reduced = PREF === "off" || (PREF !== "on" && OS_REDUCED);
  var coarse = window.matchMedia("(pointer: coarse)").matches;
  var THREE_SRC = "/three.min.js"; // bundled in assets/ (three r149)
  var ORIGIN = [19.08, 72.88]; // Mumbai

  function css(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  /* ───────────────────────── Shared mouse state ───────────────────────── */
  var M = { x: 0, y: 0, nx: 0, ny: 0, dx: 0, seen: false };
  window.addEventListener("mousemove", function (e) {
    M.x = e.clientX; M.y = e.clientY; M.dx += e.movementX || 0; M.seen = true;
    M.nx = (e.clientX / innerWidth - 0.5) * 2; M.ny = (e.clientY / innerHeight - 0.5) * 2;
  }, { passive: true });

  /* ───────────────────────── Globe ───────────────────────── */
  var landBits = null;
  function isLand(lat, lon) {
    if (!landBits) {
      var s = window.MERIDIAN_LAND; if (!s) return 0;
      var bin = atob(s); landBits = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) landBits[i] = bin.charCodeAt(i);
    }
    var row = clamp(Math.floor(90 - lat), 0, 179), col = clamp(Math.floor(lon + 180), 0, 359);
    var idx = row * 360 + col;
    return (landBits[idx >> 3] >> (7 - (idx & 7))) & 1;
  }
  function latLon(lat, lon, r) {
    var phi = (90 - lat) * Math.PI / 180, th = (lon + 180) * Math.PI / 180;
    return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th));
  }
  function yawFor(lon, lat) { var v = latLon(lat, lon, 1); return Math.atan2(-v.x, v.z); }
  function angDiff(a, b) { var d = (b - a) % (Math.PI * 2); if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2; return d; }
  function dotTexture() {
    var c = document.createElement("canvas"); c.width = c.height = 32;
    var g = c.getContext("2d"); g.fillStyle = "#fff"; g.beginPath(); g.arc(16, 16, 13, 0, 7); g.fill();
    return new THREE.CanvasTexture(c);
  }

  function buildGlobe(canvas) {
    var wrap = canvas.parentElement;
    var mode = canvas.dataset.globe;                  // hero | dash | agents | band
    var unis = []; try { unis = JSON.parse(canvas.dataset.unis || "[]"); } catch (e) {}
    var arcsMode = canvas.dataset.arcs || "all";      // all | first | progress
    var spin = canvas.dataset.spin || "auto";         // auto | scroll | tilt
    var selectable = canvas.dataset.select === "1";
    var draggable = canvas.dataset.drag === "1";

    var renderer;
    try { renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true }); }
    catch (e) { return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, coarse ? 1.5 : 2));
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20); camera.position.set(0, 0, 5.0);

    var navy = new THREE.Color(css("--navy")), navy2 = new THREE.Color(css("--navy-2")), slate = new THREE.Color(css("--slate"));
    var accent = new THREE.Color(css("--accent")), ivory = new THREE.Color(css("--ivory"));
    var onNavy = mode === "band" || mode === "agents";

    var key = new THREE.DirectionalLight(0xfff3e0, 0.75); key.position.set(-3, 3, 4);
    scene.add(key, new THREE.HemisphereLight(0xfff8ee, 0x4a6178, 1.25));

    var outer = new THREE.Group(), globe = new THREE.Group(); outer.add(globe); scene.add(outer);
    globe.add(new THREE.Mesh(new THREE.SphereGeometry(1, 64, 48),
      new THREE.MeshStandardMaterial({ color: onNavy ? navy2 : navy, roughness: 0.85, metalness: 0.02 })));

    // graticule (thin, printed)
    var lineMat = new THREE.LineBasicMaterial({ color: slate, transparent: true, opacity: onNavy ? 0.4 : 0.5 });
    var la, lo, k, pts;
    for (la = -60; la <= 60; la += 30) { pts = []; for (k = 0; k <= 96; k++) pts.push(latLon(la, -180 + k * 3.75, 1.001)); globe.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat)); }
    for (lo = -180; lo < 180; lo += 30) { pts = []; for (k = 0; k <= 64; k++) pts.push(latLon(-90 + k * 2.8125, lo, 1.001)); globe.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat)); }

    // continents as a dotted grid
    var pos = [], step = 2.0;
    for (la = -84; la <= 84; la += step) {
      var n = Math.max(8, Math.round(360 * Math.cos(la * Math.PI / 180) / step));
      for (k = 0; k < n; k++) { lo = -180 + (k + 0.5) * 360 / n; if (isLand(la, lo)) { var v = latLon(la, lo, 1.004); pos.push(v.x, v.y, v.z); } }
    }
    var geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    globe.add(new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.038, map: dotTexture(), alphaTest: 0.4, transparent: true, opacity: 1, color: ivory, sizeAttenuation: true, depthWrite: false })));

    // routes and markers
    var o = latLon(ORIGIN[0], ORIGIN[1], 1.006), arcs = [];
    function addDot(v, color, r) { var d = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12), new THREE.MeshBasicMaterial({ color: color })); d.position.copy(v); globe.add(d); return d; }
    addDot(o, ivory, 0.022);
    (arcsMode === "first" ? unis.slice(0, 1) : unis).forEach(function (u) {
      var b = latLon(u.lat, u.lon, 1.006), mid = o.clone().add(b).normalize().multiplyScalar(1.2 + o.distanceTo(b) * 0.12);
      var mat = new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.5 });
      var curve = new THREE.QuadraticBezierCurve3(o, mid, b);
      var tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 72, 0.0045, 6, false), mat); globe.add(tube);
      arcs.push({ id: u.id, tube: tube, mat: mat, curve: curve, dot: addDot(b, ivory, 0.017), lat: u.lat, lon: u.lon });
    });

    // orbit ring + satellite: depth cue that sits outside the spinning globe
    var ring = null, sat = null;
    if (mode !== "hero" && mode !== "mini") {
      ring = new THREE.Group(); var rp = [];
      for (k = 0; k <= 160; k++) rp.push(new THREE.Vector3(Math.cos(k / 160 * 6.2832) * 1.42, 0, Math.sin(k / 160 * 6.2832) * 1.42));
      ring.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(rp), new THREE.LineBasicMaterial({ color: onNavy ? ivory : slate, transparent: true, opacity: 0.35 })));
      sat = new THREE.Mesh(new THREE.SphereGeometry(0.03, 16, 12), new THREE.MeshBasicMaterial({ color: accent })); ring.add(sat);
      ring.rotation.x = 1.15; ring.rotation.z = -0.35; scene.add(ring);
    }
    var runners = arcs.map(function (a) {
      var r = new THREE.Mesh(new THREE.SphereGeometry(0.014, 12, 8), new THREE.MeshBasicMaterial({ color: ivory })); globe.add(r); return r;
    });

    // orientation
    var rotY, tiltX = 0.28, vel = 0, camX = 0, camY = 0;
    if (mode === "hero" && unis[0]) rotY = yawFor((ORIGIN[1] + unis[0].lon) / 2, (ORIGIN[0] + unis[0].lat) / 2);
    else rotY = yawFor(-30, 30);
    outer.rotation.z = 0.2;

    var dragging = false, lastX = 0, lastMove = -9999, focusUntil = 0, focusY = 0, focusX = 0;
    var mx = 0, my = 0, cmx = 0, cmy = 0, selId = null, visible = true, prev = performance.now(), running = false;

    function selectedId() { var e = document.getElementById("sel-uni"); return e ? e.textContent.trim() : null; }
    function progressCount() { var e = document.getElementById("agent-progress"); return e ? parseInt(e.textContent, 10) || 0 : 0; }

    if (draggable) {
      canvas.style.cursor = "grab";
      canvas.addEventListener("pointerdown", function (e) { dragging = true; lastX = e.clientX; canvas.setPointerCapture(e.pointerId); canvas.style.cursor = "grabbing"; });
      canvas.addEventListener("pointermove", function (e) { if (!dragging) return; rotY += (e.clientX - lastX) * 0.006; lastX = e.clientX; lastMove = performance.now(); if (reduced) tick(performance.now()); });
      var end = function () { dragging = false; canvas.style.cursor = "grab"; lastMove = performance.now(); };
      canvas.addEventListener("pointerup", end); canvas.addEventListener("pointercancel", end);
    }

    new IntersectionObserver(function (en) { visible = en[0].isIntersecting; if (visible) { prev = performance.now(); loop(); } }).observe(wrap);
    function resize() { var w = wrap.clientWidth, h = wrap.clientHeight; if (!w || !h) return; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); if (reduced) tick(performance.now()); }
    new ResizeObserver(resize).observe(wrap); resize();

    function loop() { if (running) return; running = true; requestAnimationFrame(tick); }
    function tick(now) {
      running = false;
      if (!visible) return;
      if (!document.body.contains(canvas)) { renderer.dispose(); return; }
      var dt = Math.min(now - prev, 50); prev = now;

      if (selectable) {
        var s = selectedId();
        if (s && s !== selId) {
          selId = s;
          var a = arcs.filter(function (x) { return x.id === s; })[0];
          if (a && !reduced) { focusY = yawFor(a.lon, a.lat); focusX = clamp(a.lat * Math.PI / 180 * 0.6, -0.5, 0.8); focusUntil = now + 4500; }
        }
      }
      var pc = arcsMode === "progress" ? progressCount() : 0;
      arcs.forEach(function (a, i) {
        var sel = selectable && a.id === selId;
        a.mat.opacity = sel ? 1 : (selectable ? 0.3 : 0.6);
        a.dot.material.color.copy(sel ? accent : ivory); a.dot.scale.setScalar(sel ? 1.8 : 1);
        if (arcsMode === "progress") { var vis = i < Math.ceil(pc * arcs.length / 7); a.tube.visible = vis; a.dot.visible = vis; a.mat.opacity = 0.9; }
      });

      // cursor: horizontal swipes add spin momentum, position tilts the globe and shifts the camera (real depth)
      var rc = wrap.getBoundingClientRect(), cxr = (M.x - (rc.left + rc.width / 2)) / innerWidth * 2, cyr = (M.y - (rc.top + rc.height / 2)) / innerHeight * 2;
      if (!reduced && spin !== "tilt" && mode !== "mini") { vel = clamp(vel + M.dx * 0.00028, -0.035, 0.035); }
      M.dx = 0; vel *= 0.94;
      var mouseOn = M.seen && !coarse && !reduced;
      camX += ((mouseOn ? clamp(cxr, -1, 1) * 0.42 : 0) - camX) * 0.06; camY += ((mouseOn ? clamp(cyr, -1, 1) * -0.3 : 0) - camY) * 0.06;
      camera.position.x = camX; camera.position.y = camY; camera.lookAt(0, 0, 0);

      if (reduced) { /* static frame */ }
      else if (dragging || now - lastMove < 2200) { /* user is in control */ }
      else if (now < focusUntil) { rotY += angDiff(rotY, focusY) * 0.06; tiltX += (focusX - tiltX) * 0.06; }
      else if (mode === "mini") { rotY += (window.scrollY * 0.0065 + now * 0.00012 - rotY) * 0.1; }
      else if (spin === "auto") { rotY += dt * (mode === "dash" ? 0.00034 : 0.00024) + vel; tiltX += (0.28 + clamp(cyr, -1, 1) * 0.12 - tiltX) * 0.03; }
      else if (spin === "scroll") {
        var r = wrap.getBoundingClientRect(), p = clamp(1 - (r.top + r.height) / (innerHeight + r.height), 0, 1);
        rotY += (yawFor(-40, 20) + p * Math.PI * 2 + now * 0.00012 - rotY) * 0.06;
      } else if (spin === "tilt") { cmx += (M.nx - cmx) * 0.05; cmy += (M.ny - cmy) * 0.05; }
      if (spin === "auto" && !dragging) rotY += 0;

      globe.rotation.y = rotY + (spin === "tilt" ? cmx * 0.22 : 0);
      outer.rotation.x = tiltX + (spin === "tilt" ? cmy * 0.14 : 0);
      if (ring) { ring.rotation.y = now * 0.00022; sat.position.set(Math.cos(now * 0.0011) * 1.42, 0, Math.sin(now * 0.0011) * 1.42); }
      runners.forEach(function (rn, i) {
        var a = arcs[i], t = ((now * 0.00028) + i / Math.max(arcs.length, 1)) % 1;
        rn.position.copy(a.curve.getPoint(t)); rn.visible = a.tube.visible;
        var sel = selectable && a.id === selId; rn.scale.setScalar(sel ? 1.8 : 1); rn.material.color.copy(sel ? ivory : accent);
      });
      if (mode === "mini") { var op = clamp((window.scrollY - 520) / 260, 0, 1); wrap.style.opacity = op; if (op < 0.02) { loop(); return; } }
      renderer.render(scene, camera);
      if (!reduced) loop();
    }
    wrap.classList.add("live");
    loop();
  }

  function loadThree(cb) {
    if (window.THREE) return cb();
    if (loadThree.q) return loadThree.q.push(cb);
    loadThree.q = [cb];
    var s = document.createElement("script"); s.src = THREE_SRC; s.async = true;
    s.onload = function () { loadThree.q.forEach(function (f) { f(); }); };
    document.head.appendChild(s);
  }
  function bootGlobes() {
    Array.prototype.forEach.call(document.querySelectorAll("canvas[data-globe]:not([data-ready])"), function (c) {
      c.dataset.ready = "1";
      if (c.dataset.globe === "hero" && (reduced || coarse || innerWidth < 900)) return;   // static desk scene
      var io = new IntersectionObserver(function (en) {
        if (!en[0].isIntersecting) return; io.disconnect();
        loadThree(function () { try { buildGlobe(c); } catch (e) { /* keep SVG fallback */ } });
      }, { rootMargin: "200px" });
      io.observe(c);
    });
  }

  /* ───────────────────── Hero parallax (mouse + scroll) ───────────────────── */
  function initParallax(scene) {
    if (reduced || coarse || innerWidth < 900) return;
    var layers = Array.prototype.slice.call(scene.querySelectorAll(".layer[data-depth]"));
    var tx = 0, ty = 0, cx = 0, cy = 0, raf = null;
    function frame() {
      cx += (tx - cx) * 0.08; cy += (ty - cy) * 0.08;
      var sy = Math.min(window.scrollY, 700);
      layers.forEach(function (l) {
        var d = parseFloat(l.dataset.depth), r = parseFloat(l.dataset.rot || "0");
        l.style.transform = "translate3d(" + (cx * d * -9).toFixed(2) + "px," + (cy * d * -6 + sy * d * 0.045).toFixed(2) + "px,0) rotate(" + (r + cx * d * 0.35 + sy * d * 0.002).toFixed(2) + "deg)";
      });
      raf = (Math.abs(tx - cx) > 0.001 || Math.abs(ty - cy) > 0.001) ? requestAnimationFrame(frame) : null;
    }
    var kick = function () { if (!raf) raf = requestAnimationFrame(frame); };
    window.addEventListener("mousemove", function (e) { tx = (e.clientX / innerWidth - 0.5) * 2; ty = (e.clientY / innerHeight - 0.5) * 2; kick(); }, { passive: true });
    window.addEventListener("scroll", kick, { passive: true });
    layers.forEach(function (l) { l.style.transition = "none"; });
  }

  /* ───────────────────── Scroll reveal, count-up, tilt ───────────────────── */
  function fmt(n, el) { return (el.dataset.prefix || "") + Math.round(n).toLocaleString("en-US") + (el.dataset.suffix || ""); }
  function countUp(el) {
    var to = parseFloat(el.dataset.count); if (isNaN(to)) return;
    var t0 = performance.now(), dur = 1300;
    (function step(now) { var p = clamp((now - t0) / dur, 0, 1), e = 1 - Math.pow(1 - p, 3); el.textContent = fmt(to * e, el); if (p < 1) requestAnimationFrame(step); })(t0);
  }
  var revealIO = null;
  function bootReveal() {
    if (reduced) return;
    if (!revealIO) revealIO = new IntersectionObserver(function (en) {
      en.forEach(function (x) {
        if (!x.isIntersecting) return; revealIO.unobserve(x.target); x.target.classList.add("in");
        x.target.querySelectorAll("[data-count]").forEach(countUp);
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -6% 0px" });
    document.querySelectorAll(".reveal:not([data-r])").forEach(function (el) {
      el.dataset.r = "1";
      el.querySelectorAll("[data-count]").forEach(function (c) { c.textContent = fmt(0, c); });
      revealIO.observe(el);
    });
  }
  function bootTilt() {
    if (reduced || coarse) return;
    document.querySelectorAll("[data-tilt]:not([data-t])").forEach(function (el) {
      el.dataset.t = "1";
      el.addEventListener("mousemove", function (e) {
        var r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        el.style.transition = "transform .08s linear";
        el.style.transform = "perspective(900px) rotateX(" + (-y * 5).toFixed(2) + "deg) rotateY(" + (x * 6).toFixed(2) + "deg)";
      });
      el.addEventListener("mouseleave", function () { el.style.transition = "transform .5s cubic-bezier(.2,.7,.2,1)"; el.style.transform = ""; });
    });
  }

  /* ───────────────────── Scroll progress + section index ───────────────────── */
  var bar = null;
  function bootChrome() {
    if (bar) return;
    bar = document.createElement("div"); bar.id = "scroll-progress"; document.body.appendChild(bar);
    var upd = function () {
      var h = document.documentElement.scrollHeight - innerHeight;
      bar.style.transform = "scaleX(" + (h > 0 ? clamp(window.scrollY / h, 0, 1) : 0) + ")";
      var links = document.querySelectorAll(".section-index a"), cur = null;
      links.forEach(function (a) { var t = document.getElementById(a.getAttribute("href").slice(1)); if (t && t.getBoundingClientRect().top < innerHeight * 0.4) cur = a; });
      links.forEach(function (a) { a.classList.toggle("active", a === cur); });
    };
    window.addEventListener("scroll", upd, { passive: true }); window.addEventListener("resize", upd); upd();
  }

  /* ───────────────────── Cursor effects ───────────────────── */
  var ringEl = null, dotEl = null, rx = 0, ry = 0, ringOn = false;
  var HOT = "a,button,input,select,textarea,label,.marker,.uni-chip,.doc-tab,[data-tilt],canvas[data-drag='1']";
  function bootCursor() {
    if (ringEl || reduced || coarse) return;
    ringEl = document.createElement("div"); ringEl.id = "cursor-ring";
    dotEl = document.createElement("div"); dotEl.id = "cursor-dot";
    document.body.appendChild(ringEl); document.body.appendChild(dotEl);
    window.addEventListener("mousemove", function (e) {
      ringOn = true; ringEl.style.opacity = 1; dotEl.style.opacity = 1;
      dotEl.style.transform = "translate(" + e.clientX + "px," + e.clientY + "px)";
      var t = e.target && e.target.closest ? e.target : null;
      ringEl.classList.toggle("hot", !!(t && t.closest(HOT)));
      ringEl.classList.toggle("dark", !!(t && t.closest(".navy,.cover,.open-cover")));
      dotEl.classList.toggle("dark", !!(t && t.closest(".navy,.cover,.open-cover")));
      var sh = t && t.closest(".sheet");                       // soft desk-lamp highlight on paper
      if (sh) { var r = sh.getBoundingClientRect(); sh.style.setProperty("--mx", (e.clientX - r.left) + "px"); sh.style.setProperty("--my", (e.clientY - r.top) + "px"); }
    }, { passive: true });
    document.addEventListener("mouseleave", function () { ringEl.style.opacity = 0; dotEl.style.opacity = 0; });
    (function follow() {
      rx += (M.x - rx) * 0.18; ry += (M.y - ry) * 0.18;
      ringEl.style.transform = "translate(" + rx.toFixed(1) + "px," + ry.toFixed(1) + "px)";
      requestAnimationFrame(follow);
    })();
  }

  /* ─── magnetic buttons: they lean toward the cursor (uses the `translate` property, so hover transforms still work) ─── */
  var mags = [];
  function bootMagnetic() {
    if (reduced || coarse) return;
    mags = Array.prototype.slice.call(document.querySelectorAll(".tab-button,.btn-download,.btn-ghost"));
    if (bootMagnetic.on) return; bootMagnetic.on = true;
    window.addEventListener("mousemove", function (e) {
      mags.forEach(function (el) {
        if (!document.body.contains(el)) return;
        var r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2, dx = e.clientX - cx, dy = e.clientY - cy;
        var near = Math.abs(dx) < r.width / 2 + 60 && Math.abs(dy) < r.height / 2 + 50;
        el.style.translate = near ? (dx * 0.14).toFixed(1) + "px " + (dy * 0.22).toFixed(1) + "px" : "0px 0px";
      });
    }, { passive: true });
  }

  /* ─── depth groups: children with data-pd float at different depths as the cursor moves ─── */
  var groups = [];
  function bootGroups() {
    groups = Array.prototype.slice.call(document.querySelectorAll("[data-pgroup]"));
    if (bootGroups.on || reduced || coarse) return; bootGroups.on = true;
    (function tick() {
      groups.forEach(function (g) {
        if (!document.body.contains(g)) return;
        var r = g.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) return;
        var tx = M.seen ? clamp((M.x - (r.left + r.width / 2)) / (innerWidth / 2), -1, 1) : 0, ty = M.seen ? clamp((M.y - (r.top + r.height / 2)) / (innerHeight / 2), -1, 1) : 0;
        var cur = g._c || (g._c = { x: 0, y: 0 }); cur.x += (tx - cur.x) * 0.07; cur.y += (ty - cur.y) * 0.07;
        g.querySelectorAll("[data-pd]").forEach(function (c) {
          var d = parseFloat(c.dataset.pd);
          c.style.translate = (cur.x * d * -16).toFixed(1) + "px " + (cur.y * d * -11).toFixed(1) + "px";
          c.style.rotate = (cur.x * d * 0.9).toFixed(2) + "deg";
        });
      });
      requestAnimationFrame(tick);
    })();
  }

  /* ─── scroll parallax: data-sp = speed; the element drifts and shrinks slightly as you scroll ─── */
  var sps = [];
  function bootScrollParallax() {
    sps = Array.prototype.slice.call(document.querySelectorAll("[data-sp]"));
    if (bootScrollParallax.on || reduced) return; bootScrollParallax.on = true;
    var run = function () {
      var y = window.scrollY;
      sps.forEach(function (el) {
        if (!document.body.contains(el)) return;
        var f = parseFloat(el.dataset.sp);
        el.style.translate = "0px " + (Math.min(y, 900) * f).toFixed(1) + "px";
        el.style.scale = String(1 - Math.min(y, 700) * 0.00028);
      });
    };
    window.addEventListener("scroll", run, { passive: true }); run();
  }


  /* ───────────────────── Motion toggle + ?debug=1 panel ───────────────────── */
  function bootMotionToggle() {
    if (document.getElementById("motion-toggle")) return;
    var b = document.createElement("button"); b.id = "motion-toggle"; b.type = "button";
    if (reduced) { b.textContent = OS_REDUCED && PREF !== "off" ? "Animations off (system setting) · Turn on" : "Animations off · Turn on"; b.className = "attn"; }
    else b.textContent = "Animations on · Turn off";
    b.addEventListener("click", function () { try { localStorage.setItem("meridian-motion", reduced ? "on" : "off"); } catch (e) {} location.reload(); });
    document.body.appendChild(b);
  }
  function bootDebug() {
    if (!/[?&]debug=1/.test(location.search)) return;
    var p = document.getElementById("debug-panel"); if (!p) { p = document.createElement("div"); p.id = "debug-panel"; document.body.appendChild(p); }
    var gl = false; try { var c = document.createElement("canvas"); gl = !!(c.getContext("webgl") || c.getContext("experimental-webgl")); } catch (e) {}
    var cv = document.querySelectorAll("canvas[data-globe]");
    p.textContent = "MERIDIAN debug\n" +
      "motion: " + (reduced ? "OFF" : "ON") + "  (system reduce-motion: " + OS_REDUCED + ", saved choice: " + PREF + ")\n" +
      "webgl: " + gl + "\nthree.js loaded: " + !!window.THREE + "\nland data loaded: " + !!window.MERIDIAN_LAND + "\n" +
      "globe canvases: " + cv.length + ", live: " + document.querySelectorAll(".globe3d.live").length + "\n" +
      "pointer coarse: " + coarse + "  width: " + innerWidth;
  }

  function boot() {
    var scene = document.getElementById("meridian-scene");
    if (scene && !scene.dataset.ready) { scene.dataset.ready = "1"; initParallax(scene); }
    bootGlobes(); bootReveal(); bootTilt(); bootChrome(); bootCursor(); bootMagnetic(); bootGroups(); bootScrollParallax(); bootMotionToggle(); bootDebug();
  }
  setInterval(boot, 400);
})();
