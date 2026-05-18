import React, { useState, useEffect } from "react";
import { Loader2, Layers, Image as ImageIcon, Eye } from "lucide-react";

interface Props {
  baseImage: string;
  fetchHeatmap: () => Promise<string>; // returns "data:image/png;base64,..." or throws
}

const HeatmapViewer: React.FC<Props> = ({ baseImage, fetchHeatmap }) => {
  const [activeTab, setActiveTab] = useState<"original" | "heatmap" | "overlay">("original");
  const [heatmap, setHeatmap] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0.4);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noSignal, setNoSignal] = useState(false);

  // Reset heatmap cache when image or fetch fn changes — prevents stale overlays
  useEffect(() => {
    setHeatmap(null);
    setError(null);
    setNoSignal(false);
    setActiveTab("original");
  }, [fetchHeatmap, baseImage]);

  const loadHeatmap = async () => {
    if (heatmap || loading) return;

    setLoading(true);
    setError(null);
    setNoSignal(false);

    try {
      const data = await fetchHeatmap();
      if (!data || data === "data:image/png;base64,") {
        setNoSignal(true);
      } else {
        setHeatmap(data);
      }
    } catch (err: any) {
      console.error("Failed to fetch heatmap:", err);
      if (err?.message === "__NO_SIGNAL__") {
        setNoSignal(true);
      } else {
        setError(err?.message || "Heatmap synthesis failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = async (tab: "original" | "heatmap" | "overlay") => {
    setActiveTab(tab);
    if (tab !== "original") {
      await loadHeatmap();
    }
  };

  const handleRetry = () => {
    setHeatmap(null);
    setError(null);
    setNoSignal(false);
    loadHeatmap();
  };

  return (
    <div className="w-full glass-panel rounded-2xl p-6 border border-white/10 overflow-hidden shadow-2xl">
      {/* Header & Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Layers className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-fg italic tracking-tight">VISUALIZATION ENGINE</h3>
            <p className="text-xs text-fg-dim font-medium tracking-widest uppercase">Compare &amp; Analyze Layers</p>
          </div>
        </div>

        <div className="flex bg-black/20 p-1 rounded-xl border border-white/5 self-start md:self-auto">
          {[
            { id: "original", label: "Original", icon: ImageIcon },
            { id: "heatmap",  label: "Heatmap",  icon: Layers   },
            { id: "overlay",  label: "Overlay",  icon: Eye      },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 ${
                activeTab === tab.id
                  ? "bg-primary text-black shadow-lg shadow-primary/20 scale-105"
                  : "text-fg-dim hover:text-fg hover:bg-white/5"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Preview Area: NO overflow-hidden on the container — image defines height */}
      <div className="relative w-full rounded-xl bg-black/40 border border-white/5">
        {/* Base Image — full height, never cropped. rounded-xl on img for clipping. */}
        <img
          src={baseImage}
          alt="Base analysis"
          className={`block w-full h-auto rounded-xl transition-opacity duration-500 ${
            activeTab === "heatmap" ? "opacity-0" : "opacity-100"
          }`}
        />

        {/* Heatmap overlay — absolutely positioned, same size as the base image */}
        {heatmap && (
          <img
            src={heatmap}
            alt="Heatmap layer"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              objectFit: "fill",
              borderRadius: "0.75rem",
              opacity:
                activeTab === "overlay" ? opacity :
                activeTab === "heatmap" ? 1 :
                0,
              mixBlendMode: "normal",
              transition: "opacity 0.4s ease",
              pointerEvents: "none",
            }}
          />
        )}

        {/* Loading State */}
        {loading && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center gap-4 z-20">
            <Loader2 className="w-10 h-10 text-primary animate-spin" />
            <p className="text-primary font-bold tracking-widest text-sm uppercase animate-pulse">
              Synthesizing Heatmap...
            </p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center gap-4 z-20 p-6 text-center">
            <p className="text-red-400 font-medium text-sm">{error}</p>
            <button
              onClick={handleRetry}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors border border-white/10 font-semibold"
            >
              Retry Analysis
            </button>
          </div>
        )}
      </div>

      {/* Overlay Opacity Slider — only visible when overlay tab is active AND heatmap exists */}
      <div
        className={`mt-6 space-y-3 transition-all duration-500 ${
          activeTab === "overlay" && heatmap
            ? "opacity-100 translate-y-0"
            : "opacity-0 -translate-y-4 pointer-events-none h-0 p-0 m-0"
        }`}
      >
        <div className="flex justify-between items-center px-1">
          <label className="text-xs font-bold text-fg-dim tracking-widest uppercase">Overlay Transparency</label>
          <span className="text-xs font-mono font-bold text-primary bg-primary/10 px-2 py-0.5 rounded italic">
            {(opacity * 100).toFixed(0)}%
          </span>
        </div>
        <div className="relative group px-1">
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-primary group-hover:bg-white/20 transition-all"
          />
        </div>
        <div className="flex justify-between text-[10px] text-fg-dim/50 font-bold px-1">
          <span>MIN</span>
          <span>NEUTRAL</span>
          <span>MAX</span>
        </div>
      </div>

      {/* Empty Prompt — shown on original tab when nothing has been fetched yet */}
      {!loading && !heatmap && !noSignal && !error && activeTab === "original" && (
        <div className="mt-4 p-3 bg-white/5 border border-white/5 rounded-lg flex items-center justify-center gap-2">
          <p className="text-[10px] text-fg-dim font-medium uppercase tracking-widest">
            Switch to <span className="text-primary italic">Heatmap</span> or{" "}
            <span className="text-primary italic">Overlay</span> to begin synthesis
          </p>
        </div>
      )}
    </div>
  );
};

export default HeatmapViewer;
