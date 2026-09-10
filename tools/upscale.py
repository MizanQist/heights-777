import sys, os, time, numpy as np, onnxruntime as ort
from PIL import Image, ImageOps
SRC = "/Users/mammanali/Desktop/Desktop - Mamman’s MacBook Pro/Heights 77"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"); os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))  # put real_esrgan_x2.onnx and real_esrgan_x4.onnx here (huggingface.co/SceneWorks/real-esrgan-onnx)
TILE, PAD = 256, 16
so = ort.SessionOptions(); so.log_severity_level = 3
SESS = {}
def session(scale):
    if scale not in SESS:
        SESS[scale] = ort.InferenceSession(os.path.join(HERE, f"real_esrgan_x{scale}.onnx"), so, providers=["CPUExecutionProvider"])
        x = np.random.rand(1, 3, TILE+2*PAD, TILE+2*PAD).astype(np.float32); SESS[scale].run(None, {"input": x})
        t = time.time(); SESS[scale].run(None, {"input": x}); print(f"[bench] x{scale} cpu: {time.time()-t:.2f}s per {TILE+2*PAD}px tile", flush=True)
    return SESS[scale]

def upscale(im, SCALE):
    sess = session(SCALE)
    a = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    H, W = a.shape[:2]
    Hp = (H + TILE - 1) // TILE * TILE; Wp = (W + TILE - 1) // TILE * TILE
    a = np.pad(a, ((PAD, Hp - H + PAD), (PAD, Wp - W + PAD), (0, 0)), mode="reflect")
    out = np.zeros((Hp * SCALE, Wp * SCALE, 3), dtype=np.uint8)
    n = (Hp // TILE) * (Wp // TILE); k = 0; t0 = time.time()
    for y in range(0, Hp, TILE):
        for x0 in range(0, Wp, TILE):
            tile = a[y:y + TILE + 2*PAD, x0:x0 + TILE + 2*PAD]
            inp = np.ascontiguousarray(tile.transpose(2, 0, 1)[None])
            o = sess.run(None, {"input": inp})[0][0].transpose(1, 2, 0)
            o = o[PAD*SCALE:(PAD+TILE)*SCALE, PAD*SCALE:(PAD+TILE)*SCALE]
            out[y*SCALE:(y+TILE)*SCALE, x0*SCALE:(x0+TILE)*SCALE] = np.clip(o * 255.0 + 0.5, 0, 255).astype(np.uint8)
            k += 1
            if k % 8 == 0 or k == n: print(f"   tile {k}/{n}  {time.time()-t0:.0f}s", flush=True)
    return Image.fromarray(out[:H*SCALE, :W*SCALE])

JOBS = [  # source, output name, target width, fixed (w,h) cover-fit, model scale
 ("22FE5A65-98A3-44AF-97A6-64D521B7824F.jpeg", "corner-dusk", 2880, None, 4),
 ("826B157D-EA2B-407B-A600-E6872B50E84C_1_105_c.jpeg", "entrance-day", None, (2000, 2800), 4),
 ("6DFF9481-1AA4-4066-B1E0-5823DCA593A6_1_201_a.jpeg", "entrance-dusk", None, (2000, 2800), 2),
 ("0840AF59-0AF5-4EA3-9219-F58999D87DCF.jpeg", "front-overcast", 2340, None, 2),
 ("6C6B333A-1B55-4799-AA94-BB4283D94E63_1_105_c.jpeg", "front-clear", 2000, None, 4),
 ("88D8B942-D2F8-400A-8284-636F75AC629D_1_105_c.jpeg", "balconies-aerial", 2000, None, 4),
 ("FCC13B8A-B0A9-4504-8A2A-481A19E40E6D_1_105_c.jpeg", "street-day", 2000, None, 4),
]
only = sys.argv[1:]  # optional subset of output names
for src, name, tw, fixed, SC in JOBS:
    if only and name not in only: continue
    im = ImageOps.exif_transpose(Image.open(os.path.join(SRC, src)))
    print(f"[{name}] {im.size} -> x{SC}", flush=True); t = time.time()
    big = upscale(im, SC)
    if fixed: fin = ImageOps.fit(big, fixed, Image.LANCZOS, centering=(0.5, 0.5))
    elif tw >= big.width: fin = big
    else: fin = big.resize((tw, round(big.height * tw / big.width)), Image.LANCZOS)
    fin.save(os.path.join(OUT, name + ".jpg"), "JPEG", quality=90, optimize=True, progressive=True, subsampling=0)
    print(f"[{name}] done {fin.size} in {time.time()-t:.0f}s -> {os.path.getsize(os.path.join(OUT, name+'.jpg'))//1024} KB", flush=True)
print("ALL DONE", flush=True)
