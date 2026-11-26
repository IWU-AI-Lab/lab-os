// The object detector for object-labels.js (quick job 128), in a Web Worker: the headset's frames never wait
// for it. MediaPipe's ObjectDetector with EfficientDet-Lite0 (int8, the 80 COCO kinds), on the CPU.
//
// MediaPipe loads its wasm loader with importScripts(); a module worker has none, so it calls self.import(url)
// when that exists. The loader is a plain script that declares ModuleFactory: run it as global code.
self.import = async (url) => {
  const code = await (await fetch(url)).text();
  (0, eval)(`${code}\nself.ModuleFactory = ModuleFactory;`);
};

const MP = "/web/vendor/mediapipe";
let detector = null;

self.onmessage = async (e) => {
  const m = e.data;
  if (m.type === "load") {
    try {
      const { FilesetResolver, ObjectDetector } = await import(`${MP}/vision_bundle.mjs`);
      const files = await FilesetResolver.forVisionTasks(`${MP}/wasm`);
      detector = await ObjectDetector.createFromOptions(files, {
        baseOptions: { modelAssetPath: `${MP}/efficientdet_lite0.tflite`, delegate: "CPU" },
        runningMode: "IMAGE",
        scoreThreshold: m.minScore,
        maxResults: m.max,
      });
      self.postMessage({ type: "ready" });
    } catch (err) {
      self.postMessage({ type: "failed", message: String(err?.message || err) });
    }
  } else if (m.type === "frame") {
    const { bitmap } = m, W = bitmap.width, H = bitmap.height;
    let found = [];
    try {
      const t0 = performance.now();
      const r = detector ? detector.detect(bitmap) : { detections: [] };
      found = r.detections.map((d) => ({
        name: d.categories[0]?.categoryName || "object",
        score: d.categories[0]?.score || 0,
        box: { x: d.boundingBox.originX / W, y: d.boundingBox.originY / H, w: d.boundingBox.width / W, h: d.boundingBox.height / H },
      }));
      self.postMessage({ type: "found", found, ms: Math.round(performance.now() - t0) });
    } catch (err) {
      self.postMessage({ type: "found", found, error: String(err?.message || err) });
    } finally {
      bitmap.close();
    }
  }
};
