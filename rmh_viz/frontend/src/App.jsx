import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";

const useThreeScene = (streamlines, isoSurface, showUncertainty) => {
  const ref = useRef();
  useEffect(() => {
    const width = ref.current.clientWidth || 640;
    const height = ref.current.clientHeight || 480;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 2);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    ref.current.appendChild(renderer.domElement);

    const light = new THREE.PointLight(0xffffff, 1);
    light.position.set(5, 5, 5);
    scene.add(light);

    const material = new THREE.MeshPhongMaterial({ color: 0x156289, transparent: true, opacity: 0.4 });
    const geometry = new THREE.BufferGeometry();
    const vertices = new Float32Array(isoSurface.flat());
    geometry.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
    const mesh = new THREE.Points(geometry, material);
    scene.add(mesh);

    const streamlineMaterial = new THREE.LineBasicMaterial({ color: 0xff8800 });
    streamlines.forEach((line) => {
      const lineGeometry = new THREE.BufferGeometry();
      const lineVertices = new Float32Array(line.flat());
      lineGeometry.setAttribute("position", new THREE.BufferAttribute(lineVertices, 3));
      const polyline = new THREE.Line(lineGeometry, streamlineMaterial);
      scene.add(polyline);
    });

    if (showUncertainty) {
      const heatMaterial = new THREE.PointsMaterial({ color: 0xff0000, size: 0.02, opacity: 0.5, transparent: true });
      const heatGeometry = new THREE.BufferGeometry();
      heatGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(isoSurface.flat()), 3));
      const heat = new THREE.Points(heatGeometry, heatMaterial);
      scene.add(heat);
    }

    const animate = () => {
      requestAnimationFrame(animate);
      mesh.rotation.y += 0.002;
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      renderer.dispose();
      ref.current.removeChild(renderer.domElement);
    };
  }, [streamlines, isoSurface, showUncertainty]);
  return ref;
};

const App = () => {
  const [data, setData] = useState(null);
  const [showUncertainty, setShowUncertainty] = useState(true);
  const [metrics, setMetrics] = useState([]);

  useEffect(() => {
    fetch("/field/stream")
      .then((res) => res.json())
      .then(setData);
    fetch("/metrics")
      .then((res) => res.json())
      .then((payload) => setMetrics(payload.metrics));
  }, []);

  const canvasRef = useThreeScene(data?.streamlines || [], data?.iso_surface || [], showUncertainty);

  return (
    <div className="app">
      <h1>RMH Field Visualizer</h1>
      <label>
        <input type="checkbox" checked={showUncertainty} onChange={(e) => setShowUncertainty(e.target.checked)} />
        Show uncertainty heatmap
      </label>
      <div className="canvas" ref={canvasRef} style={{ width: "100%", height: "480px" }} />
      <section className="metrics">
        <h2>Session Metrics</h2>
        <ul>
          {metrics.map((m) => (
            <li key={m.name}>
              {m.name}: {m.value} (±{Math.round(m.confidence * 100)}%)
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

export default App;
